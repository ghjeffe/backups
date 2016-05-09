#!/bin/python3.3

from argparse import ArgumentParser
import os
import re
import shutil
import subprocess
import sys
import time

from utilities import timer, pretend

BACKUP_COUNT = 21 #(3 weeks)
BACKUP_DST_ROOT = '/backups'
BACKUP_SRC_ROOT = '/mnt'
MAC_ADDRS = {
             'lianli':'00:03:47:f8:7d:b1'
             }


def run_backup(host, verbose=False, wait=0):
    dir_perms = 664 #used in mkdir
    host_root_src_dir = os.path.join(BACKUP_SRC_ROOT, host)
    host_root_dst_dir = os.path.join(BACKUP_DST_ROOT, host)
    new_dir_suffix = '.00'
    link_dir_suffix = '.01'
    new_dir = os.path.join(
                           host_root_dst_dir
                           ,'{}{}'.format(
                                          host
                                          ,new_dir_suffix
                                          )
                           )
    #hard links will be set between new_dir and link_dir for data de-duplication
    link_dir = os.path.join(
                            host_root_dst_dir
                           ,'{}{}'.format(
                                          host
                                          ,link_dir_suffix
                                          )
                           )
    last_dir = '{}.{}'.format(new_dir, str(BACKUP_COUNT)) #last directory to keep

    def shuffle_dirs():
        if verbose:
            print("Shuffling dirs")
        os.chdir(host_root_dst_dir)
        
        backup_dirs = list(pathlib.Path('.').glob('{}.[0-9][0-9]*{}'.format(
                                                            host
                                                            ,len(BACKUP_COUNT)
                                                                            )
                                                  )
                           )
        for backup_dir in sorted(backup_dirs, key=lambda x: int(
                                                        x.name.split('.')[1]
                                                        )
                                 ,reverse=True
                                 ):
            base, extn = backup_dir.name.split('.')
            if int(extn) == BACKUP_COUNT:
                shutil.rmtree(backup_dir.name)
            else:
                dir_becomes = '{}.{}'.format(base, str(int(extn) + 1).zfill(2))
                backup_dir.rename(dir_becomes)
                print('{} becomes {}'.format(backup_dir.name, dir_becomes))
        os.mkdir('testdir.00')
    
    def perform_backup():
        time.sleep(wait)
        os.chdir(host_root_dst_dir)
        shuffle_dirs()
        os.mkdir(new_dir, dir_perms)
        shutil.copy('cludes', new_dir + '/') #capture cludes file for backup validation
        rsync()
        os.utime(new_dir, None) #update timestamp of newest directory
        return True

    def rsync():
        '''
         Run rsync
         Rsync options:
            -v, --verbose               increase verbosity
            -q, --quiet                 suppress non-error messages
                --no-motd               suppress daemon-mode MOTD (see caveat)
            -c, --checksum              skip based on checksum, not mod-time & size
            -a, --archive               archive mode; equals -rlptgoD (no -H,-A,-X)
                --no-OPTION             turn off an implied OPTION (e.g. --no-D)
            -r, --recursive             recurse into directories
            -R, --relative              use relative path names
                --no-implied-dirs       don't send implied dirs with --relative
            -b, --backup                make backups (see --suffix & --backup-dir)
                --backup-dir=DIR        make backups into hierarchy based in DIR
                --suffix=SUFFIX         backup suffix (default ~ w/o --backup-dir)
            -u, --update                skip files that are newer on the receiver
                --inplace               update destination files in-place
                --append                append data onto shorter files
                --append-verify         --append w/old data in file checksum
            -d, --dirs                  transfer directories without recursing
            -l, --links                 copy symlinks as symlinks
            -t, --times                 preserve modification times
        '''
        rsync_kwargs = {
                        'rsync_cmd' : '/bin/rsync'
                        ,'link_dest' : '{}{}'.format(host_root_dst_dir, link_dir_suffix)
                        ,'clude_file' : os.path.join(host_root_dst_dir, 'cludes')
                        ,'log_file' : os.path.join(host_root_dst_dir, 'backup.log')
                        ,'backup_src' : host_root_src_dir
                        ,'new_dir' : new_dir
                        ,'perms' : 'ug+rx,o-rwx' #used for --chmod; can be prefixed with D for directories or F for files
                        }
        cmd_text = (
                    '{rsync_cmd} --rltvz --progress --stats'
                    ' --chmod {perms}'
                    ' --link-dest={link_dest}'
                    ' --exclude-from={clude_file}'
                    ' --log-file={log_file}'
                    ' {backup_src}'
                    ' {new_dir}'
                    ).format(**rsync_kwargs)
        rsync_output = subprocess.check_output(cmd_text)
    
    #ensure mount point is available
    mounts = subprocess.check_output(['cat','/proc/mounts']
                                     ,stderr = subprocess.PIPE
                                     ).decode('utf8')
    regex_host_mount = re.compile(r'(//{0}/\w+\$?) (/mnt/{0})'.format(host))
    if regex_host_mount.search(mounts): #mount point exists, continue with backup
        retval = perform_backup()
    else: #attempt to mount
        cmd_text = ['mount','/mnt/{}'.format(host)]
        proc_mount = subprocess.Popen(cmd_text, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
        out, err = proc_mount.communicate()
        if proc_mount.returncode == 0:
            retval = perform_backup()
        else: #unable to mount filesystem to perform backup, must exit
            retval = False

    return retval


def shutdown(host):
    #Shutdown of remote machine succeeded
    regex_pw = re.compile('username=(\w*)[ \W\n]password=(\w*)[ \W\n]')
    creds = regex_pw.search(open('/home/ghjeffeii/.smbcreds'
                                 ,mode='r'
                                 ,encoding='utf8'
                                 ).read()
                            ).group(1,2)
    cmd_text = ['net','rpc','shutdown','-I',host,'-U','{}%{}'.format(*creds)]
    proc_shutdown = subprocess.check_output(cmd_text, timeout=5)
    if 'succeeded' in proc_shutdown.decode('utf8').lower():
        return True
    else:
        return False
    
def is_alive(host, attempts = 1):
    cmd_text = ['ping', '-w', '.1', '-c', str(attempts), host]
    try:
        proc_ping = subprocess.check_output(cmd_text, timeout=.5)
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
        return False
    else:
        return True if 'ttl' in proc_ping.decode('utf8').lower() else False

def wake_machine(mac_addr):
    try:
        subprocess.check_output(['/bin/wol',mac_addr]
                                ,stderr=subprocess.PIPE
                                )
        return True
    except (OSError #command not present
            ,subprocess.CalledProcessError #bad argument
            ):
        return False

def main():
    was_off = False #was machine off before script began; initialize False
    parser = ArgumentParser(description='Pull backup for specified host, waking and shutting if desired'
                            ,usage='{} host'.format(sys.argv[1])
                            )
    parser.add_argument('host', help='host to pull backup from')
    parser.add_argument('--aggressive'
                        ,help='wake and shut machine if necessary'
                        ,action='store_true' #false by default
                        )
    parser.add_argument('--verbose'
                        ,help='set for print statements'
                        ,action='store_true' #false by default
                        )
    
    args = parser.parse_args()
    timer_host_alive = timer(is_alive
                             ,run_until=True
                             ,interval=10
                             ,verbose=args.verbose
                             )
    timer_host_dead = timer(is_alive
                            ,run_until=False
                            ,interval=10
                            ,verbose=args.verbose
                            )
    if is_alive(args.host): #host online
        backup_retval = run_backup(args.host)
    elif args.aggressive: #host offline and we need to wake
        was_off = True
        if wake_machine(MAC_ADDRS[args.host]):
            alive_retval = timer_host_alive(args.host)
            if alive_retval: #host now online
                backup_retval = run_backup(args.host, wait=30, verbose=args.verbose)
                if shutdown(args.host):
                    retval_host_dead = timer_host_dead(args.host) 
                    if retval_host_dead:
                        print('{} is dead; duration: {}'.format(args.host
                                                                ,retval_host_dead
                                                                )
                              )
                    else:
                        print('{} is not killable'.format(args.host))
                else:
                    print('shutdown failed', file=sys.stderr)
            else:
                print('{} is not wakeable'.format(args.host), file=sys.stderr)
        else:
            print('wake command failed', file=sys.stderr)

def main2():
    rsync()

if __name__ == "__main__":
    sys.exit(main())
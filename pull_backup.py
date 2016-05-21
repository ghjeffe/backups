#!/bin/python3.3
''' pull backups from specified host '''
#written by Gary H Jeffers II
#===============================================================================
# v0.1.1 5/19/2016
#     -fixed rsync source dir issue by adding trailing slash
#===============================================================================

from argparse import ArgumentParser
import os
import pathlib
import re
import shutil
import subprocess
import sys
import time

from utilities import timer

BACKUP_COUNT = 21 #(3 weeks)
BACKUP_DST_ROOT = pathlib.Path('/backups')
BACKUP_SRC_ROOT = pathlib.Path('/mnt')
MAC_ADDRS = {
             'lianli':'00:03:47:f8:7d:b1'
             }


def run_backup(host, verbose=False, wait=0):
    dir_perms = 664 #used in mkdir
    dir_pad = 0 #character used to pad newer directories to ensure consistent lengths (01 vs 21)
    backup_dir_fmt = '{base}.{num:{pad}>{width}d}'
    host_root_src_dir = BACKUP_SRC_ROOT.joinpath(host)
    host_root_dst_dir = BACKUP_DST_ROOT.joinpath(host)
    new_dir = host_root_dst_dir.joinpath(backup_dir_fmt.format(base=host
                                               ,num=0
                                               ,pad=dir_pad
                                               ,width=len(str(BACKUP_COUNT))
                                               )
                                         )
    link_dir = host_root_dst_dir.joinpath(backup_dir_fmt.format(base=host
                                               ,num=1
                                               ,pad=dir_pad
                                               ,width=len(str(BACKUP_COUNT))
                                               )
                                         )

    def shuffle_dirs():
        if verbose:
            print("Shuffling dirs")
        backup_dir_glob = '{}.{}'.format(host,'[0-9]' * len(str(BACKUP_COUNT - 1)))
        glob_items = list(host_root_dst_dir.glob(backup_dir_glob))
        for glob_item in sorted(glob_items, key=lambda x: int(x.name.split('.')[1]) #TEST: dangerous slice; might want [-1] instead
                                ,reverse=True
                                ):
            if not glob_item.is_dir():
                continue
            backup_dir = glob_item #rename for sanity now that we know what it is
            del(glob_item)
            base, extn = backup_dir.name.split('.')
            try:
                if base == host and extn == BACKUP_COUNT: #ensure that we're handling a backup directory for this host
                    shutil.rmtree(str(backup_dir))
            except:
                raise
            else:
                backup_dir.rename(backup_dir_fmt.format(base=base
                                                        ,num=int(extn) + 1
                                                        ,pad=0
                                                        ,width=len(str(BACKUP_COUNT))
                                                        )
                                  )
        new_dir.mkdir(mode=dir_perms)
    
    def perform_backup():
        time.sleep(wait)
        os.chdir(str(host_root_dst_dir)) #is this necessary?
        shuffle_dirs()
        shutil.copy('cludes', str(new_dir) + '/') #capture cludes file for backup validation
        rsync()
        new_dir.touch() #update timestamp of newest directory
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
            -z, --compress              compress file data during the transfer
        '''
        rsync_kwargs = {
                        'rsync_cmd' : '/usr/bin/rsync'
                        ,'link_dir' : str(link_dir)
                        ,'clude_file' : os.path.join(str(host_root_dst_dir), 'cludes')
                        ,'log_file' : os.path.join(str(host_root_dst_dir), 'backup.log')
                        ,'backup_src' : str(host_root_src_dir)
                        ,'backup_dst' : str(new_dir)
                        ,'perms' : 'ug+rx,o-rwx' #used for --chmod; can be prefixed with D for directories or F for files
                        }
        cmd_text = ['/usr/bin/rsync'
#                     ,'-rltvz', '--progress', '--stats'
                    ,'--recursive'
                    ,'--links'
                    ,'--times'
                    ,'--verbose'
                    ,'--compress'
                    ,'--chmod{}'.format(rsync_kwargs['perms'])
                    ,'--link-dest={}'.format(rsync_kwargs['link_dir'])
                    ,'--exclude-from={}'.format(rsync_kwargs['clude_file'])
                    ,'--log-file={}'.format(rsync_kwargs['log_file'])
                    ,rsync_kwargs['backup_src']
                    ,rsync_kwargs['backup_dst']
                    ]

        rsync_output = subprocess.Popen(cmd_text, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print(rsync_output.communicate())
    
    #ensure mount point is available
    mounts = subprocess.check_output(['cat','/proc/mounts']
                                     ,stderr = subprocess.PIPE
                                     ).decode('utf8')
    regex_host_mount = re.compile(r'(//{0}/\w+\$?) (/mnt/{0})'.format(host))
    if regex_host_mount.search(mounts): #mount point exists, continue with backup
        retval = perform_backup()
    else: #attempt to mount
        cmd_text = ['mount','{}'.format(str(host_root_dst_dir))]
        proc_mount = subprocess.Popen(cmd_text, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
        _ = proc_mount.communicate()
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
                            ,usage='{} host --aggressive --verbose'.format(sys.argv[0])
                            )
    parser.add_argument('host', help='host from which to pull backup')
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
                print('timeout waiting for {} to wake'.format(args.host), file=sys.stderr)
        else:
            print('wake command failed', file=sys.stderr)

if __name__ == "__main__":
    sys.exit(main())
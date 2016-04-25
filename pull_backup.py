#!/bin/python3.3

from argparse import ArgumentParser
import os
import re
import shutil
import subprocess
import sys
import time

from utilities import timer

HOST = None
BACKUP_COUNT = 21 #(3 weeks)
BACKUP_ROOT = '/backups'
VERBOSE = False
MAC_ADDRS = {
             'lianli':'00:03:47:f8:7d:b1'
             }
WAS_OFF = None


def run_backup(host, wait = 0):
    int_perms=664 #used in mkdir
    def perform_backup():
        time.sleep(wait)
        os.chdir(backup_root)
        shuffle_dirs()
        os.mkdir(target_dir, int_perms)
        shutil.copy('cludes',target_dir + '/') #capture cludes file for backup validation
        rsync()
        os.utime(target_dir, None) #update timestamp of newest directory
        return (True, "Ran to completion")

    #ensure mount point is available
    mounts = subprocess.check_output(['cat','/proc/mounts'], stderr = subprocess.PIPE)
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

def shuffle_dirs():
    base_dir = HOST
    last_dir = '{0}.{1}'.format(base_dir,str(backup_count)) #last directory to keep
    if VERBOSE:
        print("Shuffling dirs")
    #iterate backward from back up count to rename dirs
    for i in range(BACKUP_COUNT, -1, -1):
        d = base_dir + '.' + str(i).zfill(2)
        if os.access(d, os.F_OK):
            if d == last_dir:
                shutil.rmtree(d) #remove oldest directory, if exists
            else:
                shutil.move(d, base_dir + '.' + str(i + 1).zfill(2))

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
    rsync = '/bin/rsync'
    backup_src = '/mnt/lianli/'
    target_dir = '{0}/{1}.00'.format(backup_root,base_dir) #newest directory
    link_dest = '{0}/{1}{2}.01'.format(backup_root,base_dir)
    log_file = '{0}/{1}'.format(backup_root,'log')
    clude_file = '{0}/{1}'.format(backup_root,'cludes')
    perms = "ug+rx,o-rwx" #used for --chmod; can be prefixed with D for directories or F for files
    rsync_kwargs = {'link_dest' : ''
                    ,'clude_file' : ''
                    ,'log_file' : ''
                    ,'backup_src' : ''
                    ,'target_dir' : ''
                    ,'perms' : ''
                    }
    cmd_text = ['rsync', '-rltvz', '--progress', '--stats'
                ,'--chmod {}'.format(rsync_kwargs['perms'])
                ,'--link-dest={}'.format(rsync_kwargs['link_dest'])
                ,'--exclude-from={}'.format(rsync_kwargs['clude_file'])
                ,'--log-file={2} {3} {4}'
                ]
    #.format(link_dest,clude_file,log_file,backup_src,target_dir,perms)
    #os.system('rsync -rltvz --progress --stats --chmod {5} --link-dest={0} --exclude-from={1} --log-file={2} {3} {4}'.format(link_dest,clude_file,log_file,backup_src,target_dir,perms))
    rsync_output = 

# def main(host):
#     sleepTimer = 5
#     waitTimer = 600 #wait seconds for host to wake
#     if not is_alive(host): #machine is not alive
#         WAS_OFF = True
#         print("{0} not online".format(host))
#         wakeCode, wakeMsg = wake_machine(MAC_ADDRS[host])
#         if wakeCode: #wake signal has been sent successfully
#             timeStart = time.time()
#             while (time.time() - timeStart) < waitTimer: #still time left
#                 if is_alive(host): #host has responded
#                     retVal = run_backup(host, wait=60) #host has just woken, allow it to get bearings (rise and shine)
#                     break
#                 else:
#                     time.sleep(sleepTimer)
#             else: #timed out
#                 print("Exiting. {0} has not awoke timely.".format(host))
#                 retVal = (False, "{0} is not alive".format(host))
#         else: #wake signal not sent
#             retVal = (False, wakeMsg)
#     else:
#         WAS_OFF = False
#         retVal = run_backup(host) #host already alive, immediately begin backup
# #     else:
# #         with open(log_file, 'a') as f:
# #             f.write("{0} Unable to contact {1}\n".format(time.strftime('%Y/%m/%d %H:%M:%S'),host))
# #         retVal = (False, "Error logged")
# 
#     print("main returns: {0} for host {1}".format(retVal, host))
#     return retVal

def main():
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
    timer_is_alive = timer(is_alive, run_until=True, verbose=True)
    timer_is_dead = timer(is_alive, run_until=False, verbose=True)
    if is_alive(args.host): #host online
        WAS_OFF = False
        backup_retval = run_backup(args.host, wait=30)
    elif args.aggressive: #host offline and we need to wake
        WAS_OFF = True
        if wake_machine(MAC_ADDRS[args.host]):
            alive_retval = timer_is_alive(args.host)
            if alive_retval: #host now online
                backup_retval = run_backup(args.host, wait=30)
                if shutdown(args.host):
                    if timer_is_dead(args.host):
                        print('{} is dead'.format(args.host))
                    else:
                        print('{} is not killable'.format(args.host))
                else:
                    print('shutdown failed', file=sys.stderr)
        else:
            print('{} is not wakeable'.format(args.host), file=sys.stderr)

if __name__ == "__main__":
    sys.exit(main())
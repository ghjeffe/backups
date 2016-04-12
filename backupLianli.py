#!/bin/python3.3

import os, shutil, time, re
import subprocess



### VARIABLES
backupCount = 21 #(3 weeks)
backupDst = '/backups'
backupSrc = '/mnt/lianli/'
rsync = '/bin/rsync'
baseDir = 'lianli'
lastDir = '{0}.{1}'.format(baseDir,str(backupCount)) #last directory to keep
targetDir = '{0}/{1}{2}'.format(backupDst,baseDir,'.00') #newest directory
linkDest = '{0}/{1}{2}'.format(backupDst,baseDir,'.01')
logFile = '{0}/{1}'.format(backupDst,'log')
cludeFile = '{0}/{1}'.format(backupDst,'cludes')
perms = "ug+rx,o-rwx" #used for --chmod; can be prefixed with D for directories or F for files
intPerms=664 #used in mkdir 
macs = {
    'lianli':'00:03:47:f8:7d:b1'
    }
WAS_OFF = None


def _timer(func, timeout=600, interval=5, run_until=True, verbose=False):
    '''run func for timeout seconds or until run_until every interval'''
    def inner(*args, **kwargs):
        time_start = time.time()
        time_end = time_start + timeout
        last_run = ''
        while time.time() < time_end:
            try:
                retval = func(*args, **kwargs)
                last_run = time.time()
            except TypeError as e:
                raise e
            if retval != run_until:
                if verbose:
                    print('{}({}) returns {} @ {}'.format(
                                                     func.__name__
                                                     ,(args, kwargs)
                                                     ,retval
                                                     ,time.time()
                                                     )
                          )
                time.sleep(interval)
            else:
                return (time_start, last_run)
    return inner

def runBackup(host, wait = 0):
    def performBackup():
        time.sleep(wait)
        os.chdir(backupDst)
        shuffle()
        os.mkdir(targetDir, intPerms)
        shutil.copy('cludes',targetDir + '/') #capture cludes file for backup validation
        rsync()
        os.utime(targetDir, None) #update timestamp of newest directory
        return (True, "Ran to completion")

    #ensure mount point is available
    proc = subprocess.Popen(['cat','/proc/mounts'], stdout = subprocess.PIPE, stderr = subprocess.PIPE)
    out, err = proc.communicate()
    strOut = str(out)
    regex = re.compile(r'(//{0}/\w+\$?) (/mnt/{0})'.format(host))
    if regex.search(strOut): #mount point exists, continue with backup
        retVal = performBackup()
    else: #attempt to mount
        cmdText = ['mount','/mnt/' + host]
        mount = subprocess.Popen(cmdText, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
        out, err = mount.communicate()
        if mount.returncode == 0:
            retVal = performBackup()
        else: #unable to mount filesystem to perform backup, must exit
            retVal = (False, "Unable to mount filesystem")

    print(retVal)
    return retVal

def shuffle():
    print("Shuffling dirs")
    for i in range(backupCount, -1, -1):
        d = baseDir + '.' + str(i).zfill(2)
        if os.access(d, os.F_OK):
            if d == lastDir:
                shutil.rmtree(d) #remove oldest directory, if exists
            else:
                shutil.move(d, baseDir + '.' + str(i + 1).zfill(2))

def shutdown(host):
    #Shutdown of remote machine succeeded
    cmd_text = ['net','rpc','shutdown','-I',host,'-U','ghjeffeii%'.format(pw)]
    regex_pw = re.compile('<?=password=)\w*')
    pw = regex_pw.search(regex_pw, open('/home/ghjeffeii/.smbcreds', mode='r', encoding='utf8'))
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

def wakeMachine(macAddr):
    try:
        proc = subprocess.Popen(['/bin/wol',macAddr]
                                ,stdout=subprocess.PIPE
                                ,stderr=subprocess.PIPE
                                )
        out = proc.communicate()
        strOut = str(out)
        if "Waking" in strOut:
            retVal = (True, "Success")
        if "Cannot assemble" in strOut:
            retVal = (False, "Improper MAC format")
    except OSError:
        retVal = (False, "wol command not found in /bin")

    print("Wake: {0}".format(retVal))
    return retVal

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
    os.system('rsync -rltvz --progress --stats --chmod {5} --link-dest={0} --exclude-from={1} --log-file={2} {3} {4}'.format(linkDest,cludeFile,logFile,backupSrc,targetDir,perms))

def main(host):
    sleepTimer = 5
    waitTimer = 600 #wait seconds for host to wake
    if not is_alive(host): #machine is not alive
        WAS_OFF = True
        print("{0} not online".format(host))
        wakeCode, wakeMsg = wakeMachine(macs[host])
        if wakeCode: #wake signal has been sent successfully
            timeStart = time.time()
            while (time.time() - timeStart) < waitTimer: #still time left
                if is_alive(host): #host has responded
                    retVal = runBackup(host, wait=60) #host has just woken, allow it to get bearings (rise and shine)
                    break
                else:
                    time.sleep(sleepTimer)
            else: #timed out
                print("Exiting. {0} has not awoke timely.".format(host))
                retVal = (False, "{0} is not alive".format(host))
        else: #wake signal not sent
            retVal = (False, wakeMsg)
    else:
        WAS_OFF = False
        retVal = runBackup(host) #host already alive, immediately begin backup
#     else:
#         with open(logFile, 'a') as f:
#             f.write("{0} Unable to contact {1}\n".format(time.strftime('%Y/%m/%d %H:%M:%S'),host))
#         retVal = (False, "Error logged")

    print("main returns: {0} for host {1}".format(retVal, host))
    return retVal

if __name__ == "__main__":
    host = 'lianli'
    main(host)
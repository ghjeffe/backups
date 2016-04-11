#!/bin/python3.3

import argparse
import os
import shutil
import subprocess as sp
import sys
import time

#GLOBALS
BACKUP_COUNT = 21 #(3 weeks)
BACKUP_DEST_ROOT = '/backups'

def runBackup(host, wait = 0):
    dest_dir_perms = 664
    host_backup_root = os.path.join(BACKUP_DEST_ROOT, host)
    was_mounted = os.path.ismount(host_backup_root)
    path_mount = '/usr/bin/mount'
    path_rsync = '/usr/bin/rsync'

    def shuffle():
        rsync_target_dir = os.path.join(host_backup_root, '{}.00'.format(host)) #dir where rsync writes to
        rsync_link_dest = os.path.join(host_backup_root, '{}.01'.format(host)) #used for --link-dest option to create hard links
        last_dir_to_keep = os.path.join(host_backup_root
                                        , '{}.{}'.format(host, str(BACKUP_COUNT)))
        host_log_file = os.path.join(host_backup_root, 'backup.log')
        clude_file = os.path.join(host_backup_root, 'cludes')
    
        print("Shuffling dirs")
        for i in range(BACKUP_COUNT, -1, -1):
            d = baseDir + '.' + str(i).zfill(2)
            if os.access(d, os.W_OK): #os.W_OK = ensure we can write to dir
                if d == last_dir_to_keep:
                    shutil.rmtree(d) #remove oldest directory, if exists
                else:
                    shutil.move(d, baseDir + '.' + str(i + 1).zfill(2))
    
    def performBackup():
        time.sleep(wait)
        os.chdir(host_backup_root)
        shuffle(host_backup_root)
        os.mkdir(rsync_target_dir, dest_dir_perms)
        shutil.copy('cludes',rsync_target_dir + '/') #capture cludes file for backup validation
        rsync() #TODO: capture return value and react appropriately
        os.utime(rsync_target_dir, None) #update timestamp of newest directory
        return (True, "Ran to completion")

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
        perms = "ug+rx,o-rwx" #used for --chmod; can be prefixed with D for directories or F for files
        os.system('rsync -rltvz --progress --stats --chmod {5} --link-dest={0}\
                    --exclude-from={1} --log-file={2} {3} {4}'.format(
                    linkDest, clude_file, host_log_file, backupSrc, rsync_target_dir, perms
                    )
                  )

    
    #ensure mount point is available
 
    if was_mounted:
        retVal = performBackup()
    else: #attempt to mount
        cmd_mount = [path_mount, host_backup_root]
        proc_mount = sp.Popen(cmd_mount, stdout = sp.PIPE, stderr = sp.PIPE)
        out, err = proc_mount.communicate()
        if proc_mount.returncode == 0:
            retVal = performBackup()
        else: #unable to mount filesystem to perform backup, must exit
            retVal = (False, "Unable to mount filesystem")
    print(retVal)
    return retVal

def isAlive(host, attempts = 1):
    out = ""
    proc = sp.Popen(['ping', '-c', str(attempts), host], stdout = sp.PIPE, stderr = sp.PIPE)
    out = out + str(proc.communicate())
    
    if 'ttl' in out:
        retVal = (True, "{0} is alive".format(host))
    else:
        retVal = (False, "{0} is not alive".format(host))
        
    print(retVal)
    return retVal


def wakeMachine(macAddr):
    macs = {
        'lianli':'00:03:47:f8:7d:b1'
        }

    try:
        proc = sp.Popen(['/bin/wol',macAddr], stdout = sp.PIPE, stderr = sp.PIPE)
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

def main():
    parser = argparse.ArgumentParser(usage='{} host'.format(sys.argv[0]))
    parser.add_argument('host', help='Host to pull backups from')
    host = parser.parse_args().host
    sleepTimer = 5
    waitTimer = 600 #wait seconds for host to wake
    aliveCode, aliveMsg = isAlive(host)
    if not aliveCode: #machine is not alive
        print("{} not online".format(host))
        wakeCode, wakeMsg = wakeMachine(macs[host])
        if wakeCode: #wake signal has been sent successfully
            timeStart = time.time()
            while (time.time() - timeStart < waitTimer): #still time left
                if not aliveCode: #no response from host
                    aliveCode, aliveMsg = isAlive(host)
                    time.sleep(sleepTimer)
                elif aliveCode: #host has responded
                    retVal = runBackup(host, wait = 20) #host has just woken, allow it to get bearings (rise and shine)
                    break
            else: #timed out
                print("Exiting. {0} unwakeable.".format(host))
                retVal = (False, "{0} is not alive".format(host))
        else: #wake signal not sent
            retVal = (False, wakeMsg)
    elif aliveCode:
        retVal = runBackup(host) #host already alive, immediately begin backup
    else:
        with open(host_log_file, 'a') as f:
            f.write("{0} Unable to contact {1}\n".format(strftime('%Y/%m/%d %H:%M:%S'),host))
        retVal = (False, "Error logged")

    print("main returns: {0} for host {1}".format(retVal, host))
    return retVal

if __name__ == "__main__":
    sys.exit(main())
#!/bin/python3.3
''' pull backups from specified host '''
#written by Gary H Jeffers II
#===============================================================================
# v0.1.3.1 (7/28/2016)
# TODO:
#     -capture rsync output and send to admin
#===============================================================================

from argparse import ArgumentParser
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import time

from net_tools import pinger
from utilities import timer, shutdown
from wakeonlan import wol

BACKUP_COUNT = None
BACKUP_DST_ROOT = None
BACKUP_SRC_ROOT = None
VERBOSE = False

def conditional_print(msg):
    if VERBOSE:
        print(msg)

def run_backup(host, verbose=False, wait=0):
    host_root_src_dir = BACKUP_SRC_ROOT.joinpath(host)
    host_root_dst_dir = BACKUP_DST_ROOT.joinpath(host)
    dir_perms = 664 #used in mkdir
    dir_pad = 0 #character used to left-pad newer directories to ensure consistent lengths (01 vs 21)
    backup_dir_fmt = '{host}.{suffix:{pad}>{width}}'
    fmt_buckets = {'host':''
                   ,'suffix':''
                   ,'pad':dir_pad
                   ,'width':len(str(BACKUP_COUNT))
                   } #passed into backup_dir_fmt to match host dirs for link_dirs
    link_dirs = [] #holds list of links for rsync to use for link-dest arg
    os.chdir(str(host_root_dst_dir))
    
    #newest backup will go here
    new_dir = host_root_dst_dir.joinpath(backup_dir_fmt.format(host=host
                                               ,suffix=0
                                               ,pad=dir_pad
                                               ,width=len(str(BACKUP_COUNT))
                                               )
                                         )
    
    def get_link_dirs(dst_dir=host_root_dst_dir):
        items = []
        for item in os.listdir(dst_dir):
            base, suff, *_ = item.split('.')
            if (
                base == host
                and suff.isnumeric()
                and int(suff) < BACKUP_COUNT and int(suff) > 0
                ):
                items.append('--link-dest={}'.format(item))
        return items

    def shuffle_dirs():
        conditional_print('shuffling dirs')
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
                backup_dir.rename(backup_dir_fmt.format(host=base
                                                        ,suffix=int(extn) + 1
                                                        ,pad=0
                                                        ,width=len(str(BACKUP_COUNT))
                                                        )
                                  )
        new_dir.mkdir(mode=dir_perms)
    
    def perform_backup():
        time.sleep(wait)
        shuffle_dirs()
        link_dirs = get_link_dirs()
        shutil.copy('cludes', str(new_dir) + '/') #capture cludes file for backup validation
        rsync()
        new_dir.touch() #update timestamp of newest directory
        return True

    def rsync():
        rsync_kwargs = {
                        'rsync_cmd' : '/usr/bin/rsync'
                        ,'link_dirs' : str(link_dirs)
                        ,'clude_file' : os.path.join(str(host_root_dst_dir), 'cludes')
                        ,'log_file' : os.path.join(str(host_root_dst_dir), 'backup.log')
                        ,'backup_src' : str('{}/'.format(host_root_src_dir))
                        ,'backup_dst' : str(new_dir)
                        ,'perms' : 'Dug-w,o-rwx,Fug-wx,o-rws' #used for --chmod; can be prefixed with D for directories or F for files
                        }
        rsync_cmd_text = ['/usr/bin/rsync'
                    ,'--recursive'
                    ,'--links'
                    ,'--times'
                    ,'--verbose'
                    ,'--compress'
                    ,'--chmod={}'.format(rsync_kwargs['perms'])
                    ]
        rsync_cmd_text(link_dirs)
        rsync_cmd_text(['--exclude-from={}'.format(rsync_kwargs['clude_file'])
                        ,'--log-file={}'.format(rsync_kwargs['log_file'])
                        ,rsync_kwargs['backup_src']
                        ,rsync_kwargs['backup_dst']
                        ])

        conditional_print('dir {} before rsync call: {}'.format(os.getcwd(), os.listdir()))
        conditional_print('calling rsync with these args:\n{}'.format(rsync_cmd_text))
        rsync_cmd = subprocess.Popen(rsync_cmd_text, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        rsync_output = rsync_cmd.communicate()
    
    #ensure mount point is available
    mounts = subprocess.check_output(['cat','/proc/mounts']
                                     ,stderr = subprocess.PIPE
                                     ).decode('utf8')
    regex_host_mount = re.compile(r'(//{0}/\w+\$?) (/mnt/{0})'.format(host))
    if regex_host_mount.search(mounts): #mount point exists, continue with backup
        conditional_print('calling perform_backup')
        retval = perform_backup()
    else: #attempt to mount
        cmd_text = ['mount','{}'.format(str(host_root_src_dir))]
        conditional_print('attempting to mount')
        proc_mount = subprocess.Popen(cmd_text, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
        _ = proc_mount.communicate()
        if proc_mount.returncode == 0:
            conditional_print('mount succeeded, calling perform_backup')
            retval = perform_backup()
        else: #unable to mount filesystem to perform backup, must exit
            retval = False
    return retval
    
def main():
    was_off = False #was machine off before script began; initialize False
    
    #set up CLI
    mode_choices = {'wakeshut': 'wake and shut off host'
                    ,'wakenoshut': 'wake target host and leave it on'
                    ,'nowakenoshut': 'don\'t wake or shut host'
                    ,'wakeshutnice': 'wake and if target was off before waking, shut it off'
                    }
    parser = argparse.ArgumentParser(
                                     prog='pull_backup'
                                     ,description='Pull backup from specified host, waking and shutting if desired'
                                     )
    parser.add_argument('host', help='host from which to pull backup')
    parser.add_argument('--verbose'
                        ,help='set for print statements'
                        ,action='store_true' #false by default
                        )
    parser.add_argument('--alive_mode'
                        ,choices=mode_choices.keys()
                        ,help=''.join(('{} = {}\n'.format(choice, desc)) for choice, desc in mode_choices.items()))

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

    #parse config file
    try:
        fh = open('conf/app_config.json')
    except (FileNotFoundError, PermissionError):
        #unable to read config
        #TODO: decide what to do when config file isnt present
        pass
    else:
        conf = json.load(fh)
        BACKUP_COUNT = conf['hosts'][args.host].get('backup_count', conf['backup_count'])
        BACKUP_SRC_ROOT = conf.get('backup_src_root', None)
        BACKUP_DST_ROOT = conf.get('backup_dst_root', None)
        mac_addr = conf['hosts'][args.host].get('mac_addr', None)
        alive_mode = args.alive_mode if args.alive_mode else conf['hosts'].get(args.host, {}).get('alive_mode', conf.get('alive_mode', 'nowakenoshut'))
        VERBOSE = args.verbose
    finally:
        try:
            fh.close()
        except:
            pass

    if pinger(args.host).reply: #host online
        conditional_print('{} is alive, calling run_backup'.format(args.host))
        backup_retval = run_backup(args.host, verbose=args.verbose)
    elif mode[:4] == 'wake': #host offline and we need to wake
        was_off = True
        try:
            wol.send_magic_packet(mac_addr)
        except ValueError:
            #TODO: mac_addr improperly formatted; log this and exit
            pass
        else:
            alive_retval = timer_host_alive(args.host)
            if alive_retval: #host now online
                backup_retval = run_backup(args.host, wait=30, verbose=args.verbose)
                if (mode == 'wakeshut'
                    or (was_off and mode == 'wakeshutnice')
                    ):  
                    if shutdown(args.host):
                        retval_host_dead = timer_host_dead(args.host) 
                        if retval_host_dead:
                            conditional_print(
                              '{} is dead; duration: {}'.format(
                                                                args.host
                                                                ,retval_host_dead
                                                                )
                                              )
                        else:
                            print('{} is not killable'.format(args.host))
                    else:
                        print('shutdown failed') #, file=sys.stderr)
            else:
                print('timeout waiting for {} to wake'.format(args.host))#, file=sys.stderr)

def main_test():
#     run_backup('lianli', verbose=True)
    conditional_print('testing')

if __name__ == "__main__":
    sys.exit(main_test())

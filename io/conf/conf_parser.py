import json
import os

def get_config(host):
    ''' return flattened version of config for easier parsing '''
    
    #initialize defaults in case config file is absent
    host_config = {'globals': {
                               'backup_count': 21
                               ,'alive_mode': 'nowakenoshut'
                               ,'backup_src_root': '/backups'
                               ,'backup_dst_root': '/mnt'
                               }
                   }
    try:
        fh = open('conf/app_config.json')
    except (FileNotFoundError, PermissionError):
        #we don't care if config isn't present since we've initialized required
        #values already
        pass
    else:
        conf = json.load(fh)
        for k, v in conf['globals'].items():
            host_config[k] = v
            
        #override defaults with host-level settings
        for k, v in conf['hosts'][host].items():
            if v:
                host_config[k] = v
    finally:
        try:
            fh.close()
        except:
            pass
        return host_config
import time

def timer(func, timeout=600, interval=5, run_until=True, verbose=False):
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
        
def parse_rsync_output():
'''
sending incremental file list
./

Number of files: 15746
Number of files transferred: 0
Total file size: 138395205727 bytes
Total transferred file size: 0 bytes
Literal data: 0 bytes
Matched data: 0 bytes
File list size: 268765
File list generation time: 0.009 seconds
File list transfer time: 0.000 seconds
Total bytes sent: 269674
Total bytes received: 908

sent 269674 bytes  received 908 bytes  18660.83 bytes/sec
total size is 138395205727  speedup is 511472.33
'''
    pass

def pretend(func):
    def inner(*args, **kwargs):
        wait = kwargs.setdefault('wait', 0)
        print('pretended to run {}, sleeping {}'.format(
                                                        func.__name__
                                                        ,wait
                                                        )
              )
        time.sleep(wait)
    return inner
import re
import subprocess
import time

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
        
def is_alive(host, attempts = 1):
    cmd_text = ['ping', '-w', '.1', '-c', str(attempts), host]
    try:
        proc_ping = subprocess.check_output(cmd_text, timeout=.5)
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
        return False
    else:
        return True if 'ttl' in proc_ping.decode('utf8').lower() else False
    
def shutdown(host):
    #Shutdown of remote machine succeeded
    regex_pw = re.compile('(?<=password=)\w*')
    pw = regex_pw.search(open(
                              '/home/ghjeffeii/.smbcreds'
                              ,mode='r'
                              ,encoding='utf8'
                              ).read()
                         ).group()
    cmd_text = ['net','rpc','shutdown','-I',host,'-U','ghjeffeii%{}'.format(pw)]
    proc_shutdown = subprocess.check_output(cmd_text, timeout=5)
    if 'succeeded' in proc_shutdown.decode('utf8').lower():
        return True
    else:
        return False

host = 'lianli'
timer_alive_true_verb = _timer(is_alive, run_until=True, verbose=True)
timer_alive_false_verb = _timer(is_alive, run_until=False, verbose=True)
ret_shut = shutdown(host)
ret_alive = timer_alive_true_verb(host)
if ret_alive is not None:
    print('{} successfully shutdown at {}'.format(host, ret_alive[1]))

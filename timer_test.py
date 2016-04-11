import subprocess as sp
import time

def _timer(func, timeout=600, interval=5, run_until=True, verbose=False):
    '''run func for timeout seconds or until run_until every interval'''
    def inner(*args, **kwargs):
        time_start = time.time()
        time_end = time_start + timeout
        while time.time() < time_end:
            try:
                retval = func(*args, **kwargs)
            except TypeError as e:
                raise e
            if retval != run_until:
                if verbose:
                    print('{}({}) returns {} @ {}'.format(
                                                     func.__name__
                                                     ,kwargs
                                                     ,retval
                                                     ,time.time()
                                                     )
                          )
                time.sleep(interval)
            else:
                return retval
    return inner
        
def is_alive(host, attempts = 1):
    try:
        proc_ping = sp.check_output(
                                    ['ping', '-w', '.1', '-c', str(attempts), host]
                                    ,timeout=.5
                                    )
    except:
        return False
    else:
        return True if 'ttl' in proc_ping.decode('utf8').lower() else False

timer_is_alive = _timer(is_alive, run_until=True)
retval = timer_is_alive(host='lianli')
print(retval)

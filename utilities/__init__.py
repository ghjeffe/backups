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
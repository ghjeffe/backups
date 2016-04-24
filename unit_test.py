import pull_backup
import time


def main():
    host = 'lianli'
    timer_is_alive = pull_backup._timer(pull_backup.is_alive, run_until=True, verbose=True)
    timer_is_dead = pull_backup._timer(pull_backup.is_alive, run_until=False, verbose=True)
    if pull_backup.is_alive(host):
        WAS_OFF = False
        # RUN BACKUP HERE
        print('running backup')
    else:
        WAS_OFF = True
    if WAS_OFF:
        pull_backup.wakeMachine('00:03:47:f8:7d:b1')
        alive_retval = timer_is_alive(host)
        if alive_retval:
            print('{} is now alive'.format(host), alive_retval)
            print('running backup')
            time.sleep(30)
            # RUN BACKUP HERE
            print('backup complete')
            if WAS_OFF:
                if pull_backup.shutdown(host):
                    print('shutdown signal sent to {}'.format(host))
                    dead_retval = timer_is_dead('{}'.format(host))
                    if dead_retval:
                        print('{} is dead'.format(host))
                    else:
                        print('{} is not killable'.format(host))
                else:
                    print('shutdown failed')
        else:
            print('{} is not wakeable'.format(host))
main()

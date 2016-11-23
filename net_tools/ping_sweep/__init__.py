#!python3
'''multi-threaded ping sweep'''
#created by Gary H Jeffers II
#v0.2.0 5/17/2016 16:21
#===============================================================================
# CHANGELOG:
#     v0.2.0:
#         -added error handling in get_hosts() for file not found
#         -modified file output to only include host, not entire tuple
#===============================================================================

from argparse import ArgumentParser
from concurrent.futures import ThreadPoolExecutor
import concurrent.futures
from functools import partial
import ipaddress
import sys
import time

from net_tools import pinger #, get_hostname


THREAD_LIMIT = 50
TIME_FMT = '%H:%M:%S'

def get_hosts(hosts):
    try: #is target a subnet
        net1 = ipaddress.IPv4Network(hosts)
        for host in net1.hosts():
            yield host.exploded #returns address as string, as opposed to object
    except ipaddress.AddressValueError: #target is not a subnet 
        try:
            for line in open(hosts, mode='r', encoding='utf8'):
                yield line.strip('\r\n" ')
        except FileNotFoundError: #TODO: this should probably be caught elsewhere, like main()
            print('File \'{}\' not found. Please specify an input file with one host per line to ping.'.format(hosts), file=sys.stderr)
            sys.exit(1)
        except:
            raise

def run_pings(target, **kwargs):
    to_do = []
    results = []
    with ThreadPoolExecutor(THREAD_LIMIT) as tpe:
        pinger_custom = partial(pinger
                                ,count=kwargs.get('count', 1)
                                ,pad_addr=kwargs.get('pad_addr', False)
                                )
        
        for host in get_hosts(target):
            future = tpe.submit(pinger_custom, host)
            to_do.append(future)
            
        for future in concurrent.futures.as_completed(to_do):
            if kwargs.get('verbose', False):
                print(future.result())
            results.append(future.result())
        
        return results

def main():
    alive_count = 0
    fh_replies = ''
    fh_no_replies = ''
    parser = ArgumentParser(
                            usage=(
                                   'ping_sweep'
                                   ' {filename | subnet}'
                                   ' [--write-to-files | --append-to-files]' 
                                   ' --count --pad-addr  --replies-only'
                                   )
                            ,description='multi-threaded ping to ping hosts from subnet or hosts.txt file'
                            )
     
    parser.add_argument('target', help='filename with hosts listed per line or subnet (slash notation)')
    parser.add_argument('--count', help='number of echoes to send to each machine', default='1')
    parser.add_argument(
                        '--pad-addr'
                        ,help='pad ip addresses with leading zeroes for better sorting'
                        ,action='store_true'
                        )
    parser.add_argument('--replies-only', help='on console, only show replies', action='store_true')
    file_group = parser.add_mutually_exclusive_group()
    file_group.add_argument('--write-to-files'
                            ,help='write results to replies/failures files'
                            ,action='store_true'
                            )
    file_group.add_argument('--append-to-files'
                            ,help='append results to replies/failures files, or create if not present'
                            ,action='store_true'
                            )
    #TODO: add args for reverse lookup of addr to get host via net_tools.get_hostname()

    args = parser.parse_args()
    start_time = time.time()
    print('sweep started at: {}\n'.format(time.strftime(TIME_FMT, time.localtime())))
    results = run_pings(
                        args.target
                       ,pad_addr=args.pad_addr
                       ,count=args.count
                       ,verbose=not args.replies_only
                       )
    if args.write_to_files or args.append_to_files:
        reply_file = 'replies.out'
        no_reply_file = 'no-replies.out'
        if args.write_to_files:
            mode = 'w'
        else:
            mode = 'a'
        fh_replies = open(reply_file, mode=mode)
        fh_no_replies = open(no_reply_file, mode=mode)

    end_time = time.time()
#     print('\n{}REPLIES\n'.format(len(results)))
    print('\nREPLIES FROM\n')
    for result in sorted(results, key=lambda x: x[0]):
        output = result.host if result.host else result.addr
        if result.reply:
            print(result)
            alive_count += 1
            if fh_replies:
                try:
                    fh_replies.write('{}\n'.format(output))
                except:
                    pass
        else:
            if fh_no_replies:
                try:
                    fh_no_replies.write('{}\n'.format(output))
                except:
                    pass
             
    print(('\nstart: {}\n'
           'end: {}\n'
           'duration: {:.4f}\n'
           'replies: {}/{}'
           ).format(
                    time.strftime(
                                  TIME_FMT
                                  ,time.localtime(start_time)
                                  )
                    ,time.strftime(
                                   TIME_FMT
                                   ,time.localtime(end_time)
                                   )
                    ,end_time - start_time
                    ,alive_count
                    ,len(results)
                    )
          )
    
    return 1
if __name__ == '__main__':
    sys.exit(main())

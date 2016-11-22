import argparse
import pathlib


parser = argparse.ArgumentParser(description='Pull backup for specified host, waking and shutting if desired'
                        ,usage='pull_backup host [mode {wakeshut | wakenoshut}] [--verbose]')
parser.add_argument('host', help='host from which to pull backup')
subparser = parser.add_subparsers(title='subcommands')
mode_parser = subparser.add_parser('mode', help='wake and/or shut machine')
parser.add_argument('--verbose'
                    ,help='set for print statements'
                    ,action='store_true' #false by default
                    )
mode_parser.add_argument('mode'
                         ,choices=['wakeshut', 'wakenoshut', 'nowakenoshut']
                         ,help='''wakeshut = wake and shut target host
                             wakenoshut = wake target host
                             nowakenoshut = don't wake or shut host'''
                         ,default='nowakenoshut'
                         )
    
args = parser.parse_args()
print(args)
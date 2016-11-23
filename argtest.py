import argparse
import pathlib


#set up CLI
mode_choices = {'wakeshut': 'wake and shut off host'
                ,'wakenoshut': 'wake target host and leave it on'
                ,'nowakenoshut': 'don\'t wake or shut host'
                ,'wakeshutnice': 'wake and if target was off before waking, shut it off'
                }
usage = ('pull_backup host [--verbose] [mode {}]'.format(('{} | ' * len(mode_choices))[:-3])).format(*mode_choices)
parser = argparse.ArgumentParser(
                                 description='Pull backup for specified host, waking and shutting if desired'
#                                  ,usage=usage
                                 )
parser.add_argument('host', help='host from which to pull backup')
parser.add_argument('--verbose'
                    ,help='set for print statements'
                    ,action='store_true' #false by default
                    )
parser.add_argument('--mode'
                         ,choices=mode_choices.keys()
                         ,help=''.join(('{} = {}\n'.format(choice, desc)) for choice, desc in mode_choices.items())
                         ,default='nowakenoshut'
                         )

print(parser.parse_args(['lianli', '--verbose']))
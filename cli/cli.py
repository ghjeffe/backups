import argparse
    
    #set up CLI
    alive_mode_choices = {'wakeshut': 'wake and shut off host'
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
    parser.add_argument('--alive-mode'
                        ,choices=alive_mode_choices.keys()
                        ,help=''.join(('{} = {}\n'.format(choice, desc)) for choice, desc in alive_mode_choices.items()))

    args = parser.parse_args()

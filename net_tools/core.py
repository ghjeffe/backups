#!python3

from collections import namedtuple
import re
import subprocess

STARTUP_CONFIG = subprocess.STARTUPINFO()
STARTUP_CONFIG.dwFlags |= subprocess.STARTF_USESHOWWINDOW

def pinger(dest, count=1, timeout=100, pad_addr=True):
    regex_dst_ip = re.compile('(?<!reply from )(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})')
#     regex_dst_wsn = re.compile('w[dnv]-[\w\d]{12}', re.IGNORECASE)
    regex_dst_stats = re.compile('Minimum = (\d*)ms, Maximum = (\d*)ms, Average = (\d*)ms', re.IGNORECASE)
    regex_no_host = re.compile('Ping request could not find host')
    Ping = namedtuple('Ping', ['addr', 'host', 'stats', 'count', 'reply'])
    ip_display_fmt = '{:03d}.{:03d}.{:03d}.{:03d}'
    cmd_text = ['ping', '-n', '1', '-w', str(timeout), dest]
    host = stats = addr = addr_padded = reply = ''
    iter_count = 0

    if regex_dst_ip.search(dest):
        addr = dest
    else:
        host = dest
    count = int(count)
    while iter_count < count and reply != True:
        try:
            proc_ping = subprocess.Popen(
                             cmd_text
                             ,stdout=subprocess.PIPE
                             ,stderr=subprocess.PIPE
                             ,startupinfo=STARTUP_CONFIG
                             )
        except: #ping command failed to run
            reply = None
        else: #ping command ran to completion
            output = proc_ping.communicate()[0].decode('utf8')
            if regex_no_host.search(output): #host not in DNS, exit early
                reply = False
                break
            ip_match = regex_dst_ip.search(output)

            #we might still be able to capture addr from output even if addr doesn't reply
            if ip_match:
                addr = ip_match.group() if not addr else addr

            if pad_addr and addr:
                addr_padded = ip_display_fmt.format(*[int(octet) for octet in addr.split('.')]) #pad octets with leading zeroes
                addr = addr_padded

            if proc_ping.returncode == 0: #received reply
                reply = True
                stats = tuple(int(stat) for stat in regex_dst_stats.search(output).group(1,2,3))
            else: #no reply received
                reply = False
        finally:
            iter_count += 1
    return Ping(addr, host, stats, iter_count, reply)

def get_hostname(addr):
    regex_hostname = re.compile('Name: *([\w\d.-]*)')
    cmd_text = ['nslookup', addr]
    try:
        output = subprocess.check_output(cmd_text, startupinfo=STARTUP_CONFIG).decode('cp1252')
        return regex_hostname.search(output).group(1)
    except:
        return ''
    
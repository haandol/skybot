"""
log.py: written by Scaevolus 2009
"""

from __future__ import with_statement

import os
import thread
import codecs
import time

import hook

lock = thread.allocate_lock()
log_fds = {} # '%(net)s %(chan)s' : (filename, fd)

timestamp_format = '%H:%M:%S'

formats = {'PRIVMSG': '<%(nick)s> %(msg)s',
    'PART': '-!- %(nick)s [%(user)s@%(host)s] has left %(chan)s',
    'JOIN': '-!- %(nick)s [%(user)s@%(host)s] has joined %(chan)s',
    'MODE': '-!- mode/%(chan)s [%(param_tail)s] by %(nick)s',
    'KICK': '-!- %(param1)s was kicked from %(chan)s by %(nick)s [%(msg)s]',
    'TOPIC': '-!- %(nick)s changed the topic of %(chan)s to: %(msg)s'
       }

ctcp_formats = {'ACTION': '* %(nick)s %(ctcpmsg)s'}

def get_log_filename(dir, network, chan):
    return os.path.join(dir, 'log', gmtime('%Y'), network,
            gmtime('%%s.%m-%d.log') % chan).lower()


def gmtime(format):
    return time.strftime(format, time.gmtime())


def beautify(input):
    format = formats.get(input.command, '%(raw)s')
    args = vars(input)
    leng = len(args['paraml'])
    for n, p in enumerate(args['paraml']):
        args['param' + str(n)] = p
        args['param_' + str(abs(n - leng))] = p

    args['param_tail'] = ' '.join(args['paraml'][1:])
    
    if input.command == 'PRIVMSG' and input.msg.count('\x01') >= 2:
        #ctcp
        ctcp = input.msg.split('\x01', 2)[1].split(' ', 1)
        if len(ctcp) == 1:
            ctcp += ['']
        args['ctcpcmd'], args['ctcpmsg'] = ctcp
        format = ctcp_formats.get(args['ctcpcmd'],
                '%(nick)s [%(user)s@%(host)s] requested unknown CTCP '
                '%(ctcpcmd)s from %(chan)s: %(ctcpmsg)s')

    return format % args


def get_log_fd(dir, network, chan):
    fn = get_log_filename(dir, network, chan)
    cache_key = '%s %s' % (network, chan)
    filename, fd = log_fds.get(cache_key, ('', 0))

    if fn != filename: # we need to open a file for writing
        if fd != 0: # is a valid fd
            fd.flush()
            fd.close()
        dir = os.path.split(fn)[0]
        if not os.path.exists(dir):
            os.makedirs(dir)
        fd = codecs.open(fn, 'a', 'utf-8')
        log_fds[cache_key] = (fn, fd)

    return fd


@hook.event(ignorebots=False)
def log(bot, input):
    ".remember <word> <data> -- maps word to data in the memory"
    with lock:
        timestamp = gmtime(timestamp_format)
        
        fd = get_log_fd(bot.persist_dir, bot.network, 'raw')
        fd.write(timestamp + ' ' + input.raw + '\n')

        if input.chan:
            fd = get_log_fd(bot.persist_dir, bot.network, input.chan)
            fd.write(timestamp + ' ' + beautify(input) + '\n')

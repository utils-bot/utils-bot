from logging import getLogger, StreamHandler, Formatter, DEBUG, INFO, WARNING, ERROR, CRITICAL
from typing import Literal
from configs import configurations
class CustomFormatter(Formatter):

    grey = "\x1b[38;20m"
    yellow = "\x1b[33;20m"
    red = "\x1b[31;20m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"
    format = "[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s"

    FORMATS = {
        DEBUG: grey + format + reset,
        INFO: grey + format + reset,
        WARNING: yellow + format + reset,
        ERROR: red + format + reset,
        CRITICAL: bold_red + format + reset
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = Formatter(fmt = log_fmt, datefmt='%Y-%m-%d %H:%M:%S')
        return formatter.format(record)

level = eval(configurations.logging_level.upper())
log = getLogger('internal')
log.setLevel(level)
ch = StreamHandler()
ch.setLevel(level)
ch.setFormatter(CustomFormatter())
log.addHandler(ch)

def ilog(msg: str, flag: str = '', logtype: Literal['debug', 'info', 'warning', 'error', 'critical'] = 'info'):
    logtype = logtype.lower()
    if logtype not in ['debug', 'info', 'warning', 'error', 'critical']: return
    printlog = log.info if logtype == 'info' else log.debug if logtype == 'debug' else log.warning if logtype == 'warning' else log.error if logtype == 'error' else log.critical if logtype == 'critical' else None
    fflag = ''
    if flag == '':
        pass
    else:
        for i in flag.split():
            fflag = fflag + f'[{i}] '
    msg = fflag + msg
    printlog(msg=msg)
if __name__ == '__main__':
    ilog('hello msg','flag1 flag2 flag3', 'critical')
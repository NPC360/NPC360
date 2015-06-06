"""
SETUP BASIC LOGGING
"""
# papertrail stuff from http://help.papertrailapp.com/kb/configuration/configuring-centralized-logging-from-python-apps/
import logging
import socket
from os import environ
import logging.handlers

#from logging.handlers import SysLogHandler

class ContextFilter(logging.Filter):
  hostname = socket.gethostname()

  def filter(self, record):
    record.hostname = ContextFilter.hostname
    return True

log = logging.getLogger()
log.setLevel(logging.DEBUG)
lf = logging.Formatter('%(asctime)s | %(levelname)s | %(message)s', datefmt='%Y-%m-%dT%H:%M:%S')

# paper trail handler
#ptcf = ContextFilter()
#log.addFilter(ptcf)
#pt = logging.handlers.SysLogHandler(address=('logs2.papertrailapp.com', 18620))
#pt.setFormatter(lf)
#log.addHandler(pt)

# file handler
#fh = logging.FileHandler('log/npc360.log')
#fh.setLevel(logging.DEBUG)
#fh.setFormatter(lf)
#log.addHandler(fh)

# console handler
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
ch.setFormatter(lf)
log.addHandler(ch)

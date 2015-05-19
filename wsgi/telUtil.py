"""
tel utils
"""

import twilio
import twilio.rest
from twilio.rest.lookups import TwilioLookupsClient
import twilio.twiml
import re

def getCountryCode(tel):
    tel = normalizeTel(tel)
    lookup = TwilioLookupsClient(environ['TSID'], environ['TTOKEN'])
    return lookup.phone_numbers.get(tel).country_code


def normalizeTel(tel):
    nTel = re.sub(r'[^a-zA-Z0-9\+]','', tel)
    return nTel

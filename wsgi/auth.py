"""
SMS auth methods
"""
from os import environ
from sqlalchemy import *
from sqlalchemy.exc import IntegrityError
from sqlalchemy.exc import CompileError
from iron_worker import *
import datetime

from telUtil import *
from game import getNPC, sendSMS
from logstuff import *

def signupSMSauth(tel,auth):
    # lookup admin NPC # for the user's country (this of course, assumes we have one)
    fnum = getNPC({ "country": getCountryCode(tel) }, 'admin')['tel']
    #msg = "code: " + str(auth) +" "+ u"\U0001F6A8"
    msg = "--Mercury Group HR system--\nThank you for your application.\nYour 4 digit identification code is: " + str(auth)

    # send auth SMS
    workerStatus = sendSMS(fnum,tel,msg,None,0,None) #no media, 0s delay, no sendTime
    #print workerStatus

    if workerStatus is not None:
        #print "worker id", workerStatus
        log.info('worker id %s' % (workerStatus))
        return True
    else:
        #print "worker error - probably"
        log.debug('worker error ~ probably')
        return False

# SMS auth - store token
def newAuth(a):
    db = create_engine(environ['OPENSHIFT_MYSQL_DB_URL'] + environ['OPENSHIFT_APP_NAME'], convert_unicode=True, echo=False)
    md = MetaData(bind=db)
    table = Table('tokenAuth', md, autoload=True)
    con = db.connect()

    now = datetime.datetime.now()
    d = now.strftime('%Y-%m-%d %H:%M:%S')

    x = con.execute( table.insert(), auth=a, date=d)
    uid = x.inserted_primary_key[0]
    con.close()
    return uid

# SMS auth - return auth based on token
def checkAuth(uid):
    db = create_engine(environ['OPENSHIFT_MYSQL_DB_URL'] + environ['OPENSHIFT_APP_NAME'], convert_unicode=True, echo=False)
    md = MetaData(bind=db)
    table = Table('tokenAuth', md, autoload=True)
    con = db.connect()
    x = con.execute( table.select(table.c.auth).where(table.c.uid == uid) )
    a = x.fetchone().get('auth', None)
    con.close()
    return a

"""
INPUT / OUTPUT (SMS, signup auth, eail, etc.)
"""
from os import environ
from sqlalchemy import *
from sqlalchemy.exc import IntegrityError
from sqlalchemy.exc import CompileError
from game import getNPC, getGameStateData
from iron_worker import *
from telUtil import *

#This method is 'dumb'. All it does is accept data, build a payload, and schedule a job. If the job is queued successfully, it returns a task/job id. It doesen't know it's sending an SMS!!!
def sendSMS(f,t,m,u,d,st):
    # f - from
    # t - to
    # m - msg
    # u - url
    # d - delay
    # st - absolute send time
    #print "####"

    #worker = IronWorker()
    worker = IronWorker(project_id=environ['IID2'], token=environ['ITOKEN2'])
    #worker = IronWorker(project_id=ironInfo['project_id'], token=ironInfo['token'])
    #print worker

    task = Task(code_name="smsworker", scheduled=True)
    #print task

    task.payload = {"keys": {"auth": environ['TSID'], "token": environ['TTOKEN']}, "fnum": f, "tnum": t, "msg": m, "url": u}
    #print task.payload

    # scheduling conditions
    if d is not None:
        task.delay = d
        #print "sending SMS after", d, "second delay"
        log.info('sending sms after %s second delay' % (d) )
    elif st is not None:
        task.start_at = st # desired `send @ playertime` converted to servertime
        #print "sending SMS at:", st
        log.info('sending sms at %s' % (st))
    else:
        task.delay = 0
        #print "sending SMS right away"
        log.info('sending sms right away')

    # now queue the damn thing & get a response.
    response = worker.queue(task)
    #print response
    return response.id

def sendEmail(fe, fn, te, tn, sub, txt, html, d, st):
    # dom - MG domain
    # key - MG api key
    # fe - npc email
    # fn - npc display_name
    # te - player email
    # tn - player name
    # sub - subject line
    # txt - text version of email
    # html - html version of email

    worker = IronWorker(project_id=environ['IID2'], token=environ['ITOKEN2'])

    task = Task(code_name="emailworker", scheduled=True)
    task.payload = {
        "dom": environ['MGDOM'],
        "key": environ['MGKEY'],
        "fe": fe,
        "fn": fn,
        "te": te,
        "tn": tn,
        "sub": sub,
        "txt": txt,
        "html": html
        }

    # scheduling conditions
    if d is not None:
        task.delay = d
        #print "sending email after", d, "second delay"
        log.info('sending email after %s second delay' % (d) )
    elif st is not None:
        task.start_at = st # desired `send @ playertime` converted to servertime
        #print "sending email at:", st
        log.info('sending email at %s' % (st))
    else:
        task.delay = 0
        #print "sending email right away"
        log.info('sending email right away')

    # now queue the damn thing & get a response.
    response = worker.queue(task)
    #print response
    return response.id

# THIS METHOD IS NOT COMPLETE
def sendErrorSMS(player):
    # send random error phrase from list to user
    err = random.choice(errlist)
    print "error msg: " + err
    log.debug('error SMS msg: %s' % (err))

    gs = getGameStateData(player['gstate'])
    npc = getNPC(player, gs['prompt']['npc'])

    sendSMS(npc['tel'], player['tel'], err, None, 14, None)

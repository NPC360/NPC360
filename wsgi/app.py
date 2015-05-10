# -*- coding: utf-8 -*-

"""
NPC360 API

API routes:
https://github.com/NPC360/NPC360/blob/master/endpoints.md

datastore schema:
https://github.com/NPC360/NPC360/blob/master/schema.md

"""

from flask import request, Flask, redirect, render_template, Response, jsonify, url_for
import requests
import json
import re
import twilio
import twilio.rest
from twilio.rest.lookups import TwilioLookupsClient
import twilio.twiml
from sqlalchemy import *
from sqlalchemy.exc import IntegrityError
from sqlalchemy.exc import CompileError
import arrow
from firebase import firebase
from iron_worker import *
import datetime
import random
from os import environ
import tinys3

app = Flask(__name__)
app.config['PROPAGATE_EXCEPTIONS'] = True

# API & DB credentials
#from Keys import *

# YES/No/Error phrases
from yesnoerr import *

# Get IronWorker keys
#ironId = "ironworker_1321d"; # your OpenShift Service Plan ID
#ironInfo = json.loads(os.getenv(ironId))

# SETUP BASIC LOGGING
# papertrail stuff from http://help.papertrailapp.com/kb/configuration/configuring-centralized-logging-from-python-apps/
import logging
import socket
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
#fh = logging.FileHandler('log/log.txt')
#fh.setLevel(logging.DEBUG)
#fh.setFormatter(lf)
#log.addHandler(fh)

# console handler
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
ch.setFormatter(lf)
log.addHandler(ch)

"""
landing page / HTML / authorization routes

"""
@app.route("/")
def index():
    return render_template('index.html')

@app.route("/careers", methods = ['GET','POST'])
def signup():
    if request.method == 'POST':
        # if auth code has been passed in, we need to process it.
        fname = request.values.get('fname', None)
        lname = request.values.get('lname', None)
        tel = request.values.get('tel', None)
        tz = request.values.get('tz', None)
        email = request.values.get('email', None)

        # non contact vars
        why = request.values.get('why-work', None)
        history = request.values.get('history', None)
        soloteam = request.values.get('soloteam', None)
        ambitious = request.values.get('ambitious', None)
        animal = request.values.get('animal', None)

        ######
        # upload resume (if it exists?) to s3
        # s3 = tinys3.Connection(environ['S3KEY'],environ['S3SECRET'])
        # resume = request.files['resumefile']
        #
        # now = datetime.datetime.now()
        # fnd = now.strftime('%Y_%m_%d_%H_%M_%S')
        #
        # fn = '%s_%s.pdf' % (email, fnd)
        # print fn
        # conn.upload(fn,resume,'npc360/resumes')
        ######

        log.debug( 'form data: %s' % (request.values))

        if request.values.get('auth', None):
            auth = request.values.get('auth', None)
            uid = request.values.get('uid', None)
            #print auth, name, tel, tz, email, uid
            #print 'Variables from form: ' + str(auth), name, str(tel), tz, email, str(uid)
            log.debug('auth form data: %s' % (request.values))

            tableAuth = checkAuth(uid)
            #print "auth code from table:", tableAuth
            log.debug('auth code from table: %s' % (tableAuth))

            #if auth is correct, create new user in playerInfo table.
            #if auth is not correct, return to confirmation step.
            if str(auth) in str(tableAuth):
                d = {'fname':fname,
                    'lname':lname,
                    'tel':tel,
                    'tz':tz,
                    'email':email,
                    'why':why,
                    'history':history,
                    'soloteam':soloteam,
                    'ambitious':ambitious,
                    'animal':animal
                    }
                uid = makeUser(d)
                #print 'new user:', name, 'uid:', uid
                log.info('new user created : %s %s, uid: %s' % (fname, lname,  uid))

                # now, schedule game start by scheduling advanceGame() worker
                startGame(uid)

                return render_template('signupSuccess.html', fname=fname)
            else:
                return render_template('signupError.html', fname=fname, lname=lname, tel=tel, tz=tz, uid=uid, email=email, why=why, history=history, soloteam=soloteam, ambitious=ambitious, animal=animal)
        # if no auth code passed in, we need to ask for it!
        # oh, and ideally we should make sure the email/phone aren't already in the table.  (future?)
        else:
            #print name, tel, tz, email
            log.debug('name: %s %s, tel: %s, tz: %s, email: %s' % (fname, lname, tel, tz, email))
            if fname and lname and tel and tz and email:
                auth = str(random.randint(1000, 9999))
                # add data to MySQL table for lookup later on & get row id/token
                uid = newAuth(auth)
                #print 'auth code:', str(auth), 'player uid:', str(uid)
                log.info('auth code: %s, player uid: %s' % (auth, uid) )

                if signupSMSauth(tel, auth):
                    return render_template('signup2.html', fname=fname, lname=lname, tel=tel, tz=tz, uid=uid, email=email, why=why, history=history, soloteam=soloteam, ambitious=ambitious, animal=animal)
                else:
                    return render_template('signup1Error.html', fname=fname, lname=lname, email=email)
    # but, if no data POSTed at all, then we need to render the signup form!
    else:
        return render_template('signup1.html')

"""
SMS IO controller
"""
@app.route("/smsin", methods = ['GET','POST'])
def smsin():
    #print "sms in"
    phone = request.values.get('From', None)
    msg = request.values.get('Body', None)
    #print 'sms in', str(phone), str(msg)
    log.info('sms in %s %s' % (phone, msg))

    u = getUser(phone)
    #print u['id'], 'input', 'sms'
    log.info('user id: %s input via SMS' % (u['id']))
    processInput(u, msg)

    resp = Response(json.dumps(request.values), status=200, mimetype='application/json')
    resp.headers['Action'] = 'SMS received: ' + msg + " +, from: " + phone
    return resp

# SO TOTALLY NOT WRITTEN YET.
@app.route("/smsout", methods =['POST'])
def smsout():
    print "sms out"
    if request.method == 'POST':
        if request.headers['Content-Type'] == 'application/json':
            d = request.get_json()
            uid = d['id']
            # get data for next game state (outgoing message, reset crap in )
            #s = d['state']

    u = requests.get(url_for('/user'), {'id':uid})
    sendSMS(u,s,n) # user object, gamestate object (defines previous state, next state, and any other data), and npc object (number, name, gender(??) etc.)
    #log(u['id'], 'output', 'sms')

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

    #worker = IronWorker()
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

def processInput(user, msg):
    gameState = user['gstate']
    gameStateData = getGameStateData(gameState)

    #special reset / debug method
    if "!reset" in msg.lower():
         #print "MANUAL GAME RESET FOR PLAYER: " + str(user['id'])
         log.warning('MANUAL GAME RESET FOR PLAYER: %s' % (user['id']))
         startGame(user['id'])

    elif 'triggers' in gameStateData and gameStateData['triggers'] is not None:
        triggers = gameStateData['triggers']
        #print triggers
        log.debug('triggers %s' % (triggers))

        sT = triggers.copy()
        sT.pop('yes', None)
        sT.pop('no', None)
        sT.pop('error', None)
        sT.pop('noresp', None)
        sT.pop('*', None)

        #print sT # this array only contains triggers that aren't tied to special keywords / operations ^^
        log.debug('truncated triggers %s' % (sT))

        # check for 'any input response (*)'
        if '*' in triggers and msg is not None:
            advanceGame(user, triggers['*'])

        # check for affirmative / negative responses
        elif 'yes' in triggers and checkYes(msg):
            advanceGame(user, triggers['yes'])
        elif 'no' in triggers and checkNo(msg):
            advanceGame(user, triggers['no'])

        # check if response is even in the list
        elif msg.lower() in sT:
            #print "input matches one of the triggers"
            log.debug('input matches one of the triggers')
            for x in sT:
                if x in msg.lower():
                    #print x + " is in "+ msg
                    log.debug('%s is in %s' % (x, msg))
                    advanceGame(user, triggers[x])
                    break

        else:
            #print "input does not match any triggers"
            log.warning('input does not match any triggers')
            sendErrorSMS(user)

def getGameStateData(id):
    fb = firebase.FirebaseApplication(environ['FB'], None)
    data = fb.get('/gameData/'+ str(id), None)
    #print 'game data:', str(data)
    log.debug('game data: %s' % (data))
    return data

def checkYes(msg):
    if msg.lower() in map(str.lower, yeslist):
        return True
    else:
        return False

def checkNo(msg):
    if msg.lower() in map(str.lower, nolist):
        return True
    else:
        return False

# deprecated method.
def checkErr(msg, sT):

    #print msg.lower()
    #print sT.keys()
    log.debug('msg: %s' % (msg.lower()))
    log.debug('keys: %s' % (sT.keys()))

    if msg.lower() in sT:
        #print "input matches triggers!"
        log.debug('input matches triggers!')
        return True
    else:
        #print "input not found in `triggers`"
        log.debug('input not found in `triggers`')
        return False

#THIS METHOD IS NOT COMPLETE
def advanceGame(player, gsid):
    # advance user state, send new prompt, log game state change?
    log.info('advancing user: %s to game state %s' % (player['id'], gsid))
    updateUser(player['id'], {"gstate":gsid})
    gs = getGameStateData(gsid)
    npc = getNPC(player, gs['prompt']['npc'])
    #msg = gs['prompt']['msg']
    #### Fill in variables like %%fname%% <- use data from player dict.
    msg = getPlayerVars(player, gs['prompt']['msg'])

    if 'url' in gs['prompt']:
        url = gs['prompt']['url']
    else:
        url = None

    if 'delay' in gs['prompt']:
        d = gs['prompt']['delay']
    else:
        d = None

    if 'st' in gs['prompt']:
        st = gs['prompt']['st']
    else:
        st = None

    smsResp = sendSMS(npc['tel'], player['tel'], msg, url, d, st)
    print smsResp
    print 'gamestate info from advanceGame method', gs['prompt']

    # after sending prompt, if there's a goto statement, we can jump forward in the game. this is for sequential msg prompts.
    if 'goto' in gs['prompt']:
        #print 'jump to game state:', gs['prompt']['goto']
        log.info('jump player %s to game state: %s' % (player['id'], gs['prompt']['goto']))
        advanceGame(player, gs['prompt']['goto'])

# THIS METHOD IS NOT COMPLETE
def sendErrorSMS(player):
    # send random error phrase from list to user
    err = random.choice(errlist)
    print "error msg: " + err
    log.debug('error SMS msg: %s' % (err))

    gs = getGameStateData(player['gstate'])
    npc = getNPC(player, gs['prompt']['npc'])

    sendSMS(npc['tel'], player['tel'], err, None, 14, None)


"""
User API
"""
@app.route("/user", methods = ['GET', 'POST', 'PATCH'])
def user():
    if request.method == 'GET':
        if (request.values.get('id', None)):
            d = request.values.get('id', None)
            u = getUser(d)

        elif request.headers['Content-Type'] == 'application/json':
            d = request.get_json()
            #print d
            log.debug('incoming request: %s' % (d))
            u = getUser(d['id'])

        #print "player", u, "\n"
        log.debug('player info: %s' % (u))

        if u is None:
            resp = Response(json.dumps(u), status=404, mimetype='application/json')
            resp.headers['Action'] = 'user not found'
            return resp

        else:
            udata = {
                'player id':u['id'],
                'player created on':str(u['cdate']),
                'fname':u['fname'],
                'lname':u['lname'],
                'tel':u['tel'],
                'email':u['email'],
                #'twitter':u['twitter'],
                'country':u['country'],
                'timezone':u['tz'],
                'game state':u['gstate'],
                'game started on':str(u['gstart']),
            }

            # return data
            resp = Response(json.dumps(udata), status=200, mimetype='application/json')
            resp.headers['Action'] = 'user retrieved'
            return resp

    if request.method == 'POST':
        if request.headers['Content-Type'] == 'application/json':
            #build user object data structure from payload
            d = request.get_json()
            udata = {
                'fname':d['fname'],
                'lname':d['lname'],
                'tel':d['tel'],
                'tz':d['tz'],
                'email':d['email'],

                # extended info
                'why':d['why-work'],
                'history':d['history'],
                'soloteam':d['soloteam'],
                'ambitious':d['ambitious'],
                'animal':d['animal']
            }
            #print udata
            log.debug(udata)

            uid = makeUser(udata)
            log.info('new user id: %s via API' % (uid))

            # return data
            udata.update({'uid':uid})
            resp = Response(json.dumps(udata), status=201, mimetype='application/json')
            resp.headers['Action'] = 'user created'
            return resp

    elif request.method == 'PATCH':
        if request.headers['Content-Type'] == 'application/json':
            d = request.get_json()
            #print d
            log.debug('incoming request: %s' % (d))

            if getUser(d['id']) and d['id'] == getUser(d['id'])['id']:
                data = d['data']
                r = updateUser(d['id'], data)

                # if nothing returns, nothing was updated, so we need to return an error.
                if r == None:
                    resp = Response(json.dumps(d), status=500, mimetype='application/json')
                    resp.headers['Action'] = 'updateUser() error'
                else:
                    #log(u['uid'], 'mod user', 'api')
                    # if r returns data, than -something- was updated
                    resp = Response(json.dumps(r), status=200, mimetype='application/json')
                    resp.headers['Action'] = 'user updated'
            else:
                resp = Response(json.dumps(d), status=500, mimetype='application/json')
                resp.headers['Action'] = 'user id mismatch error'
            return resp


"""
MySQL DATASTORE METHODS
"""
# I/O Logging (time, userid, action taken, I/O medium -- what else??)
# def log(u,a,m):
#     db = create_engine(environ['OPENSHIFT_MYSQL_DB_URL'] + environ['OPENSHIFT_APP_NAME'], convert_unicode=True, echo=False)
#     md = MetaData(bind=db)
#
#     now = datetime.datetime.now()
#     d = now.strftime('%Y-%m-%d %H:%M:%S')
#
#     table = Table('log', md, autoload=True)
#     con = db.connect()
#     con.execute( table.insert(), date=d, user=u, action=a, medium=m)
#     con.close()
#     print d,u,a,m

# lookup user from datastore using a provided 'id' - could be uid, phone / email / twitter handle, etc. (should be medium agnostic)
def getUser(uid):
    db = create_engine(environ['OPENSHIFT_MYSQL_DB_URL'] + environ['OPENSHIFT_APP_NAME'], convert_unicode=True, echo=False)
    #db = create_engine(Mdb, convert_unicode=True, echo=False)
    md = MetaData(bind=db)
    table = Table('playerInfo', md, autoload=True)
    con = db.connect()

    x = con.execute( table.select().where(or_(table.c.id == uid, table.c.tel == uid, table.c.email == uid)))

    row = x.fetchone()
    con.close()
    return row

# create new user using POST payload.
def makeUser(ud):
    try:
        db = create_engine(environ['OPENSHIFT_MYSQL_DB_URL'] + environ['OPENSHIFT_APP_NAME'], convert_unicode=True, echo=False)
        #db = create_engine(Mdb, convert_unicode=True, echo=False)
        md = MetaData(bind=db)
        table = Table('playerInfo', md, autoload=True)

        #normalize phone # & get current datetime
        #normTel = re.sub(r'[^a-zA-Z0-9\+]','', ud['tel'])
        normTel = normalizeTel(ud['tel'])

        now = datetime.datetime.now()
        d = now.strftime('%Y-%m-%d %H:%M:%S')

        con = db.connect()
        x = con.execute( table.insert(),
            fname=ud['fname'],
            lname=ud['lname'],
            tel=normTel,
            tz=ud['tz'],
            email=ud['email'],
            country=getCountryCode(normTel),
            cdate=d,
            gstart=d,
            gstate=0,
            why=ud['why'],
            history=ud['history'],
            soloteam=ud['soloteam'],
            ambitious=ud['ambitious'],
            animal=ud['animal']
            )

        uid = x.inserted_primary_key[0]
        con.close()
        #print uid
        log.debug('new player uid: %s' % (uid))
        return uid

    except IntegrityError as e:
        #print e
        log.debug('error %s' % (e))
        return render_template('signup1_EorP_Taken.html', name=ud['fname'])

# update user data using POST payload.
def updateUser(uid, data):
    try:
        db = create_engine(environ['OPENSHIFT_MYSQL_DB_URL'] + environ['OPENSHIFT_APP_NAME'], convert_unicode=True, echo=False)
        #db = create_engine(Mdb, convert_unicode=True, echo=False)
        md = MetaData(bind=db)
        table = Table('playerInfo', md, autoload=True)
        con = db.connect()
        res = con.execute( table.update().where(table.c.id == uid).values(data) )
        con.close()
        return res.last_updated_params()

    except (CompileError, IntegrityError) as e:
        #print e
        log.debug('error %s' % (e))

# get NPC info & tel by matching NPC number and the country code of player.
def getNPC(playerInfo, npcName):
    db = create_engine(environ['OPENSHIFT_MYSQL_DB_URL'] + environ['OPENSHIFT_APP_NAME'], convert_unicode=True, echo=False)
    #db = create_engine(Mdb, convert_unicode=True, echo=False)
    md = MetaData(bind=db)
    table = Table('npcInfo', md, autoload=True)
    con = db.connect()

    x = con.execute( table.select().where(and_(table.c.name == npcName, table.c.country == playerInfo['country'])))

    row = x.fetchone()
    con.close()
    return row

# SMS auth - store token
def newAuth(a):
    db = create_engine(environ['OPENSHIFT_MYSQL_DB_URL'] + environ['OPENSHIFT_APP_NAME'], convert_unicode=True, echo=False)
    #db = create_engine(Mdb, convert_unicode=True, echo=False)
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
    #db = create_engine(Mdb, convert_unicode=True, echo=False)
    md = MetaData(bind=db)
    table = Table('tokenAuth', md, autoload=True)
    con = db.connect()
    x = con.execute( table.select(table.c.auth).where(table.c.uid == uid) )
    a = x.fetchone()['auth']
    con.close()
    return a

def getCountryCode(tel):
    tel = normalizeTel(tel)
    lookup = TwilioLookupsClient(environ['TSID'], environ['TTOKEN'])
    return lookup.phone_numbers.get(tel).country_code

def startGame(uid):
    player = getUser(uid)
    updateUser(player['id'], {"gstate":1})
    gs = getGameStateData(1)
    npc = getNPC(player, gs['prompt']['npc'])

    #print npc
    log.debug('npc info: %s' % (npc))

    ### Fill in variables like %%fname%% <- use data from player dict.
    msg = getPlayerVars(player, gs['prompt']['msg'])

    # if current player time is before 1pm, send msg at 2:05pm player time otherwise, same time next day.
    pt = arrow.now().to(player['tz'])
    if pt.hour < 13: # earlier than 1pm
        t = arrow.get(pt.year, pt.month, pt.day, 14, 5, 15, 0,  player['tz']).datetime
    else:
        t = arrow.get(pt.year, pt.month, pt.day+1, 14, 5, 15, 0, player['tz']).datetime

    #sendSMS(npc['tel'], player['tel'], msg, None, None, t)
    sendSMS(npc['tel'], player['tel'], msg, None, None, None)
    #sendEmail(npc['email'], npc['display_name'], player['email'], player['name'], "Mercury Global application accepted", "Thanks for applying", "<h3>your app was accepted</h3><img src='http://media.giphy.com/media/xTiTnxxyVuH374sjRu/giphy.gif'>", None, None)

def normalizeTel(tel):
    nTel = re.sub(r'[^a-zA-Z0-9\+]','', tel)
    return nTel

def getPlayerVars(player, msg):
    merge = re.findall(r'%%([^%%]*)%%', msg)
    for x in merge:
        #print x
        if player[x.lower()]:
            msg = re.sub('%%'+x+'%%', player[x], msg)
            #print msg
    return msg


if __name__ == "__main__":
    app.run(debug=True)

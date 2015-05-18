# -*- coding: utf-8 -*-

"""
NPC360 API

API routes:
https://github.com/NPC360/NPC360/blob/master/endpoints.md

datastore schema:
https://github.com/NPC360/NPC360/blob/master/schema.md

"""

from flask import request, session, Flask, render_template, Response, redirect, url_for
import forms
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

# API & DB credentials
#from Keys import *

# Initialise the Flask app
app = Flask(__name__)
app.config['PROPAGATE_EXCEPTIONS'] = True
app.secret_key = environ['SecretSessionKey']

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


@app.route("/solutions/")
def solutions():
    return render_template('solutions.html')


@app.route("/case-studies/")
def case_studies():
    return render_template('case-studies.html')


@app.route("/contact/")
def contact():
    return render_template('contact.html')


@app.route("/careers/")
def careers():
    return render_template('careers.html')


@app.route("/careers/job-2342/")
def careers_job():
    return render_template('careers-job-description.html')


@app.route("/careers/auth/success/")
def careers_auth_success():
    return render_template('signup-success.html')


@app.route("/careers/auth/2/")
def careers_auth_check_code():
    # Check that the user is awaiting an auth SMS, if they're
    # not, redireect them to the registration page
    if session.get('awaiting_auth', False) is not True:
        return redirect(url_for("/careers/job-2342/apply/"))

    # If the SMS hasn't been sent, jump back a step
    if session.get('sent_sms', False) is not True:
        return redireect(url_for("/careers/auth/"))

    form = forms.SMSAuth(response.form)

    if request.method == 'POST' and form.validate():
        # Create the user
        fname = session.get('first_name', None)
        lname = session.get('last_name', None)
        options = {
            'fname': fname,
            'lname': lname,
            'tel': session.get('mobile_number', None),
            'tz': session.get('tz', None),
            'email': session.get('email', None),
            'why': session.get('why_work', None),
            'history': session.get('work_history', None),
            'soloteam': session.get('team_work', None),
            'ambitious': session.get('ambitious', None),
            'leaving': session.get('leaving', None),
            'animal': session.get('animal', None)
        }
        uid = makeUser(options)
        log.info('new user created : %s %s, uid: %s' % (fname, lname, uid))

        # now, schedule game start by scheduling advanceGame() worker
        log.debug('starting game for player uid: %s' % uid)
        startGame(uid)

        # Success!
        return redireect(url_for("/careers/auth/success/"))
    else:
        return render_template('signup-auth.html', form=form, name=session.get("name"))


@app.route("/careers/auth/")
def careers_auth_send_sms():
    # Check that the user is awaiting an auth SMS, if they're
    # not, redireect them to the registration page
    if session.get('awaiting_auth', False) is not True:
        return redirect(url_for("/careers/job-2342/apply/"))

    # If the SMS hasn't been sent, jump back a step
    if session.get('sent_sms', False) is True:
        return redireect(url_for("/careers/auth/2/"))

    # Create the form instance
    form = forms.FullSignup(request.form)

    # Send Auth SMS
    # add data to table for lookup later on & get row id/token
    if request.method == 'GET' or request.method == 'POST' and form.validate():
        auth = str(random.randint(1000, 9999))
        uid = newAuth(auth)
        log.info('auth code: %s, player uid: %s' % (auth, uid))
        session['auth_sms_sent'] = signupSMSauth(session['mobile_number'], auth)

    if session.get('auth_sms_sent') is True:
        return redireect(url_for("/careers/auth/2/"))
    else:
        return render_template('signup-bad-mobile.html', form=form)


@app.route("/careers/job-2342/apply/", methods=['GET', 'POST'])
def signup():
    # If the user has already signed up and is awaiting an auth
    # SMS to come in, redirect them to the auth page
    if (session.get('awaiting_auth') is True):
        return redirect(url_for("/careers/auth/"))

    # Create the form instance
    form = forms.FullSignup(request.form)

    # Validate form
    if request.method == 'POST' and form.validate():

        # Save form data in a session
        session.update(form.data)

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

        # Indicate that the user is attempting
        # to authenticate their phone number
        session['awaiting_auth'] = True

        # Redirect to SMS auth page
        return redirect(url_for("/careers/auth/"))
    else:
        return render_template('signup-form.html', form=form)


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

def processInput(player, msg):
    gameState = player['gstate']
    gameStateData = getGameStateData(gameState)

    #special reset / debug method
    if "!reset" in msg.lower():
         #print "MANUAL GAME RESET FOR PLAYER: " + str(player['id'])
         log.warning('MANUAL GAME RESET FOR PLAYER: %s' % (player['id']))
         startGame(player['id'])

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
            advanceGame(player, triggers['*'])

        # check for affirmative / negative responses
        elif 'yes' in triggers and checkYes(msg):
            advanceGame(player, triggers['yes'])

        elif 'no' in triggers and checkNo(msg):
            advanceGame(player, triggers['no'])

        # check if response is even in the list
        elif msg.lower() not in sT:
            #print "input does not match any triggers"
            log.warning('input does not match any triggers')
            sendErrorSMS(player)

        # otherwise, run through remaining triggers
        else:
            #print "input matches one of the triggers"
            log.debug('input matches one of the triggers')
            for x in sT:
                if x.lower() in msg.lower():
                    #print x + " is in "+ msg
                    log.debug('%s is in %s' % (x, msg))
                    advanceGame(player, triggers[x])
                    break

        #else:
            #print "input does not match any triggers"
            #log.warning('input does not match any triggers')
            #sendErrorSMS(player)

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

    # POTATO HACKS -- these methods are for jumping to db checks & then coming back.
    if gsid == '126':
        log.debug('player %s hit a potato hack: %s' % (player['id'], gsid))
        hack_126(player)

    elif gsid == '133':
        log.debug('player %s hit a apotato hack: %s' % (player['id'], gsid))
        hack_133(player)

    elif gsid == '142':
        log.debug('player %s hit a potato hack: %s' % (player['id'], gsid))
        hack_142(player)

    elif gsid == '156':
        log.debug('player %s hit a potato hack: %s' % (player['id'], gsid))
        hack_156(player)



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
            leaving=ud['leaving'],
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
    a = x.fetchone().get('auth', None)
    con.close()
    return a

def getCountryCode(tel):
    tel = normalizeTel(tel)
    lookup = TwilioLookupsClient(environ['TSID'], environ['TTOKEN'])
    return lookup.phone_numbers.get(tel).country_code

def startGame(uid):
    player = getUser(uid)

    updateUser(player['id'], {"gstate":101})
    gs = getGameStateData(101)

    # send application acceptence email from HR
    log.debug('sending HR email for player uid: %s' % (uid))
    hrEmail(getUser(uid))

    # get npc data
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


#### Potato hack methods that jump around the game #

def hack_126(player):
    log.debug('player soloteam enum: %s' % (player['soloteam']))

    if player['soloteam'] == 0:
        log.debug('player %s warps to 127' % (player['id']))
        advanceGame(player, '127')

    elif player['soloteam'] == 1:
        log.debug('player %s warps to 129' % (player['id']))
        advanceGame(player, '129')

    elif player['soloteam'] == 2:
        log.debug('player %s warps to 120' % (player['id']))
        advanceGame(player, '130')

def hack_133(player):
    log.debug('player leaving enum: %s' % (player['leaving']))

    if player['leaving'] == 0:
        log.debug('player %s warps to 134' % (player['id']))
        advanceGame(player, '134')

    elif player['leaving'] == 1:
        log.debug('player %s warps to 137' % (player['id']))
        advanceGame(player, '137')

    elif player['leaving'] == 2:
        log.debug('player %s warps to 139' % (player['id']))
        advanceGame(player, '139')

    elif player['leaving'] == 3:
        log.debug('player %s warps to 136' % (player['id']))
        advanceGame(player, '136')

    elif player['leaving'] == 4:
        log.debug('player %s warps to 138' % (player['id']))
        advanceGame(player, '138')

def hack_142(player):
    log.debug('player ambitious enum: %s' % (player['ambitious']))

    if player['ambitious'] == 0:
        log.debug('player %s warps to 144' % (player['id']))
        advanceGame(player, '144')

    elif player['ambitious'] == 1:
        log.debug('player %s warps to 143' % (player['id']))
        advanceGame(player, '143')

def hack_156(player):
    log.debug('player ambitious enum: %s' % (player['ambitious']))

    if player['ambitious'] == 0:
        log.debug('player %s warps to 158' % (player['id']))
        advanceGame(player, '158')

    elif player['ambitious'] == 1:
        log.debug('player %s warps to 157' % (player['id']))
        advanceGame(player, '157')

# Application accepted email from HR
def hrEmail(player):

    # dom - MG domain
    # key - MG api key
    # fe - npc email
    # fn - npc display_name
    # te - player email
    # tn - player name
    # sub - subject line
    # txt - text version of email
    # html - html version of email

    sendEmail(
        "careers@mercury.industries",
        "Mercury Careers",
        player['email'],
        player['fname'] +" "+player['lname'],
        "Your Mercury Careers application has been accepted",

        "Dear "+player['fname']+",\n\nWe received and are currently reviewing your application for System Administrator-MGSYSAD45056. If your profile meets the position's requirements, a representative from Human Resources may contact you for additional information.\n\nIf you have any questions or require additional support, please contact: careers@mercury.industries\n\nThank you for your interest in Mercury Group.\n\nSincerely\n\nMercury Group Recruitment Team\n\n- - - \n\nPlease do not reply to this message. Replies to this message are undeliverable.\n\n Your rights and responsibilities regarding the information submitted by you and about you to the Mercury Group Career Site (including the recruitment management system and mobility management site and system) are set out in the Terms of Use statement.\n\n Mercury refers to one or more of Mercury Group Limited, a private company limited by guarantee, and its network of member firms, each of which is a legally separate and independent entity. Please see <a href='http://www.mercurygroup.com/about'>www.mercurygroup.com/about</a> for a detailed description of the legal structure of Mercury Group and its member firms.",

        "<p>Dear "+player['fname']+",</p> <p>We received and are currently reviewing your application for System Administrator-MGSYSAD45056. If your profile meets the position's requirements, a representative from Human Resources may contact you for additional information.</p> <p>If you have any questions or require additional support, please contact: careers@mercury.industries</p> <p>Thank you for your interest in Mercury Group.</p> <p>Sincerely</p> <p>Mercury Group Recruitment Team</p> <p style='font-style: italic;'>Please do not reply to this message. Replies to this message are undeliverable.</p> <p style='font-style: italic;'>Your rights and responsibilities regarding the information submitted by you and about you to the Mercury Group Career Site (including the recruitment management system and mobility management site and system) are set out in the Terms of Use statement.</p> <p style='font-style: italic;'>Mercury refers to one or more of Mercury Group Limited, a private company limited by guarantee, and its network of member firms, each of which is a legally separate and independent entity. Please see <a href='http://www.mercurygroup.com/about'>www.mercurygroup.com/about</a> for a detailed description of the legal structure of Mercury Group and its member firms.</p>",
        None,
        None)

if __name__ == "__main__":
    app.run(debug=True)

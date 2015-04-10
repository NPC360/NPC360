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

app = Flask(__name__)

# API & DB credentials
#from Keys import *

# YES/No/Error phrases
from yesnoerr import *

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
        name = request.values.get('fname', None)
        tel = request.values.get('tel', None)
        tz = request.values.get('tz', None)
        email = request.values.get('email', None)

        if request.values.get('auth', None):
            auth = request.values.get('auth', None)
            uid = request.values.get('uid', None)
            print auth, name, tel, tz, email, uid

            tableAuth = checkAuth(uid)
            print "auth from table", tableAuth

            #if auth is correct, create new user in playerInfo table.
            #if auth is not correct, return to confirmation step.
            if str(auth) in str(tableAuth):
                d = {'fname':name, 'tel':tel, 'tz':tz, 'email':email}
                uid = makeUser(d)
                print "new uid", uid

                # now, schedule game start by scheduling advanceGame() worker
                startGame(uid)

                return render_template('signupSuccess.html', name=name, tel=tel, tz=tz, email=email)
            else:
                return render_template('signupError.html', name=name, tel=tel, tz=tz, uid=uid, email=email)
        # if no auth code passed in, we need to ask for it!
        # oh, and ideally we should make sure the email/phone aren't already in the table.  (future?)
        else:
            print name, tel, tz, email
            if name and tel and tz and email:
                auth = str(random.randint(1000, 9999))
                # add data to MySQL table for lookup later on & get row id/token
                uid = newAuth(auth)
                print auth, uid

                if signupSMSauth(tel, auth):
                    return render_template('signup2.html', name=name, tel=tel, tz=tz, uid=uid, email=email)
                else:
                    return render_template('signup1Error.html', name=name, email=email)
    # but, if no data POSTed at all, then we need to render the signup form!
    else:
        return render_template('signup1.html')

"""
SMS IO controller
"""
@app.route("/smsin", methods = ['GET','POST'])
def smsin():
    print "sms in"

    phone = request.values.get('From', None)
    msg = request.values.get('Body', None)
    print phone, msg

    u = getUser(phone)
    #log(u['id'], 'input', 'sms')
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

    print "sendSMS: "+f+" "+t+" "+m+" "+u+" "+d+" "+st
    worker = IronWorker()
    print worker

    task = Task(code_name="smsworker", scheduled=True)
    print task

    task.payload = {"keys": {"auth": environ['TSID'], "token": environ['TTOKEN']}, "fnum": f, "tnum": t, "msg": m, "url": u}
    print task.payload

    # scheduling conditions
    if d is not None:
        task.delay = d
        print "sending after", d, "second delay"
    elif st is not None:
        task.start_at = st # desired `send @ playertime` converted to servertime
        print "sending at:", st
    else:
        task.delay = 0
        print "sending right away"

    # now queue the damn thing & get a response.
    response = worker.queue(task)
    print response
    return response.id

def signupSMSauth(tel,auth):
    # lookup admin NPC # for the user's country (this of course, assumes we have one)

    print "incoming tel: "+ tel
    fnum = getNPC({ "country": getCountryCode(tel) }, 'admin')['tel']
    print "send sms from: " + fnum
    msg = "code: " + str(auth) +" "+ u"\U0001F6A8"
    print "signupSMSauth", tel, msg

    # send auth SMS
    workerStatus = sendSMS(fnum,tel,msg,None,0,None) #no media, 0s delay, no sendTime

    if workerStatus is not None:
        print "worker id", workerStatus
        return True
    else:
        print "worker error - probably"
        return False

def processInput(user, msg):
    gameState = user['gstate']
    gameStateData = getGameStateData(gameState)

    #special reset / debug method
    if "!reset" in msg:
         print "MANUAL GAME RESET FOR PLAYER: " + str(user['id'])
         startGame(user['id'])

    elif 'triggers' in gameStateData and gameStateData['triggers'] is not None:
        triggers = gameStateData['triggers']
        print triggers

        sT = triggers.copy()
        sT.pop('yes', None)
        sT.pop('no', None)
        sT.pop('error', None)
        sT.pop('noresp', None)

        print sT # this array only contains triggers that aren't tied to special keywords / operations ^^


        # check for affirmative / negative responses
        if 'yes' in triggers and checkYes(msg):
            advanceGame(user, triggers['yes'])
        elif 'no' in triggers and checkNo(msg):
            advanceGame(user, triggers['no'])

        # check if response is even in the list

        elif msg.lower() in sT:
            print "input matches one of the triggers"
            for x in sT:
                #print x
                if x in msg.lower():
                    print x + " is in "+ msg
                    advanceGame(user, triggers[x])
                    break

        else:
            print "input does not match any triggers"
            sendErrorSMS(user)

def getGameStateData(id):
    fb = firebase.FirebaseApplication(environ['FB'], None)
    data = fb.get('/gameData/'+ str(id), None)
    print data
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

    print msg.lower()
    print sT.keys()

    if msg.lower() in sT:
        print "input matches triggers!"
        return True
    else:
        print "input not found in `triggers`"
        return False

#THIS METHOD IS NOT COMPLETE
def advanceGame(player, gsid):
    # advance user state, send new prompt, log game state change?
    updateUser(player['id'], {"gstate":gsid})
    gs = getGameStateData(gsid)
    npc = getNPC(player, gs['prompt']['npc'])
    msg = gs['prompt']['msg']

    if 'url' in gs['prompt']:
        url = gs['prompt']['url']
    else:
        url = None;

    if 'delay' in gs['prompt']:
        d = gs['prompt']['delay']
    else:
        d = None;

    if 'st' in gs['prompt']:
        st = gs['prompt']['st']
    else:
        st = None;

#### add a loop in here to check for & fill in variables like %fname% <- use data from player dict.

    sendSMS(npc['tel'], player['tel'], msg, url, d, st)

    #log(user['id'], "advance to game state "+ state, "SMS")

# THIS METHOD IS NOT COMPLETE
def sendErrorSMS(player):
    # send random error phrase from list to user
    err = random.choice(errlist)
    print "error msg: " + err

    gs = getGameStateData(player['gstate'])
    npc = getNPC(player, gs['prompt']['npc'])

    sendSMS(npc['tel'], player['tel'], err, None, 45, None)


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
            print d
            u = getUser(d['id'])

        print "player", u, "\n"

        if u is None:
            resp = Response(json.dumps(u), status=404, mimetype='application/json')
            resp.headers['Action'] = 'user not found'
            return resp

        else:
            udata = {
                'player id':u['id'],
                'player created on':str(u['cdate']),
                'name':u['name'],
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
                'tel':d['tel'],
                'tz':d['tz'],
                'email':d['email']
            }
            print udata
            uid = makeUser(udata)
            #log(uid, 'new user', 'api')

            # return data
            udata.update({'uid':uid})
            resp = Response(json.dumps(udata), status=201, mimetype='application/json')
            resp.headers['Action'] = 'user created'
            return resp

    elif request.method == 'PATCH':
        if request.headers['Content-Type'] == 'application/json':
            d = request.get_json()
            print d

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
def log(u,a,m):
    db = create_engine(environ['OPENSHIFT_MYSQL_DB_URL'] + environ['OPENSHIFT_APP_NAME'], convert_unicode=True, echo=False)
    md = MetaData(bind=db)

    now = datetime.datetime.now()
    d = now.strftime('%Y-%m-%d %H:%M:%S')

    table = Table('log', md, autoload=True)
    con = db.connect()
    con.execute( table.insert(), date=d, user=u, action=a, medium=m)
    con.close()
    print d,u,a,m

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
        x = con.execute( table.insert(), name=ud['fname'], tel=normTel, tz=ud['tz'], email=ud['email'], country=getCountryCode(normTel),  cdate=d, gstart=d, gstate=0 )

        uid = x.inserted_primary_key[0]
        con.close()
        print uid
        return uid

    except IntegrityError as e:
        print e
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
        print e

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
    #print "player country: " + lookup.phone_numbers.get(tel).country_code
    return lookup.phone_numbers.get(tel).country_code

def startGame(uid):
    player = getUser(uid)
    updateUser(player['id'], {"gstate":1})
    gs = getGameStateData(1)
    npc = getNPC(player, gs['prompt']['npc'])

    print npc

    # if current player time is before 1pm, send msg at 2:05pm player time otherwise, same time next day.
    pt = arrow.now().to(player['tz'])
    if pt.hour < 13: # earlier than 1pm
        t = arrow.get(pt.year, pt.month, pt.day, 14, 5, 15, 0,  player['tz']).datetime
    else:
        t = arrow.get(pt.year, pt.month, pt.day+1, 14, 5, 15, 0, player['tz']).datetime

    #sendSMS(npc['tel'], player['tel'], gs['prompt']['msg'], None, None, t)
    sendSMS(npc['tel'], player['tel'], gs['prompt']['msg'], None, None, None)

def normalizeTel(tel):
    nTel = re.sub(r'[^a-zA-Z0-9\+]','', tel)
    return nTel

if __name__ == "__main__":
    app.run(debug=True)

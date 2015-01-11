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
from twilio.rest import TwilioRestClient
import twilio.twiml
from sqlalchemy import *

import datetime
import random
from os import environ

app = Flask(__name__)

# API & DB credentials
from Keys import *

"""
landing page / HTML / authorization routes

"""
@app.route("/")
def index():
    return render_template('index.html')

@app.route("/signup", methods = ['GET','POST'])
def signup():
    if request.method == 'POST':
        # if auth code has been pass in, we need to process it.
        name = request.values.get('fname', None)
        tel = request.values.get('tel', None)
        tz = request.values.get('tz', None)

        if request.values.get('auth', None):
            auth = request.values.get('auth', None)
            uid = request.values.get('uid', None)
            print auth, name, tel, tz, uid

            tableAuth = checkAuth(uid)
            print "auth from table", tableAuth

            #if auth is correct, create new user in playerInfo table.
            #if auth is not correct, return to confirmation step.
            if str(auth) in str(tableAuth):

                d = {'fname':name, 'tel':tel, 'tz':tz}
                uid = makeUser(d)
                print "new uid", uid
                return render_template('signupSuccess.html', name=name, tel=tel, tz=tz)
            else:
                return render_template('signupError.html', name=name, tel=tel, tz=tz, uid=uid)
        # if no auth code passed in, we need to ask for it!
        else:
            print name, tel, tz
            if name and tel and tz:
                auth = str(random.randint(1000, 9999))
                # add data to MySQL table for lookup later on & get row id/token
                uid = newAuth(auth)
                print auth, uid

                signupSMSauth(tel, auth)
                return render_template('signup2.html', name=name, tel=tel, tz=tz, uid=uid)
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
    print uid, msg

    u = requests.get(url_for('user'), {'id':phone})
    print u

    log(u['id'], 'input', 'sms') # (what else do we need to log here?)

    #process input payload (if payload_error, return info via /smsout)
    #update player game state (external datastore)
    #return new prompt to player via /smsout

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
    log(u['id'], 'output', 'sms')

def sendSMS(u,s,n):
    c = TwilioRestClient(Tsid, Ttoken)
    if (s['media']): # if game state object has a media URL, we should send it via MMS!
        c.messages.create(to=u['phone'], from_=n['phone'],body=s['msg'], media_url=s['media'])
    else:
        c.messages.create(to=u['phone'], from_=n['phone'],body=s['msg'])

def signupSMSauth(tel,auth):
    fromNum ="+17183959467" # should be env variable.
    msg = "your code: " + auth +" "+ u"\U0001F6A8"
    print "signupSMSauth", tel, msg

    try:
        c = TwilioRestClient(Tsid, Ttoken)
        c.messages.create(to=tel, from_=fromNum, body=msg)
    except twilio.TwilioRestException as e:
        print e


"""
user API
"""
@app.route("/user", methods = ['GET', 'POST', 'PATCH'])
def user():
    if request.method == 'GET':
        if request.headers['Content-Type'] == 'application/json':
            d = request.get_json()
            u = getUser(d['id'])
            print "player", u['uid'], '(', u['fname'], u['lname'], ') :', u, "\n"
            return u

    if request.method == 'POST':
        if request.headers['Content-Type'] == 'application/json':
            #build user object data structure from payload
            d = request.get_json()
            udata = {'fname':d['fname'], 'tel':d['tel'], 'tz':d['tz']}
            print udata
            uid = makeUser(udata)
            #log(uid, 'new user', 'api')

            # let's return some data!!
            udata.update({'uid':uid})
            resp = Response(json.dumps(udata), status=201, mimetype='application/json')
            resp.headers['Action'] = 'user created'
            return resp

    elif request.method == 'PATCH':
        if request.headers['Content-Type'] == 'application/json':
            d = request.get_json()
            print d
            #build updated user object data structure from payload
            uu = "xxx"
            print uu
            u = updateUser(uu)
            #log(u['uid'], 'mod user', 'api')
            return u


"""
DATASTORE METHODS
"""
# I/O Logging (time, userid, action taken, I/O medium -- what else??)
def log(u,a,m):
    db = create_engine(environ['OPENSHIFT_MYSQL_DB_URL'] + environ['OPENSHIFT_APP_NAME'], convert_unicode=True, echo=True)
    md = MetaData(bind=db)

    now = datetime.datetime.now()
    d = now.strftime('%Y-%m-%d %H:%M:%S')

    table = Table('log', md, autoload=True)
    con = db.connect()
    con.execute( table.insert(), date=d, user=u, action=a, medium=m)
    print d,u,a,m

# lookup user from datastore using a provided 'id' - could be uid, phone / email / twitter handle, etc. (should be medium agnostic)
def getUser(id):
    #db = create_engine(environ['OPENSHIFT_MYSQL_DB_URL'] + environ['OPENSHIFT_APP_NAME'], convert_unicode=True, echo=True)
    db = create_engine(Mdb, convert_unicode=True, echo=True)
    md = MetaData(bind=db)
    table = Table('playerInfo', md, autoload=True)
    con = db.connect()
    #u = con.execute( table.insert(), date=d, user=u, action=a, medium=m)
    print u
    return u

# create new user using POST payload.
def makeUser(ud):
    #db = create_engine(environ['OPENSHIFT_MYSQL_DB_URL'] + environ['OPENSHIFT_APP_NAME'], convert_unicode=True, echo=True)
    db = create_engine(Mdb, convert_unicode=True, echo=False)
    md = MetaData(bind=db)
    table = Table('playerInfo', md, autoload=True)

    now = datetime.datetime.now()
    d = now.strftime('%Y-%m-%d %H:%M:%S')

    con = db.connect()
    x = con.execute( table.insert(), name=ud['fname'], tel=ud['tel'], tz=ud['tz'], cdate=d, gstart=d, gstate=0 )

    uid = x.inserted_primary_key[0]
    print uid
    return uid

# update user data using POST payload.
def updateUser(userData):
    #db = create_engine(environ['OPENSHIFT_MYSQL_DB_URL'] + environ['OPENSHIFT_APP_NAME'], convert_unicode=True, echo=True)
    db = create_engine(Mdb, convert_unicode=True, echo=False)
    md = MetaData(bind=db)
    table = Table('playerInfo', md, autoload=True)
    con = db.connect()
    #con.execute( table.update(), date=d, user=u, action=a, medium=m)
    return u

# SMS auth - store token
def newAuth(a):
    #db = create_engine(environ['OPENSHIFT_MYSQL_DB_URL'] + environ['OPENSHIFT_APP_NAME'], convert_unicode=True, echo=True)
    db = create_engine(Mdb, convert_unicode=True, echo=False)
    md = MetaData(bind=db)
    table = Table('tokenAuth', md, autoload=True)
    con = db.connect()

    now = datetime.datetime.now()
    d = now.strftime('%Y-%m-%d %H:%M:%S')

    x = con.execute( table.insert(), auth=a, date=d)
    uid = x.inserted_primary_key[0]

    return uid

# SMS auth - return auth based on token
def checkAuth(uid):
    #db = create_engine(environ['OPENSHIFT_MYSQL_DB_URL'] + environ['OPENSHIFT_APP_NAME'], convert_unicode=True, echo=True)
    db = create_engine(Mdb, convert_unicode=True, echo=False)
    md = MetaData(bind=db)
    table = Table('tokenAuth', md, autoload=True)
    con = db.connect()
    x = con.execute( table.select(table.c.auth).where(table.c.uid == uid) )
    a = x.fetchone()['auth']
    return a

if __name__ == "__main__":
    app.run(debug=True)

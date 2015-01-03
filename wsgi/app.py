# -*- coding: utf-8 -*-

"""
NPC360 SMS IO controller

https://github.com/NPC360/SMSIO/blob/master/endpoints.md

"""

from flask import request, Flask, redirect, render_template
import requests
import json
from twilio.rest import TwilioRestClient
import twilio.twiml
from sqlalchemy import create_engine, MetaData, exc, Table
import datetime
from os import environ

app = Flask(__name__)

@app.route("/")
def index():
    return render_template('index.html')

@app.route("/smsin/", methods = ['GET','POST'])
def smsin():
    print "sms in"

    phone = request.values.get('From', None)
    msg = request.values.get('Body', None)
    print uid, msg

    u = requests.get(url_for('/user'), {'id':phone})
    print u

    log(u['id'], 'input', 'sms') # (what else do we need to log here?)

    #process input payload (if payload_error, return info via /smsout)
    #update player game state (external datastore)
    #return new prompt to player via /smsout

@app.route("/smsout/")
def smsout():
    print "sms out"

@app.route("/user", methods = ['GET', 'POST', 'PATCH'])
def user():
    if request.method == 'GET':
        if request.headers['Content-Type'] == 'application/json':
            d = request.get_json()
            u = getUser(d['id'])
            print "player", u['id'], '(', u['fname'], u['lname'], ') :', u, "\n"
            return u

    if request.method == 'POST':
        if request.headers['Content-Type'] == 'application/json':
            d = request.get_json()
            print d
            #build user object data structure from payload
            nu = "xxx"
            print nu
            u = makeUser(nu)
            log(u['id'], 'new user', 'api')
            return u

    elif request.method == 'PATCH':
        if request.headers['Content-Type'] == 'application/json':
            d = request.get_json()
            print d
            #build updated user object data structure from payload
            uu = "xxx"
            print uu
            u = updateUser(uu)
            log(u['id'], 'mod user', 'api')
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
    db = create_engine(environ['OPENSHIFT_MYSQL_DB_URL'] + environ['OPENSHIFT_APP_NAME'], convert_unicode=True, echo=True)
    md = MetaData(bind=db)
    table = Table('players', md, autoload=True)
    con = db.connect()
    #u = con.execute( table.insert(), date=d, user=u, action=a, medium=m)
    print u
    return u

# create new user using POST payload.
def makeUser(userData):
    db = create_engine(environ['OPENSHIFT_MYSQL_DB_URL'] + environ['OPENSHIFT_APP_NAME'], convert_unicode=True, echo=True)
    md = MetaData(bind=db)
    table = Table('players', md, autoload=True)
    con = db.connect()
    #con.execute( table.insert(), date=d, user=u, action=a, medium=m)
    return u

# update user data using POST payload.
def updateUser(userData):
    db = create_engine(environ['OPENSHIFT_MYSQL_DB_URL'] + environ['OPENSHIFT_APP_NAME'], convert_unicode=True, echo=True)
    md = MetaData(bind=db)
    table = Table('players', md, autoload=True)
    con = db.connect()
    #con.execute( table.update(), date=d, user=u, action=a, medium=m)
    return u

if __name__ == "__main__":
    app.run()

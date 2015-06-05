# -*- coding: utf-8 -*-

"""
NPC360 Engine - for more info, check out the wiki @ https://github.com/NPC360/NPC360

"""

from flask import request, session, Flask, render_template, Response, redirect, url_for
import forms
import requests
import json
import re
import random
from os import environ
import tinys3
import string

# external method libraries.
from user import *
from game import *
from auth import *

# Initialise the Flask app
app = Flask(__name__)
app.config['PROPAGATE_EXCEPTIONS'] = True
app.secret_key = environ['SecretSessionKey']

# start logging?
from logstuff import *

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


@app.route("/careers/application_received/")
def careers_auth_success():
    return render_template('signup-success.html')


@app.route("/careers/job-2342/apply/", methods=['GET', 'POST'])
def careers_signup():
    # Create the form instance
    form = forms.FullSignup(request.form)

    # Validate form

    #### DEBUG
    log.debug('request method: %s' % (request.method))
    log.debug('form validate: %s' % ( form.validate() ))

    for fieldName, errorMessages in form.errors.iteritems():
        for err in errorMessages:
            print log.debug('form errors: %s, %s' % (fieldName, err))
    ####

    if request.method == 'POST' and form.validate():

        # Save form data in a session
        session['form'] = form.data
        log.debug('form data: %s' % (session['form']))

        auth = str(random.randint(1000, 9999))
        #uid = newAuth(auth)
        session['form']['uid'] = newAuth(auth)
        log.info('auth code: %s, player uid: %s' % (auth, session['form']['uid']))
        session['sent_sms'] = signupSMSauth(session['form']['mobile_number'], auth)

        if session['sent_sms'] is True:
            # Redirect to SMS auth page
            log.debug('redirecting to /careers/auth')
            return redirect(url_for("careers_sms_auth"))
        else:
            # if sent_sms is false, we need to trigger a visual error, because something got fucked up with the SMS (bad phone # / used landline instead of mobile / etc.)
            log.debug('there was an error with that phone # - edirecting to sign up form')
            return render_template('signup-bad-mobile.html', form=form)

    else:
        log.debug('ELSE -- redirecting to sign up form again')
        return render_template('signup-form.html', form=form)

@app.route("/careers/auth/", methods=['GET', 'POST'])
def careers_sms_auth():
    # If the SMS hasn't been sent, jump back a step
    log.debug("value of sms_sent: %s" % (session.get('sent_sms')) )
    if session['sent_sms'] is not True:
        # need to raise a visual error here (once we actually have error checking for bad phone / land line phone numbers)
        log.debug('sent_sms is not True, so redirect back to signup form')
        return redirect(url_for("careers_signup"))

    form = forms.SMSAuth(request.form)

    # Validate form

    #### DEBUG
    log.debug('request method: %s' % (request.method))
    log.debug('form validate: %s' % ( form.validate() ))

    for fieldName, errorMessages in form.errors.iteritems():
        for err in errorMessages:
            print log.debug('form errors: %s, %s' % (fieldName, err))
    ####

    if request.method == 'POST' and form.validate():
        # Create the user
        fname = session['form']['first_name']
        lname = session['form']['last_name']
        options = {
            'fname': session['form']['first_name'],
            'lname': session['form']['last_name'],
            'tel': session['form']['mobile_number'],
            'tz': session['form']['tz'],
            'email': session['form']['email'],
            'why': session['form']['why_work'],
            'history': session['form']['work_history'],
            'soloteam': session['form']['team_work'],
            'ambitious': session['form']['ambitious'],
            'leaving': session['form']['leaving'],
            'animal': session['form']['animal']
        }
        uid = makeUser(options)
        log.info('new user created : %s %s, uid: %s' % (fname, lname, uid))

        # ok, let's clear all out session variables now.
        session['sent_sms'] = False;
        session.pop('form', None)

        # now, schedule game start by scheduling advanceGame() worker
        log.debug('starting game for player uid: %s' % uid)
        startGame(uid)

        # Success!
        return redirect(url_for("careers_auth_success"))
    else:
        log.info('form validation error *probably*')
        return render_template('signup-auth.html', form=form)


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
    processInput(u, stripPunctuation( msg.lower() ))

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

"""
User API routes
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


if __name__ == "__main__":
    app.run(debug=True)

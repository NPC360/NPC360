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
import random
from os import environ
import tinys3

# external method libraries.
from user import *
from game import *
from yesnoerr import *

# Initialise the Flask app
app = Flask(__name__)
app.config['PROPAGATE_EXCEPTIONS'] = True
app.secret_key = environ['SecretSessionKey']

# start logging?
import logstuff

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
        log.debug('awaiting_auth = false, redirecting to /careers/job-2342/apply/')
        return redirect(url_for("/careers/job-2342/apply/"))

    # If the SMS hasn't been sent, jump back a step
    if session.get('sent_sms', False) is True:
        log.debug('auth sms not sent, redirecting to /careers/auth/2/')
        return redirect(url_for("/careers/auth/2/"))

    # Create the form instance
    form = forms.FullSignup(request.form)

    # Send Auth SMS
    # add data to table for lookup later on & get row id/token
    if request.method == 'GET' or request.method == 'POST' and form.validate():
        auth = str(random.randint(1000, 9999))
        uid = newAuth(auth)
        log.info('auth code: %s, player uid: %s' % (auth, uid))
        session['sent_sms'] = signupSMSauth(session['mobile_number'], auth)

    if session.get('sent_sms') is True:
        log.debug('sent_sms, redirecting to /careers/auth2/')
        return redirect(url_for("/careers/auth/2/"))
    else:
        return render_template('signup-bad-mobile.html', form=form)


@app.route("/careers/job-2342/apply/", methods=['GET', 'POST'])
def signup():
    # If the user has already signed up and is awaiting an auth
    # SMS to come in, redirect them to the auth page
    if (session.get('awaiting_auth') is True):
        log.debug('redirecting to /careers/auth')
        return redirect(url_for("/careers/auth/"))

    # Create the form instance
    form = forms.FullSignup(request.form)

    # Validate form
    if request.method == 'POST' and form.validate():

        # Save form data in a session
        session.update(form.data)
        log.debug('form data: %s' % (form.data))

        # Indicate that the user is attempting
        # to authenticate their phone number
        log.debug('setting awaiting_auth = True')
        session['awaiting_auth'] = True

        # Redirect to SMS auth page
        log.debug('redirecting to /careers/auth')
        return redirect(url_for("/careers/auth/"))
    else:
        return render_template('signup-form.html', form=form)


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

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

# external method libraries.
from user import *
from game import *
from yesnoerr import *
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


@app.route("/careers/auth/success/")
def careers_auth_success():
    return render_template('signup-success.html')


@app.route("/careers/auth/2/")
def careers_auth_check_code():
    # Check that the user is awaiting an auth SMS, if they're
    # not, redirect them to the job app
    if session.get('awaiting_auth') is not True:
        log.debug('awaiting_auth != True, redirecting to /careers/job-2342/apply/')
        return redirect(url_for("signup"))

    # If the SMS hasn't been sent, jump back a step
    if session.get('sent_sms') is not True:
        log.debug('sent_sms != True, so redirect to careers/auth')
        return redirect(url_for("careers_auth_send_sms"))

    form = forms.SMSAuth(request.form)


    #### DEBUG
    log.debug('request method: %s' % (request.method))
    log.debug('form validate: %s' % ( form.validate() ))

    for fieldName, errorMessages in form.errors.iteritems():
        for err in errorMessages:
            print log.debug('form errors: %s, %s' % (fieldName, err))
    ####


    # Hey Lach - where are you setting these session vars???
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
        return redirect(url_for("careers_auth_success"))
    else:
        return render_template('signup-auth.html', form=form, name=session.get("fname"))


@app.route("/careers/auth/")
def careers_auth_send_sms():
    # Check that the user is awaiting an auth SMS, if they're
    # not, redirect them to the registration page
    if session.get('awaiting_auth') is not True:
        log.debug('awaiting_auth = false, redirecting to /careers/job-2342/apply/')
        return redirect(url_for("signup"))

    # has sms been sent?
    log.debug("value of sms_sent: %s" % (session.get('sent_sms')) )

    # If the SMS hasn't been sent, jump back a step
    if session.get('sent_sms') is False:
        log.debug('auth sms not sent, redirecting to /careers/job-2342/apply/')
        return redirect(url_for("signup"))

    # If it has been set, let's advance.
    if session.get('sent_sms') is True:
        log.debug('sent_sms is True, redirecting to /careers/auth2/')
        return redirect(url_for("careers_auth_check_code"))

    # Create the form instance
    form = forms.FullSignup(request.form)

    # Send Auth SMS
    # add data to table for lookup later on & get row id/token
    if request.method == 'GET' or request.method == 'POST' and form.validate() and session.get('sent_sms') is None:
        auth = str(random.randint(1000, 9999))
        uid = newAuth(auth)
        log.info('auth code: %s, player uid: %s' % (auth, uid))
        session['sent_sms'] = signupSMSauth(session['mobile_number'], auth)
        return redirect(url_for("careers_auth_check_code"))
    else:
        return render_template('signup-bad-mobile.html', form=form)


@app.route("/careers/job-2342/apply/", methods=['GET', 'POST'])
def signup():
    # If the user has already signed up and is awaiting an auth
    # SMS to come in, redirect them to the auth page
    if (session.get('awaiting_auth') is True):
        log.debug('redirecting to /careers/auth')
        return redirect(url_for("careers_auth_send_sms"))

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
        session.update(form.data)
        log.debug('form data: %s' % (form.data))

        # Set flag to indicate user should be @ SMS authentication step
        log.debug('setting awaiting_auth = True')
        session['awaiting_auth'] = True
        # Redirect to SMS auth page
        log.debug('redirecting to /careers/auth')
        return redirect(url_for("careers_auth_send_sms"))

    else:
        log.debug('ELSE -- redirecting to application again')
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

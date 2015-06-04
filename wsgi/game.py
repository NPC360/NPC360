"""
Gameplay methods
"""
import re
import random
from firebase import firebase
import arrow
from os import environ
from sqlalchemy import *
from sqlalchemy.exc import IntegrityError
from sqlalchemy.exc import CompileError
from iron_worker import *
import string

from yesnoerr import *
from user import *
from telUtil import *
from logstuff import *

def startGame(uid):
    player = getUser(uid)

    updateUser(player['id'], {"gstate":101})
    gs = getGameStateData(101)

    # send application acceptence email from HR
    log.debug('sending HR email for player uid: %s' % (uid))
    hrEmail(getUser(uid))

    # get npc data
    npc = getNPC(player, gs['prompt']['npc'])
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

def processInput(player, msg):
    log.debug('processing input: %s, type: %s' % (msg, type(msg)))
    gameState = player['gstate']
    gameStateData = getGameStateData(gameState)

    #special reset / debug method
    if "magicreset" in msg.lower():
        log.warning('MANUAL GAME RESET FOR PLAYER: %s' % (player['id']))
        startGame(player['id'])

    elif 'triggers' in gameStateData and gameStateData['triggers'] is not None:
        triggers = gameStateData['triggers']
        log.debug('triggers %s' % (triggers))

        # create a copy of the trigger list and pop off any non-gamestate specific triggers.
        sT = triggers.copy()
        sT.pop('yes', None)
        sT.pop('no', None)
        sT.pop('error', None)
        sT.pop('noresp', None)
        sT.pop('*', None)

        # ^^^this array only contains triggers that aren't tied to special keywords / operations
        log.debug('truncated triggers %s' % (sT))

        # check for 'any input response (*)'
        if '*' in triggers and msg is not None:
            log.debug('`any input` trigger')
            advanceGame(player, triggers['*'])

        # check for affirmative / negative responses
        elif 'yes' in triggers or 'no' in triggers:
            log.debug('checking yes/no list')
            if searchText(msg, yeslist) is not None:
                log.debug('input matches yeslist')
                advanceGame(player, triggers['yes'])
            elif searchText(msg, nolist) is not None:
                log.debug('input matches nolist')
                advanceGame(player, triggers['no'])
            else:
                log.debug('input does not match yes/no list')

        # ok, now run through remaining triggers.
        else:
            trig = searchText(msg, sT)
            if trig is None:
                log.warning('input does not match triggers, sending error SMS')
                sendErrorSMS(player)
            else:
                log.debug('input matches trigger: %s, advancing to gs: %s' % (trig, triggers[trig]) )
                advanceGame(player, triggers[trig])

def getGameStateData(id):
    fb = firebase.FirebaseApplication(environ['FB'], None)
    data = fb.get('/gameData/'+ str(id), None)
    log.debug('game data: %s' % (data))
    return data

def stripPunctuation(msg):
    words = [word.strip(string.punctuation) for word in msg.split(" ")]
    s = " ".join(words)
    return s

# search for text within trigger array
def searchText(msg, array):
    text = stripPunctuation(msg)
    log.debug("checking: %s" % (text))
    match = searchIter(text, array)

    if match is None:
        log.debug("no match found")
        return None
    else:
        log.debug("match found: %s" % match)
        return match

def searchIter(text, array):
    for t in array:
        s = re.search(r'\b(%s)\b' % t, text, re.I|re.M)
        if s is not None:
            return s.group(1)

#THIS METHOD IS NOT COMPLETE
def advanceGame(player, gsid):
    # advance user state, send new prompt, log game state change?
    log.info('advancing user: %s to game state %s' % (player['id'], gsid))
    updateUser(player['id'], {"gstate":gsid})
    gs = getGameStateData(gsid)
    npc = getNPC(player, gs['prompt']['npc'])
    #### Fill in variables like %%fname%% <- use data from player dict.
    msg = getPlayerVars(player, gs['prompt']['msg'])
    log.debug('msg w/ player vars: %s' % msg)

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
    log.debug('%s' % smsResp)
    log.debug('gamestate info from advanceGame method: %s' % gs['prompt'])

    # after sending prompt, if there's a goto statement, we can jump forward in the game. this is for sequential msg prompts.
    if 'goto' in gs['prompt']:
        log.info('jumping player %s to game state: %s' % (player['id'], gs['prompt']['goto']))
        advanceGame(player, gs['prompt']['goto'])

    # 'potato hacks' / dbchecks -- or more accurately, using player data to control gameflow between states (not just personalizing outgoing messages)
    if 'dbcheck' in gs and gs['dbcheck'] is not None:
        log.debug('player %s hit a dbcheck @ %s' % (player['id'], gsid))

        # get name of db field & extract path tree to own subvariable
        dbfield = gs['dbcheck']['field']
        paths = gs['dbcheck']['paths']
        log.debug('player enum for -%s- is: %s' % (dbfield, player[dbfield]))
        log.debug( 'paths: %s' % (paths))

        for k in paths:
            log.debug('k: %s, v: %s' % (k, paths[k]) )
            log.debug('now checking path: %s vs. player[%s]: %s' % (paths[k], dbfield, player[dbfield]))

            if str(paths[k]) == str(player[dbfield]):
                log.debug('jumping player %s to game state: %s' % (player['id'],k))
                advanceGame(player, k)

def getPlayerVars(player, msg):
    merge = re.findall(r'%%([^%%]*)%%', msg)
    for x in merge:
        if player[x.lower()]:
            msg = re.sub('%%'+x+'%%', player[x], msg)
    return msg

# get NPC info & tel by matching NPC number and the country code of player.
def getNPC(playerInfo, npcName):
    db = create_engine(environ['OPENSHIFT_MYSQL_DB_URL'] + environ['OPENSHIFT_APP_NAME'], convert_unicode=True, echo=False)
    md = MetaData(bind=db)
    table = Table('npcInfo', md, autoload=True)
    con = db.connect()

    x = con.execute( table.select().where(and_(table.c.name == npcName, table.c.country == playerInfo['country'])))

    row = x.fetchone()
    con.close()
    return row

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



"""
INPUT / OUTPUT (SMS, signup auth, eail, etc.)
"""

#This method is 'dumb'. All it does is accept data, build a payload, and schedule a job. If the job is queued successfully, it returns a task/job id. It doesen't know it's sending an SMS!!!
def sendSMS(f,t,m,u,d,st):
    # f - from
    # t - to
    # m - msg
    # u - url
    # d - delay
    # st - absolute send time

    worker = IronWorker(project_id=environ['IID2'], token=environ['ITOKEN2'])
    task = Task(code_name="smsworker", scheduled=True)

    task.payload = {"keys": {"auth": environ['TSID'], "token": environ['TTOKEN']}, "fnum": f, "tnum": t, "msg": m, "url": u}

    # scheduling conditions
    if d is not None:
        task.delay = d
        log.info('sending sms after %s second delay' % (d) )
    elif st is not None:
        task.start_at = st # desired `send @ playertime` converted to servertime
        log.info('sending sms at %s' % (st))
    else:
        task.delay = 0
        log.info('sending sms right away')

    # now queue the damn thing & get a response.
    response = worker.queue(task)
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
        log.info('sending email after %s second delay' % (d) )
    elif st is not None:
        task.start_at = st # desired `send @ playertime` converted to servertime
        log.info('sending email at %s' % (st))
    else:
        task.delay = 0
        log.info('sending email right away')

    # now queue the damn thing & get a response.
    response = worker.queue(task)
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

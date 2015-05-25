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

        sT = triggers.copy()
        sT.pop('yes', None)
        sT.pop('no', None)
        sT.pop('error', None)
        sT.pop('noresp', None)
        sT.pop('*', None)

        # this array only contains triggers that aren't tied to special keywords / operations ^^
        log.debug('truncated triggers %s' % (sT))

        # check for 'any input response (*)'
        if '*' in triggers and msg is not None:
            advanceGame(player, triggers['*'])

        # check for affirmative / negative responses
        if 'yes' in triggers:
            log.debug('running a yeslist check')
            if checkYes(msg) is True:
                log.debug('input matches term from yeslist')
                advanceGame(player, triggers['yes'])
            else:
                log.debug('input did not match term from yeslist')

        if 'no' in triggers:
            log.debug('running a nolist check')
            if checkNo(msg) is True:
                log.debug('input matches term from nolist')
                advanceGame(player, triggers['no'])
            else:
                log.debug('input did not match term from nolist')

        # check if response is even in the list
        #elif msg.lower() not in sT:
        elif any(y.lower() in msg for y in sT):
            log.debug('running a check for OTHER triggers (not *, yes, or no)')
            for x in sT:
                if x.lower() in msg.lower():
                    log.debug('%s is in %s' % (x, msg))
                    advanceGame(player, triggers[x])
                    break
        else:
            log.warning('input does not match any triggers')
            sendErrorSMS(player)


def getGameStateData(id):
    fb = firebase.FirebaseApplication(environ['FB'], None)
    data = fb.get('/gameData/'+ str(id), None)
    #print 'game data:', str(data)
    log.debug('game data: %s' % (data))
    return data

def stripPunctuation(msg):
    # split string into words & strip punctuation
    words = [word.strip(string.punctuation) for word in msg.split(" ")]
    # recombine words into sentence
    s =""
    for w in words:
        s = s+" "+w
    return s

def checkYes(msg):

    if any(y.lower() in msg for y in yeslist):
        return True
    else:
        return False

def checkNo(msg):

    if any(n.lower() in msg for n in nolist):
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
        log.info('jumping player %s to game state: %s' % (player['id'], gs['prompt']['goto']))
        advanceGame(player, gs['prompt']['goto'])


    # 'potato hacks' / dbchecks -- or more accurately, using player data to control gameflow between states (not just personalizing outgoing messages)
    if 'dbcheck' in gs and gs['dbcheck'] is not None:
        log.debug('player %s hit a dbcheck @ %s' % (player['id'], gsid))

        # get name of db field & extract path tree to own subvariable
        dbfield = gs['dbcheck']['field']
        paths = gs['dbcheck']['paths']
        log.debug('player enum for -%s- is: %s' % (dbfield, player[dbfield]))

        for p in paths:
            if p == player[dbfield]:
                log.debug('jumping player %s to game state:' % (player['id'], paths[p]))
                advanceGame(player, paths[p])

    """
    # POTATO HACKS -- these methods are for jumping to db checks & then coming back.
    if gsid == '126':
        log.debug('player %s hit a potato hack: %s' % (player['id'], gsid))
        hack_126(player)

    elif gsid == '133':
        log.debug('player %s hit a potato hack: %s' % (player['id'], gsid))
        hack_133(player)

    elif gsid == '142':
        log.debug('player %s hit a potato hack: %s' % (player['id'], gsid))
        hack_142(player)

    elif gsid == '156':
        log.debug('player %s hit a potato hack: %s' % (player['id'], gsid))
        hack_156(player)
    """

def getPlayerVars(player, msg):
    merge = re.findall(r'%%([^%%]*)%%', msg)
    for x in merge:
        #print x
        if player[x.lower()]:
            msg = re.sub('%%'+x+'%%', player[x], msg)
            #print msg
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
    #print "####"

    worker = IronWorker(project_id=environ['IID2'], token=environ['ITOKEN2'])
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

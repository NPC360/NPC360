"""
User MySQL DB methods
"""
import datetime
from os import environ
from sqlalchemy import *
from sqlalchemy.exc import IntegrityError
from sqlalchemy.exc import CompileError
import normalizeTel
#from gameio import normalizeTel, sendSMS, sendErrorSMS, sendEmail

# lookup user from datastore using a provided 'id' - could be uid, phone / email / twitter handle, etc. (should be medium agnostic)
def getUser(uid):
    db = create_engine(environ['OPENSHIFT_MYSQL_DB_URL'] + environ['OPENSHIFT_APP_NAME'], convert_unicode=True, echo=False)
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
        md = MetaData(bind=db)
        table = Table('playerInfo', md, autoload=True)
        con = db.connect()
        res = con.execute( table.update().where(table.c.id == uid).values(data) )
        con.close()
        return res.last_updated_params()

    except (CompileError, IntegrityError) as e:
        #print e
        log.debug('error %s' % (e))

from iron_worker import *
import datetime
import random
from os import environ
import os

def sendSMS(f,t,m,u,d,st):
    # f - from
    # t - to
    # m - msg
    # u - url
    # d - delay
    # st - absolute send time

    print "####"
    print f
    print t
    #print m
    print u
    print d
    print st
    print "####"

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

sendSMS('+17183959467', '+13093978751', 'BLERP', None, 0, None)

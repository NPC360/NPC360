import twilio
import twilio.rest
import twilio.twiml

# retreive payload
import sys, json
pl = None
plf = None
for i in range(len(sys.argv)):
    if sys.argv[i] == "-payload" and (i + 1) < len(sys.argv):
        plf = sys.argv[i + 1]
        break

f = open(plf, "r")
contents = f.read()
f.close()
pl = json.loads(contents)
print pl

## ## ## ## ## ## ## ## ## ##

# send msg via Twilio
try:
    c = twilio.rest.TwilioRestClient(pl["keys"]["auth"], pl["keys"]["token"])

    if pl["url"]:
        m = c.messages.create(
        to = pl["tnum"],
        from_= pl["fnum"],
        body = pl["msg"],
        media_url = pl["url"]
    )
    else:
        m = c.messages.create(
        to = pl["tnum"],
        from_ = pl["fnum"],
        body = str(pl["msg"])
    )
    # if succesful, return true as a 'success flag'
    print m.sid
    #return True

# if not succesful, return flag flag
except twilio.TwilioRestException as e:
    print e
    #return False

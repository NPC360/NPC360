import requests

# retrieve payload
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

# send msg via Mailgun

# dom - MG domain
# key - MG api key
# fr - npc dict
# to - player dict
# sub - subject line
# txt - text version of email
# html - html version of email

r = requests.post(
      pl['dom'],
      auth=("api", pl['key']),
      data={
          "from": pl['fr']['name'] +" <"+ pl['fr']['email']+">",
          "to": pl['to']['name'] +" <"+ pl['to']['email']+">",
          "subject": pl['sub'],
          "text": pl['txt'],
          "html": pl['html']})

if r.status_code == 200:
    print "Msg id: " + r.json()['id']
else:
    print "Mailgun API error"

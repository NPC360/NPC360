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
# fe - npc email
# fn - npc display_name
# te - player email
# tn - player name
# sub - subject line
# txt - text version of email
# html - html version of email

r = requests.post(
      pl['dom'],
      auth=("api", pl['key']),
      data={
          "from": pl['fn'] +" <"+ pl['fe']+">",
          "to": pl['tn'] +" <"+ pl['te']+">",
          "subject": pl['sub'],
          "text": pl['txt'],
          "html": pl['html']})

if r.status_code == 200:
    print "Msg id: " + r.json()['id']
else:
    print "Mailgun API error"

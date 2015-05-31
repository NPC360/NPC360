import re
from yesnoerr import *
import string

def stripPunctuation(msg):
    words = [word.strip(string.punctuation) for word in msg.split(" ")]
    s = " ".join(words)
    return s

# search for text within trigger array
def searchText(msg, triggers):
    text = stripPunctuation(msg)
    print "checking: %s" % (text)
    match = searchIter(text, triggers)

    if match is None:
        print "no match found"
    else:
        print "match found: %s" % match

def searchIter(text, triggers):
    for t in triggers:
        s = re.search(r'\b(%s)\b' % t, text, re.I|re.M)
        if s is not None:
            return s.group(1)


print "\nCHECK YES"
searchText('let\'s do it already.', yeslist) #yes
searchText('let\'s', yeslist) #no
searchText('yes.', yeslist) #yes
searchText('no', yeslist) #no
searchText('yep', yeslist) #yes
searchText('yeppers', yeslist) #yes
searchText('by all means, please do so.', yeslist) #yes
searchText('yes but no', yeslist) #yes
searchText('I\'ll gladly come down and handle that for you.', yeslist) #yes
searchText('That\'s ok with me bruh.', yeslist) #yes
searchText('sure thing - send it my way', yeslist) #yes
searchText('fo sho bruh', yeslist) #yes

print "\nCHECK NO"
searchText('sorry, but I can\'t.', nolist) #no
searchText('nah', nolist) #no
searchText('fuck that noise, I\'m going out and never coming back.', nolist) #no
searchText('blerg, not this time.', nolist) #no
searchText('that\'s a big negatory old buddy', nolist) #no
searchText('yes, I\'d love too!', nolist) #yes

print "\nCHECK TRIGGERS"
tr = {
    "who":"a",
    "amused":"b",
    "or four":"c",
    "kennywood":"d",
    "don\'t":"e"
    }

searchText('who?', tr) #pass
searchText('who is this?', tr) #pass
searchText('i am not amused or something', tr) #pass
searchText('three or four', tr) #pass
searchText('kennywood up in this!', tr) #pass
searchText('i don\'t care for this', tr) #pass
searchText('who? is going to that thing?', tr) #pass
searchText('what are you even talking about?', tr) # does not pass

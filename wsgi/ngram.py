"""
  break up msg into 3word ngrams
  for each ngram, concat into a string

  check each string for a substring containing terms from global yes/no array (as words - not just substrings)
  - if term exists, break out of loop and advanceGame
"""
import re
from yesnoerr import *
import string
from nltk.tokenize import RegexpTokenizer
from nltk.util import ngrams as NG
tok = RegexpTokenizer("[\\w']+|[^\\w\\s]+")


def stripPunctuation(msg):
    # split string into words & strip stripPunctuation
    words = [word.strip(string.punctuation) for word in msg.split(" ")]
    # recombine words into sentence
    s =""
    for w in words:
        s = s+" "+w
    return s

# checkYes & checkNo look for yes/no matches, but don't return the matched response. They just return True if they find something.
def checkYes(msg):
    # break up msg into 3-word ngrams
    text = tok.tokenize(stripPunctuation(msg))
    print "checking: %s" % (text)
    ngrams = NG(text, 3)


    # if our message is just 1 word, run a simple `in msg` check for yeslist
    if len(ngrams) < 1:
        if any(yes.lower() in text for yes in yeslist):
            print 'YES'
            return True

    # otherwise, rock and roll on the big long regex search
    else:
        for n in ngrams:
            ng = ' '.join(n)
            if any(re.search(r'\b(%s)\b' % yes, ng, re.I|re.M) for yes in yeslist):
                print 'YES'
                return True

def checkNo(msg):
    # break up msg into 3-word ngrams
    text = tok.tokenize(stripPunctuation(msg))
    print "checking: %s" % (text)
    ngrams = NG(text, 3)

    # if our message is just 1 word, run a simple `in msg` check for nolist
    if len(ngrams) < 1:
        if any(no.lower() in text for no in nolist):
            print 'NO'
            return True

    # otherwise, rock and roll on the big long regex search
    else:
        for n in ngrams:
            ng = ' '.join(n)
            if any(re.search(r'\b(%s)\b' % no, ng, re.I|re.M) for no in nolist):
                print 'NO'
                return True

# Unlike checkYes & checkNo, this method returns the match - this is so we can advance the game.
def checkTriggers(msg, triggers):
    # break up msg into 3-word ngrams
    text = tok.tokenize(stripPunctuation(msg))
    print "checking: %s" % (text)
    ngrams = NG(text, 3)

    # if our message is just 1 word, run a simple `in msg` check for nolist
    if len(ngrams) < 1:
        match = searchTriggers(str(text), triggers)

    # otherwise, rock and roll on the big long regex search
    else:
        #match = None # temp var
        for n in ngrams:
            ng = ' '.join(n)
            match = searchTriggers(ng, triggers)
            if match is not None:
                break

    if match is None:
        print "no match found"
    else:
        print "match found: %s" % match

def searchTriggers(text, triggers):
    for t in triggers:
        #print 'comparing: %s and: %s' % (t, text)
        s = re.search(r'\b(%s)\b' % t, text, re.I|re.M)
        if s is not None:
            #print 'match: %s' % s.group(1)
            return s.group(1)

print "\nCHECK YES"
checkYes('let\'s do it already.') #yes
checkYes('let\'s') #no
checkYes('yes.') #yes
checkYes('no') #no
checkYes('yep') #yes
checkYes('yeppers') #yes
checkYes('by all means, please do so.') #yes
checkYes('yes but no') #yes
checkYes('I\'ll gladly come down and handle that for you.') #yes
checkYes('That\'s ok with me bruh.') #yes
checkYes('sure thing - send it my way') #yes
checkYes('fo sho bruh') #yes

print "\nCHECK NO"
checkNo('sorry, but I can\'t. ') #no
checkNo('nah') #no
checkNo('fuck that noise, I\'m going out and never coming back.') #no
checkNo('blerg, not this time.') #no
checkNo('that\'s a big negatory old buddy') #no
checkNo('yes, I\'d love too!') #yes

print "\nCHECK TRIGGERS"
tr= {
    "who":"a",
    "amused":"b",
    "or four":"c",
    "kennywood":"d",
    "don\'t":"e"
    }

checkTriggers('who?', tr) #pass
checkTriggers('who is this?', tr) #pass
checkTriggers('i am not amused or something', tr) #pass
checkTriggers('three or four', tr) #pass
checkTriggers('kennywood up in this!', tr) #pass
checkTriggers('i don\'t care for this', tr) #pass
checkTriggers('who? is going to that thing?', tr) #pass
checkTriggers('what are you even talking about?', tr) # does not pass

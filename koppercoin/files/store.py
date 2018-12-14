from twisted.internet.fdesc import setNonBlocking, readFromFD, writeToFD
from twisted.internet.defer import Deferred

# this manifests the store
# stores files to disk
# reads files fromd isk

sizelimit = 0 # no limit yet

def log(msg):
    import datetime
    print('\033[93m'+msg+'\033[0m')

def store(content, id):
    log("Storing file of size: "+str(len(content)))
    #log("Writing: "+str(content))
    with open(id+".kc", 'w') as file:
        #fd = file.fileno()
        #setNonBlocking(fd)
        #writeToFD(fd, content)
        file.write(content)

def retrieve(fileid):
    #log("Retrieve called with: "+fileid)
    d = Deferred()
    with open(fileid+".kc",'r') as file:
        # fd = file.fileno()
        # setNonBlocking(fd)
        # readFromFD(fd, d.callback) # only reads 8192 bytes........
        d.callback(file.read())
    return d

def listoffiles():
    import os
    return [_ for _ in os.listdir() if _.endswith(".kc")]
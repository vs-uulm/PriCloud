from twisted.internet.endpoints import TCP4ServerEndpoint, TCP4ClientEndpoint
from twisted.internet import reactor
from p2p import *
from random import randint

port = randint(27347,55555)
factory = KCFactory(port)

log("Init on port "+str(port))

endpoint = TCP4ServerEndpoint(reactor, port)
endpoint.listen(factory)
# for bootstrap in range(5):
point = TCP4ClientEndpoint(reactor, "localhost", 27346)
d = point.connect(factory)
d.addCallback(gotProtocol)
reactor.run()
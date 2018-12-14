from twisted.internet.endpoints import TCP4ServerEndpoint, TCP4ClientEndpoint, connectProtocol
from twisted.internet import reactor
from koppercoin.network.p2p import *

# for bootstrap in range(5):
point = TCP4ClientEndpoint(reactor, "134.60.77.158", 27346)
d = point.connect(KCFactory(27346, None, None, None))
d.addCallback(gotProtocol)
reactor.run()
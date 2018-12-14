from twisted.internet.endpoints import TCP4ServerEndpoint, TCP4ClientEndpoint, connectProtocol
from twisted.internet import reactor
from koppercoin.network.p2p import *

endpoint = TCP4ServerEndpoint(reactor, 27346)
endpoint.listen(KCFactory(27346, None, None, None))
reactor.run()

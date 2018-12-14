from twisted.internet.protocol import Factory
from twisted.internet.task import LoopingCall
from twisted.protocols.basic import LineReceiver
from twisted.internet.defer import Deferred
from twisted.internet.error import ConnectionDone
from twisted.internet import reactor
from time import time
from uuid import uuid4 as uuid
import json
import datetime
import random
import hashlib
from collections import defaultdict

def log(msg):
    print('\033[93m'+msg+'\033[0m')
    #print('\033[93m'+datetime.datetime.now().strftime("%d.%m, %H:%M:%S")+": "+msg+'\033[0m')


class Mixin():
    def __init__(self):
        self.msgtypes = {}
        self.entrances = {}
    def start(self, **kwargs): # entrce for action
        pass
    def connectionMade(self):
        pass
    def connectionInit(self):
        pass
    def connectionLost(self):
        pass


class PingPong(Mixin):
    def __init__(self, protocol):
        self.protocol = protocol
        self.looping = LoopingCall(self.send_ping)
        self.islooping = False
        self.lastping = None
        self.msgtypes = {'ping': self.handle_ping, 'pong': self.handle_pong}
        self.entrances = {}

    def send_ping(self):
        self.protocol.send({'msgtype': 'ping'})

    def send_pong(self):
        self.protocol.send({'msgtype': 'pong'})

    def handle_ping(self, msg):
        self.send_pong()

    def handle_pong(self, msg):
        #log("Successful ping/pong: "+str(self.protocol.remote))
        self.lastping = time()

    def connectionInit(self):
        if not self.islooping:
            self.looping.start(60)
            self.islooping = True

    def connectionLost(self):
        if self.islooping:
            self.looping.stop()


class Gossip(Mixin):
    def __init__(self, protocol, addressstore):
        self.protocol = protocol
        self.addresses = addressstore
        self.msgtypes = {'getaddr': self.handle_getaddr, 'addrlist': self.handle_addrlist}
        self.entrances = {}

    def start(self, **kwargs):
        self.send_getaddr()

    def send_getaddr(self):
        self.protocol.send({'msgtype': 'getaddr'})

    def send_addrlist(self):
        self.protocol.send({'msgtype': 'addrlist', 'hosts': self.addresses.sample()})

    def handle_getaddr(self, msg):
        self.send_addrlist()

    def handle_addrlist(self, msg):
        for host,port,uuid in msg['hosts']:
            self.addresses.add((host,port,uuid))
        self.protocol.factory._updateConnections()

    def connectionInit(self):
        self.send_addrlist()
        self.send_getaddr()


class Transactions(Mixin):
    def __init__(self, protocol):
        self.protocol = protocol
        self.factory = protocol.factory
        self.msgtypes = {'transaction': self.handle_transaction}
        self.entrances = {'tx': self.start}

    def start(self, **kwargs):
        self.send_transaction(kwargs['tx'])

    def send_transaction(self, tx):
        self.protocol.send({'msgtype': 'transaction', 'tx': tx.json()})

    def handle_transaction(self, msg):
        from koppercoin.tokens.model import Transaction
        tx = Transaction.from_json(msg["tx"])
        self.factory.publishTransaction(tx)


class Blocks(Mixin):
    def __init__(self, protocol):
        self.protocol = protocol
        self.factory = protocol.factory
        self.msgtypes = {'block': self.handle_block}
        self.entrances = {'block': self.start}

    def start(self, **kwargs):
        self.send_block(kwargs['block'])

    def send_block(self, block):
        self.protocol.send({'msgtype': 'block', 'block': block.json()})

    def handle_block(self, msg):
        from koppercoin.tokens.model import Block
        block = Block.from_json(msg["block"])
        self.factory.publishBlock(block)
        self.factory.blockchain.add_block(block)
        reactor.callInThread(self.factory.wallet.rescan_blockchain)
        #self.factory.wallet.rescan_blockchain()
        # todo check validity and remove tx from mempool


class StoreFile(Mixin):
    def __init__(self, protocol):
        self.protocol = protocol
        self.factory = protocol.factory
        self.msgtypes = {'offercontract': self.handle_offer,
                         'answercontract': self.handle_answer,
                         'fileupload': self.handle_file}
        self.entrances = {'store': self.start}

    def start(self, **kwargs):
        self.send_offer(kwargs["file"], kwargs["size"])

    def send_offer(self, id, size):
        # client
        self.protocol.send({'msgtype': 'offercontract', 'fileid': id, 'size': size})

    def send_answer(self, id):
        # server
        key = json.dumps(self.protocol.factory.wallet.public_key)
        self.protocol.send({'msgtype': 'answercontract', 'key': key, 'fileid': id, 'cost': str(25)})

    def send_file(self, id):
        # client
        try:
            self.protocol.send({'msgtype': 'fileupload', 'fileid': id, 'file': self.factory.file[id][0]})
            del self.factory.file[id]
        except Exception as e:
            pass#log(str(e))

    def handle_offer(self, msg):
        # server
        # todo
        log("Request received to store file of size "+str(msg["size"])+".")
        if self.protocol.factory.storage:
            self.send_answer(msg["fileid"])
        else:
            #this node does not store files, so ignore offers
            pass

    def handle_answer(self, msg):
        # client
        fhash = msg["fileid"]
        def select(obj):
            import time
            # select an offer from the collected offers
            offers = obj.file[fhash][2]
            self.factory.file[fhash] = (self.factory.file[fhash][0],"TRANSMIT",[])
            # take minimal cost offer
            mincon, mincost, minkey = min(offers, key = lambda t: int(t[1]))
            log("Selected offer for "+str(mincost)+".")
            #time.sleep(1)
            minkey = json.loads(minkey)
            try:
                contract = self.factory.wallet.gen_transfer_tx(1,[minkey],[int(mincost)],0)
            except Exception as e:
                contract = None
            log("Contract created for "+str(mincost)+" to "+str(minkey[0][:10])+".")
            #time.sleep(1)
            if contract is not None:
                self.factory.publishTransaction(contract)
            log("Contract published.")
            #time.sleep(1)
            mincon.send_file(fhash)
            log("File transmitted successfully.")

        log("Received offer for file costing "+msg["cost"]+".")
        try:
            if self.factory.file[fhash][1] is "INIT":
                self.factory.file[fhash] = (self.factory.file[fhash][0],"COLLECT",[])
                reactor.callLater(5,select, self.factory)
            # if collecting offers, append self and contract information for offer
            if self.factory.file[msg["fileid"]][1] is "COLLECT":
                self.factory.file[msg["fileid"]][2].append((self,msg["cost"],msg["key"]))
            # in other cases ignore the answer
        except Exception as e:
            log(str(e))

    def handle_file(self, msg):
        # server
        log("Received file: "+msg["fileid"])
        try:
            if self.protocol.factory.storage:
                from koppercoin.files.store import store
                store(msg["file"], msg["fileid"])
        except Exception as e:
            log(str(e))
        # todo
        # put file in store only if there is a contract


class RetrieveFile(Mixin):

    def __init__(self, protocol):
        self.protocol = protocol
        self.factory = protocol.factory
        self.msgtypes = {'requestfile': self.handle_madrequest,
                         'filedownload': self.handle_file,
                         'madrelease': self.handle_release,
                         'cancelretrieval': self.handle_cancel}
        self.entrances = {'retrieve': self.start}

    def start(self, **kwargs):
        fileid = kwargs['fileid']
        log("Retrieving keyinformation from Blockchain.")
        import time
        time.sleep(1)
        self.send_madrequest(fileid)

    def send_madrequest(self, fileid):
        # client request
        log("Sending MAD Request for file "+fileid[:8])
        self.protocol.send({'msgtype': 'requestfile', 'fileid': fileid})

    def send_file(self, fileid, file):
        # server answer
        log("Returning file "+fileid[:8])
        self.protocol.send({'msgtype': 'filedownload', 'fileid': fileid, 'file': file})

    def send_madrelease(self, fileid):
        # client release
        log("MAD funds released.")
        self.protocol.send({'msgtype': 'madrelease', 'fileid': fileid})
        del self.factory.files[fileid]

    def send_cancel_file(self, fileid):
        log("Canceling file.")
        self.protocol.send({'msgtype': 'cancelretrieval', 'fileid': fileid})

    def handle_cancel(self, msg):
        log("File canceled.")
        #if self.factory.files.get(msg["fileid"]) is not None:
        #    del self.factory.files[msg["fileid"]]

    def handle_madrequest(self, msg):
        # server
        # todo
        # check and accept/sign mad transaction, broadcast it and send file
        try:
            fileid = msg["fileid"]
            log("Locking MAD funds for file "+fileid[:8])
            import time
            time.sleep(1)
            from koppercoin.files.store import retrieve
            deferred = retrieve(fileid)
            def file_read(file):
                try:
                    #log("File read from disk: "+fileid+" of lenght "+str(len(file)))
                    log("Sending file.")
                    file = json.loads(file) #only return actual file part
                    self.send_file(fileid, file["file"])
                except Exception as e:
                    #print("{0}".format(e))
                    self.send_cancel_file(fileid)
                return file
            deferred.addCallback(file_read)
        except Exception as e:
            pass#print("Mist! {0}".format(e))

    def handle_file(self, msg):
        # client
        # todo
        try:
            import time
            time.sleep(1)
            fileid = msg["fileid"]
            #log("Retrieved file.")
            if self.factory.files.get(fileid) is None or self.factory.files.get(fileid)[0] is not "INIT":
                #log("Invalid state.")
                self.send_cancel_file(fileid)
            self.factory.files.get(fileid)[1].callback(msg["file"])
            time.sleep(1)
            log("Releasing MAD funds.")
            self.send_madrelease(fileid)
        except Exception as e:
            pass#print("HANDLE FILE: {0}".format(e))

    def handle_release(self, msg):
        # server
        # todo
        # broadcast mad release after signing
        pass


class KCProtocol(LineReceiver):
    version = "0.2"
    delimiter = b'\n'

    def __init__(self, factory):
        self.factory = factory
        self.factory.connections.add(self)
        self.remote = None
        self.remoteid = None
        self.addins = [PingPong(self),
                       Gossip(self, self.factory.addresses),
                       StoreFile(self),
                       RetrieveFile(self),
                       Transactions(self),
                       Blocks(self)]
        self.dispatch = defaultdict(lambda: (lambda msg: None))
        self.dispatch.update({"init": self.handle_init, "init2": self.handle_init2})
        self.start = defaultdict(lambda: (lambda **kwargs: None))
        for addin in self.addins:
            self.dispatch.update(addin.msgtypes)
            self.start.update(addin.entrances)

    def connectionMade(self):
        self.remote = self.transport.getPeer()
        self.host =  self.transport.getHost()
        self.factory.addresses.own.add((self.host.host, self.factory.port, self.factory.identity))
        for addin in self.addins:
            addin.connectionMade()
        #log("Connection from "+str(self.remote))

    def connectionLost(self, reason=ConnectionDone):
        #log("Disconnected "+self.remoteid)
        for addin in self.addins:
            addin.connectionLost()
        self.factory.connections.remove(self)

    def lineReceived(self, line):
        # TODO implement routing here
        # data = data.decode("utf-8")
        # log("Received: "+data)
        # for line in data.splitlines():
        # line = line.strip()
        try:
            line = line.decode("utf-8")
            #log("Received: "+line)
            msg = json.loads(line)
            msgtype = msg["msgtype"]
            self.dispatch[msgtype](msg)
        except Exception as e:
            log("Error: "+str(e))

    def send(self, msgdict):
        msgdict['v'] = self.version
        msg = json.dumps(msgdict)
        #log("Sending: "+msg)
        self.sendLine(msg.encode("utf-8"))

    # INIT Handshake
    def send_init(self):
        self.send({'msgtype': 'init', 'uuid': self.factory.identity})

    # INIT2 3WHandshake
    def send_init2(self):
        self.send({'msgtype': 'init2', 'uuid': self.factory.identity})

    def handle_init(self, msg):
        try:
            self.remoteid = msg['uuid']
            #log("New connection: "+self.remoteid)
            if self.remote == self.host or 1<len([1 for _ in self.factory.connections if _.remoteid == self.remoteid]):
                self.transport.loseConnection()
            else:
                self.send_init2()
                for addin in self.addins:
                    addin.connectionInit()
        except Exception as e:
            pass
            #log("Error: "+str(e))

    def handle_init2(self, msg):
        # threeway handshake end
        self.remoteid = msg['uuid']
        #log("Learned uuid "+self.remoteid)
        for addin in self.addins:
            addin.connectionInit()
        try:
            if self.remote == self.host or 1<len([1 for _ in self.factory.connections if _.remoteid == self.remoteid]):
                self.transport.loseConnection()
        except Exception as e:
            pass
            #log("Error: "+str(e))

class HostsStore:
    def __init__(self, own, bootstrap, blacklist):
        self.addresses = set()
        self.own = set(own)
        self.bootstrap = set(bootstrap)
        self.blacklist = set(blacklist)
        self.samplelimit = 5

    def add(self, address):
        if address not in self.bootstrap and address not in self.own and address not in self.blacklist:
            #log("Add to store: "+str(address))
            for adr in self.addresses.copy():
                if adr[2] == address[2]:
                    self.addresses.discard(adr)
            self.addresses.add(address)
        #else:
            #log("Not added to store: "+str(address))

    def remove(self, address):
        #log("Removed from store: "+str(address))
        self.addresses.remove(address)

    def sample(self, includeown=True):
        use = self.addresses
        if includeown:
            use = use.union(self.own)
        return random.sample(use, min(self.samplelimit, len(use)))

    def addtoblacklist(self, entry):
        #log("Add to blacklist: "+str(entry))
        self.blacklist.add(entry)
        self.addresses = self.addresses.difference(self.blacklist)


class KCFactory(Factory):
    def __init__(self, port, blockchain, wallet, mempool, miningmanager, *, storage=False):
        self.identity = str(uuid())
        log("Own identity: "+self.identity)
        self.port = port
        self.blockchain = blockchain
        self.wallet = wallet
        self.mempool = mempool
        self.storage = storage
        self.miningmanager = miningmanager
        self.addresses = HostsStore([], [('127.0.0.1', 27346)], [])
        self.connections = set()
        self.file = defaultdict(lambda: (None, None, None))
        self.files = {} # used for file retrieval
        self.senttx = set() # maybe remove entries after time late
        self.sentblocks = set() # maybe remove entries after time late

    def _updateConnections(self):
        try:
            for a in self.addresses.addresses:
                if len(self.connections) < self.addresses.samplelimit:
                    if a[2] not in [_.remoteid for _ in self.connections]:
                        from twisted.internet.endpoints import TCP4ClientEndpoint
                        #log("Create con. to "+str(a[0])+":"+str(a[1]))
                        point = TCP4ClientEndpoint(reactor, a[0], a[1])
                        d = point.connect(self)
                        d.addCallback(gotProtocol)
        except KeyError:
            #log("Connections not full but no new Connections to establish.")
            pass # no new known addresses, so no new connections
        except Exception as e:
            pass#log(str(e))

    def startFactory(self):
        pass

    def buildProtocol(self, addr):
        return KCProtocol(self)

    def publishBlock(self, block):
        #log("Publishing: "+str(block.hash))
        if block.hash not in self.sentblocks:
            log("New Block! "+str(block.hash[:10]))
            self.sentblocks.add(block.hash)
            for connection in self.connections:
                connection.start["block"](block=block)

    def publishTransaction(self, transaction):
        try:
            if transaction.hash not in self.senttx:
                self.mempool.add(transaction)
                self.miningmanager.add_transaction(transaction)
                self.senttx.add(transaction.hash)
                for connection in self.connections:
                    connection.start["tx"](tx=transaction)
        except Exception as e:
            log(str(e))

    def store(self, file, jstate):
        # start store on all connections
        # jstate needs to be included in transactions, so pass along
        file = file
        thash = hashlib.sha256(file.encode("utf-8")).hexdigest()
        #log("Starting to store file: "+thash)
        self.file[thash] = (file,"INIT", [])
        for connection in self.connections:
            connection.start["store"](file=thash,size=len(file))

    def retrieve(self, id):
        d = Deferred()
        self.files[id] = ("INIT", d)
        # ask all connections for our file
        for connection in self.connections:
            connection.start["retrieve"](fileid=id)
        return d


def gotProtocol(p):
    p.send_init()

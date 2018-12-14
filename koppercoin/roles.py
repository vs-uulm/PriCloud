from crochet import setup, wait_for, run_in_reactor
import base64, zlib
setup()

def log(msg):
    import datetime
    print('\033[93m'+msg+'\033[0m')
    #datetime.datetime.now().strftime("%d.%m, %H:%M:%S")+


class Role():
    def __init__(self, storage=False):
        self.storage = storage
        self.factory = None

    @run_in_reactor
    def start(self):
        from .tokens import Blockchain, Mempool, Miningmanager, Wallet
        # initialize all core modules
        @run_in_reactor
        def blocksuccess(block):
            self.factory.publishBlock(block)
        self.blockchain = Blockchain()
        self.mempool = Mempool()
        self.wallet = Wallet(blockchain=self.blockchain)
        self.miningmanager = Miningmanager(self.mempool, self.blockchain, self.wallet, callback=blocksuccess)

        # init network
        from twisted.internet.endpoints import TCP4ServerEndpoint, TCP4ClientEndpoint
        from twisted.internet import reactor
        from .network.p2p import KCFactory, gotProtocol
        from random import randint
        # create server port to participate in network
        port = randint(27347, 55555)
        self.factory = KCFactory(port, self.blockchain, self.wallet, self.mempool, self.miningmanager, storage=self.storage)
        endpoint = TCP4ServerEndpoint(reactor, port)
        endpoint.listen(self.factory)
        # connect to bootstrap server as first connection
        point = TCP4ClientEndpoint(reactor, "134.60.77.158", 27346)
        d = point.connect(self.factory)
        d.addCallback(gotProtocol)

    @run_in_reactor
    def store(self, file, jstate):
        self.factory.store(file, jstate)

    @wait_for(timeout=30.0)
    def retrieve(self, fileid):
        d = self.factory.retrieve(fileid)
        return d

    @run_in_reactor
    def _transfermoney(self, tx):
        self.factory.publishTransaction(tx)

    def transfermoney(self, anonymitysize, address, amount, fees):
        self.wallet.rescan_blockchain()
        tx = self.wallet.gen_transfer_tx(anonymitysize, [address], [amount], fees)
        self._transfermoney(tx)

    def getbalance(self):
        self.wallet.rescan_blockchain()
        return self.wallet.get_balance()

    def getpublickey(self):
        return self.wallet.public_key

    def getchainlength(self):
        return self.blockchain.current_block.blockheight


class User():
    def __init__(self):
        self.role = Role()
        self.role.start()
        from nacl.public import PrivateKey
        self.key = PrivateKey.generate()

    def storefile(self, file):
        import time
        with open(file, "r") as f:
            data = f.read()
        log("File loaded.")
        #time.sleep(1)
        from .files.encryption import encrypt
        file = encrypt(data, self.key, [])#base64.b64encode().decode("utf-8")
        from koppercoin.crypto.AKKEffProofOfRetrievability import GQProofOfRetrievability as GQP
        log("File encrypted.")
        #time.sleep(1)
        #encode file for PoR, but how to decode?
        pub, sec = GQP.keygen()
        _ , tags, state = GQP.encode(sec, pub, file)
        log("File encoded.")
        #time.sleep(1)
        # secret key should be thrown away after this
        import json
        jtags = json.dumps([str(_) for _ in tags])
        jstate = json.dumps(state)
        file = json.dumps({"tags":jtags, "file":base64.b64encode(file).decode("utf-8")})
        log("Requesting storage of size "+str(len(file))+"B")
        log("Waiting for 5 seconds to receive some requests.")
        #time.sleep(1)
        self.role.store(file, jstate)
        #transaktion: public key, state
        #transmit: chunks + tags?

    def retrievefile(self, fileid):
        # get fileid from network
        from .files.encryption import decrypt
        data = self.role.retrieve(fileid)
        log("Retrieved: "+str(len(data))+"B.")
        # return data
        # print(str(data))
        data = base64.b64decode(data.encode("utf-8"))
        # print(str(data))
        import time
        time.sleep(1)
        log("Decrypted file.")
        data = decrypt(data, self.key)
        with open(fileid, "w") as f:
            f.write(data)
        time.sleep(1)
        log("File stored locally.")


class StorageProvider():
    def __init__(self):
        self.role = Role(storage=True)
        self.role.start()

    def listfiles(self):
        from koppercoin.files.store import listoffiles
        files = listoffiles()
        print("There are %d files stored:"%len(files))
        for filename in files:
            print(" -> %s"%filename)


class Miner(Role):
    def __init__(self):
        self.role = Role()
        self.role.start()

    def startmining(self):
        self.role.miningmanager.start_mining()

    def stopmining(self):
        self.role.miningmanager.stop_mining()
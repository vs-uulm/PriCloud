from .model import Block, Transaction, TxInput, TxOutput, OutputCondition
from .mempool import Mempool
# Tailimport of Wallet to prevent Circular import Problems
from .mining import Miningmanager
from collections import namedtuple

class Genesisblock(Block):
    def is_valid(self, *args,**kwargs):
        return True

genesisblock = Genesisblock(blockheight=0, prevhash='0000', target='0', nonce='0', transactions=[], timestamp='1488980649')


class Persistencemanager():
    def __init__(self):
        import sqlite3
        self.conn = sqlite3.connect("blockchain.db", check_same_thread=False)
        self.__create_tables()
        self.clear()

    def __create_tables(self):
        cursor = self.conn.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS blocks (height integer, hash text, content text)")
        self.conn.commit()

    def clear(self):
        self.newset = set()

    def save(self, block):
        self.newset.add(block)

    def load(self, blockchain):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM blocks ORDER BY height DESC LIMIT 1")
        try:
            height, hash, jsonblock = cursor.fetchone()
        except:
            return
        block = Block.from_json(jsonblock)
        blockchain.add_block(block)
        while block.prevhash != genesisblock.hash:
            cursor.execute("SELECT * FROM blocks WHERE hash = ?", (block.prevhash,))
            _, _, jsonblock = cursor.fetchone()
            block = Block.from_json(jsonblock)
            blockchain.add_block(block)

    def commit(self):
        cursor = self.conn.cursor()
        for block in self.newset:
            prepared = (block.blockheight, block.hash, block.json())
            cursor.execute("INSERT INTO blocks VALUES (?, ?, ?)", prepared)
        self.conn.commit()
        self.clear()


class Blockchain():
    Maxblock = namedtuple('Maxblock', 'blockheight hash')

    def __init__(self,*, persistence=Persistencemanager(), allowload=True):
        self.blocks = {}
        self.transactions = {}
        self.keyimages = {}
        self.outputs = {}
        self.blocks[genesisblock.hash] = genesisblock
        self.maxblock = Blockchain.Maxblock(blockheight=0, hash=genesisblock.hash)
        self.pm = persistence
        if allowload:
            self.pm.load(self)

    def add_block(self, block):
        if block.blockheight > self.maxblock.blockheight:
            self.maxblock = Blockchain.Maxblock(blockheight=block.blockheight, hash=block.hash)
            # TODO:
            # Manage forks?!
        for tx in block.transactions:
            self.add_transaction(tx)
        self.blocks[block.hash] = block
        self.pm.save(block)

    def add_transaction(self, tx):
        self.transactions[tx.hash] = tx
        try:
            for output in tx.outputs:
                self.outputs[output.hash] = output
            for keyimage in [_.keyimages for _ in tx.inputs]:
                self.keyimages[str(keyimage[0])] = tx
        except TypeError:
            # if we end up here, inputs are None
            pass

    def get_output_by_hash(self, hash):
        return self.outputs[hash]

    def get_transaction_by_hash(self, hash):
        return self.transactions[hash]

    def get_transaction_by_keyimage(self, keyimage):
        return self.keyimages[str(keyimage)]

    def get_block_by_hash(self, hash):
        if hash == genesisblock.prevhash:
            return genesisblock
        return self.blocks[hash]

    @property
    def current_block(self):
        return self.blocks[self.maxblock.hash]

    def resolve_previous_block(self, block):
        return self.get_block_by_hash(block.prevhash)

    def __iter__(self):
        def Chaingenerator(blockchain):
            current = blockchain.current_block
            while True:
                if current == genesisblock:
                    yield genesisblock
                    break
                yield current
                current = blockchain.resolve_previous_block(current)
        return Chaingenerator(self)

    def get_random_output_by_flavor_and_amnt(self, *args):
        # TODO
        # raise NotImplementedError("get random output by flavor and amnt missing. TODO")
        return []

from .wallet import Wallet
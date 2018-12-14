"""
This file implements a mempool. Informally speaking, a mempool is a
set of transactions which are not yet confirmed, i.e., included in the
blockchain.
Since the network and the mining threads access the same mempool this
class needs to be threadsafe.
"""

import multiprocessing
from koppercoin.tokens.model import *


class Persistencemanager():
    def __init__(self):
        import sqlite3
        self.conn = sqlite3.connect("mempool.db", check_same_thread=False)
        self.__create_tables()
        self.clear()

    def __create_tables(self):
        cursor = self.conn.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS transactions (hash text, content text)")
        self.conn.commit()

    def clear(self):
        self.newset = set()
        self.removeset = set()

    def save(self, tx):
        self.newset.add(tx)
        self.removeset.discard(tx)

    def remove(self, tx):
        self.removeset.add(tx)
        self.newset.discard(tx)

    def load(self, mempool):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM transactions")
        txs = cursor.fetchall()
        for hash, jsontx in txs:
            mempool.pool.add(Transaction.from_json(jsontx))

    def commit(self):
        cursor = self.conn.cursor()
        for tx in self.newset:
            prepared = (tx.hash, tx.json())
            cursor.execute("INSERT INTO transactions VALUES (?, ?)", prepared)
        for tx in self.removeset:
            cursor.execute("DELETE FROM transactions WHERE hash = ?", (tx.hash,))
        self.conn.commit()
        self.clear()


class Mempool:
    """This class implements a mempool. This is a pool containing some
    transactions. More transactions can be added or removed."""
    def __init__(self, *, persistencemanager=Persistencemanager(), allowload=True):
        self.pool = set([])
        self.pm = persistencemanager
        if allowload:
            self.pm.load(self)

    def add(self, tx):
        """add a transaction to the pool."""
        self.pool.add(tx)
        self.pm.save(tx)

    def add_many(self, txs):
        """add a transaction to the pool."""
        for tx in txs:
            self.pool.add(tx)

    def remove(self, tx):
        """remove a transaction from the pool."""
        self.pool.remove(tx)
        self.pm.remove(tx)

    def remove_many(self, txs):
        """remove a transaction from the pool."""
        for tx in txs:
            self.pool.remove(tx)

    def get_txs_with_max_fee(self, num):
        """returns the num transactions of the pool with the highest fees"""
        highest = [x for x in self.pool if x.fee >= max(tx.fee for tx in self.pool)]
        return highest[0:num]

#    def get_txs_with_max_fee_nonblck(self, num):
#        """
#        This is the nonblocking version of get_txs_with_max_fee. It
#        either returns get_txs_with_max_fee or None if no lock can be
#        acquired.
#        """
#        l = self.lock.acquire(False)
#        if l:
#            highest = [x for x in self.mempool if x.get_fee_amount() >= max(tx.get_fee_amount() for tx in self.mempool)]
#            self.lock.release()
#            return highest[0:num]
#        else:
#            return None

    def get_tx_with_max_fee(self):
        """returns the tx of the pool which has the highest fee"""
        return self.get_tx_with_max_fee(1)

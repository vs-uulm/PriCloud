
from multiprocessing import Event, Process, Queue, Pool
from threading import Thread
import datetime
import queue
import logging
import koppercoin.logsetup


class NoBlockFoundError(Exception):
    pass

def _setup(event):
    global finished
    finished = event

def _find_next_block(block, transactions, id, idrange):
    from koppercoin.tokens import Block
    possible_block = Block.from_prevblock(prevblock=block, transactions=transactions)
    while True:
        time = int(datetime.datetime.now().strftime("%s"))
        possible_block.timestamp = time - (time % idrange) + id
        # todo make start random
        for nonce in range(2**64-1):
            possible_block.nonce = nonce
            if int(possible_block.hash,16) < int(possible_block.target,16):
                return possible_block
            if finished.is_set():
                raise NoBlockFoundError()

class Miningmanager():

    def __init__(self, mempool, blockchain, wallet, callback=lambda x:None, num_threads=4):
        self.logger = logging.getLogger(__name__)
        self.mining_stoprequest = Event()
        self.num_threads = num_threads
        self.process = None
        self.mempool = mempool
        self.blockchain = blockchain
        self.wallet = wallet
        self.blockfound = callback
        self.txqueue = Queue()

    def start_mining(self):
        self.mining_stoprequest.clear()
        self.queue = Queue()
        self.txqueue = Queue()
        self.process = Process(target=self._mine,
                                args=(self.queue, self.txqueue, self.mempool, self.mining_stoprequest, self.blockchain, self.wallet, self.num_threads))
        self.consumer = Thread(target=self._consume)
        self.process.start()
        self.consumer.start()

    def add_transaction(self, tx):
        self.txqueue.put(tx)

    def stop_mining(self):
        self.mining_stoprequest.set()
        self.logger.debug("Attempting to close miningmanager.")
        while self.process.is_alive():
            self.process.join(1)
            self.consumer.join(1)
        self.logger.debug("Miningmanager closed succesfully.")

    def _consume(self):
        # process internal thread to consume created blocks: put it in blockchain and call blockfound
        while not self.mining_stoprequest.is_set() or not self.queue.empty():
            try:
                block = self.queue.get(timeout=5)
                if block.blockheight > self.blockchain.current_block.blockheight:
                    self.blockchain.add_block(block)
                    self.blockfound(block)
                    self.logger.debug("Block added to chain: "+str(block))
            except queue.Empty:
                pass

    def _mine(self, result_queue, tx_queue, mempool, stoprequest, blockchain, wallet, num_threads):
        """
        Mines blocks with a coinbase transaction and some transactions
        :param result_queue: A queue to which the fnal blocks are written
        :paramtype result_queue: multiprocessing.Queue
        :param mempool: A mempool whose transactions will be included
            in the block.
        :paramtype mempool: koppercoin.token.mempool.Mempool
        :param stoprequest: When set, the mining function will terminate
        :paramtype stoprequest: multiprocessing.Event
        """
        def consume_tx(tx_queue, mempool):
            while not self.mining_stoprequest.is_set() or not self.txqueue.empty():
                try:
                    tx = tx_queue.get(timeout=5)
                    mempool.add(tx)
                    self.logger.debug("TX added to mining mempool. "+str(tx))
                except queue.Empty:
                    pass

        def finished_callback(block):
            # callback for newly found block
            result_queue.put(block)
            blockchain.add_block(block)
            mempool.remove_many(transactions[:-1])
            self.logger.info("Block found: "+str(block))
            self.finished.set()

        self.logger.info("Setup mining using "+str(num_threads)+" processes.")
        consumer = Thread(target=consume_tx, args=(tx_queue, mempool))
        consumer.start()
        while not stoprequest.is_set():
            current_block = blockchain.current_block
            coinbase = wallet.gen_coinbase_tx(current_block.blockheight)
            self.logger.debug("Using as base: "+str(current_block.blockheight)+" -> "+str(current_block.hash))
            transactions = mempool.get_txs_with_max_fee(5)+[coinbase]

            self.finished = Event()
            self.finished.clear()

            with Pool(processes=num_threads, initializer=_setup, initargs=(self.finished,)) as pool:
                self.logger.debug("Pool setup.")
                for i in range(num_threads):
                    pool.apply_async(_find_next_block, (current_block, transactions, i, num_threads),
                                     callback=finished_callback)
                pool.close()
                self.logger.debug("Wait for mining.")
                self.finished.wait()
                self.logger.debug("Mininground finished.")
                pool.terminate()
            self.logger.debug("Pool terminated.")
        consumer.join(1)
        self.logger.info("Miningmanager stopped mining.")
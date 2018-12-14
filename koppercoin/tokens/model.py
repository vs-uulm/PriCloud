"""
This file implements raw data objects for the blockchain: Blocks, Transactions, Inputs/Outputs
"""
import hashlib
import datetime
import random
import json

from enum import IntEnum

from koppercoin.crypto import lww_signature
from koppercoin.tokens.parameters import *

def hash(obj):
    return hashlib.sha512(json.dumps(obj, sort_keys=True).encode('utf-8')).hexdigest()


class KCBase():
    __abstract__ = True

    def __str__(self):
        return self.json()

    def serialize(self):
        """
        Method to return a serializable version of the object that
        can be dumped to json or other serialization.
        """
        t = {}
        # only consider not-None values
        for k,v in self.__dict__.items():
            # call serialize if it exists
            t[k] = getattr(v,'serialize',lambda : v)()
            # descend one indirection
            try:
                t[k] = [_.serialize() for _ in t[k]]
            except Exception:
                pass
        return  t

    @classmethod
    def from_json(cls, json_str):
        return cls.from_dict(json.loads(json_str))

    @classmethod
    def from_dict(cls, dict):
        return cls(**dict)

    @property
    def hash(self):
        """Returns a unique hash of the object, based on its serialization."""
        return hash(self.json())

    def json(self):
        """
        A unique serialization of the Transaction.
        :returns: a json-serialization
        """
        return json.dumps(self.serialize(), sort_keys=True)



class Block(KCBase):
    """This class implements blocks.
    """

    def __init__(self, *, blockheight, prevhash, target, transactions, nonce = 0, timestamp = None):
        if timestamp is None:
            timestamp = int(datetime.datetime.now().strftime("%s"))
        self.blockheight = blockheight
        self.prevhash = prevhash
        self.nonce = nonce
        self.target = target
        self.transactions = transactions
        self.timestamp = timestamp

    def next_target(self):
        # TODO
        return '54778eff6ff5c0f03f521ece097d26d59d10c3eb2146bbc817df89f63c6bbe25d0826c36ddded059e859aa97732557a4717b504d691c6457290bcaa5a5db'

    @classmethod
    def from_prevblock(cls, prevblock, *, transactions, nonce = 0):
        return Block(blockheight = prevblock.blockheight+1, prevhash = prevblock.hash, target = prevblock.next_target(),
                     transactions = transactions,  nonce = nonce)

    def __repr__(self):
        return "%s(blockheight=%s, prevhash='%s', target='%s', nonce='%s', transactions=%s, timestamp='%s')" % \
               (self.__class__.__name__, self.blockheight, self.prevhash, self.target, self.nonce, self.transactions, self.timestamp)

    def is_valid(self, *, validate_transactions = True, blockchain):
        """Checks if a block is valid. If validate_transactions is
        set, the included transactions will also be checked.
        """
        # TODO: correct genesis block? need bockchain as an argument
        # TODO: does the block suffice the Pow-property?
        # TODO: is the timestamp neither "too high" nor "too low"
        # TODO: valid target, will need previous block or blockchain # to validate against
        valid_reward = mining_reward_per_blockheight(self.blockheight)
        coinbase_txs = [tx for tx in self.transactions if tx.is_coinbase]
        if len(coinbase_txs) > 1 or not all([tx.amount == valid_reward for tx in coinbase_txs]):
            return False
        # check if the amount of the coinbase (without fees) is set correctly
        if validate_transactions:
            keyimages = [_.keyimage for _ in [_.inputs for _ in self.transactions]]
            # the all part validates that all transactions are valid in context of the blockchain
            # the first part validates them relative to each other
            return (len(keyimages)==len(set(keyimages))) and all([_.is_valid(blockchain=blockchain) for _ in self.transactions])
        return True


    @classmethod
    def from_dict(cls, dict):
        return cls(blockheight=dict['blockheight'],
                   transactions=[Transaction.from_dict(_) for _ in dict['transactions']],
                   nonce=dict['nonce'],
                   prevhash=dict['prevhash'],
                   target=dict['target'],
                   timestamp=dict['timestamp'])


class Transaction(KCBase):
    """This class implements transactions of tokens between different
    participants.

    'coinbase' denotes a coinbase transaction. Its amount depends on
    the height in the blockchain plus the other fees included in the
    block. The signaturelist in the spending TxInput needs to contain
    a valid signature of the outputs with the corresponding publickey
    of the miner which has mined the block.
    """

    def __init__(self, *, inputs=None, outputs, por=None, pubkey, is_coinbase):
        self.inputs = inputs
        self.outputs = outputs
        self.por = por
        self.pubkey = pubkey
        self.is_coinbase = is_coinbase

    @classmethod
    def gen_coinbase(cls, output, pubkey):
        return Transaction(outputs=[output], pubkey=pubkey, is_coinbase=True)

    @classmethod
    def gen_regular(cls, inputs, outputs, pubkey):
        return Transaction(inputs=inputs, outputs=outputs, pubkey=pubkey, is_coinbase=False)

    @property
    def fee(self):
        if self.is_coinbase:
            return 0
        inputamount = sum([txin.amount for txin in self.inputs])
        outputamount = sum([txout.amount for txout in self.outputs])
        return inputamount - outputamount

    def is_coinbase(self):
        return self.is_coinbase

    def __repr__(self):
        return "%s(inputs=%s, outputs=%s,por='%s',pubkey'%s',is_coinbase=%s)" % \
               (self.__class__.__name__, str(self.inputs), str(self.outputs), self.por, self.pubkey, str(self.is_coinbase))

    def is_valid(self, *, blockchain):
        """Checks if a transaction is valid.
        """
        # The types have to be correct
        try:
            if not all(isinstance(txout, TxOutput) for txout in self.outputs):
                return False
            # The fees need to be positive or zero
            if self.fee < 0:
                return False
        except Exception:
            return False
        if not self.is_coinbase:
            # check the spend authorization (correct sig, or correct
            # multisig or correct contract) for non-coinbase transactions
            if not self.check_signatures(blockchain = blockchain):
                return False
            # check for Doublespend
            if self.is_doublespend(blockchain = blockchain):
                return False
        return True

    def is_doublespend(self, *, blockchain):
        for txinput in self.inputs:
            for keyimage in txinput.keyimages:
                try:
                    tx = blockchain.get_transaction_by_keyimage(keyimage)
                    # retrieve a tx with the same keyimage
                    # if it is the same as our transaction, it is no doublespend
                    if tx == self:
                        return False
                    # otherwise it is
                    else:
                        return True
                # if we do not find a tx with the same keyimage, it is
                # no doublespend
                except KeyError:
                    return False
        return True

    def check_signatures(self, *, blockchain):
        """
        Checks if the permissions to spend the referenced previous
        TxOuts (prevouts) in the TxInputs exists. I.e, this will check
        if the signatures in the TxInputs correspond to the TxOutputs.
        It is in the interest of the creator of the transaction that
        all referenced txouts have the same OutputCondition to have a big
        anonymity set.

        In the case of singlesig and multisig transactions, this will
        check the signatures.
        """
        for txinput in self.inputs:
            for ring_output in [blockchain.get_output_by_hash(h) for h in txinput.prevhashes]:
                # multiple previous outputs outs due to ringsig
                can_spend_this_output = False
                if ring_output.condition == OutputCondition.singlesig:
                    # Check if the signature is valid.
                    # first collect all the recipient pubkeys in the ring
                    previous_txos = [blockchain.get_output_by_hash(h) for h in txinput.prevhashes]
                    pubkeys = [output.recipientpubkeys[0] for output in previous_txos]
                    # get the message which should be signed
                    message = json.dumps([_.serialize() for _ in self.outputs], sort_keys=True)
                    # Get the signature
                    # We have a TxOutFlavor.transfer, so there is only one sig
                    signature = txinput.signatures[0]
                    # and check the sig
                    if lww_signature.verify(pubkeys, message, signature):
                        can_spend_this_output = True
                elif ring_output.condition == OutputCondition.contract:
                    raise NotImplementedError
                elif ring_output.condition == OutputCondition.multisig:
                    # Check if the signatures are valid.
                    # first collect the sigs
                    previous_txo = blockchain.get_output_by_hash(txinput.prevhashes[0])
                    # note: this is not a ringsig and cannot be made one, since there is no real anonymity set
                    # this also means we have only one previous txo
                    # (one prehash), so we take the first one
                    # we copy the pubkeys and the signatures, since these can be in a
                    # different order, so we need to iterate and
                    # remove the pubkey
                    pubkeys = list(previous_txo.recipientpubkeys)
                    # get the message which should be signed
                    message = json.dumps([_.serialize() for _ in self.outputs], sort_keys=True)
                    # get the signatures
                    signatures = list(txinput.signatures)
                    for pk in list(pubkeys):
                        for sig in list(signatures):
                            if lww_signature.verify([pk], message, sig):
                                # we have found the corresponding signature and can delete it
                                pubkeys.remove(pk)
                                signatures.remove(sig)
                    if len(pubkeys) == 0 and len(signatures) == 0:
                        can_spend_this_output = True
                if can_spend_this_output == False:
                    # At least on of the referenced txouts per txin need to be spendable
                    return False
        return True

    @classmethod
    def from_dict(cls, dict):
        if dict['inputs'] is not None:
            inputs = [TxInput.from_dict(_) for _ in dict['inputs']]
        else:
            inputs = None
        if dict['outputs'] is not None:
            outputs = [TxOutput.from_dict(_) for _ in dict['outputs']]
        else:
            outputs = None
        return cls(inputs=inputs, outputs=outputs, is_coinbase=dict['is_coinbase'], pubkey=dict['pubkey'])


class TxInput(KCBase):
    """This class implements inputs of transactions.
    """

    def __init__(self, *, prevhashes, signatures, amount):
        self.prevhashes = prevhashes
        self.signatures = signatures
        self.amount = amount

    @classmethod
    def from_prevouts(cls, prevouts, *, signatures):
        prevouthashes = [o.hash for o in prevouts]
        assert all(_.amount == prevouts[0].amount for _ in prevouts)
        amount = prevouts[0].amount
        return TxInput(prevhashes=prevouthashes, signatures=signatures, amount=amount)

    def __repr__(self):
        return "%s(prevhashes=%s, signatures=%s, amount=%s)" % \
               (self.__class__.__name__, self.prevhashes, self.signatures, self.amount)

    @property
    def keyimages(self):
        return [sig[0] for sig in self.signatures]


class TxOutput(KCBase):
    """This class implements outputs of transactions.
    """

    def __init__(self, *, recipientpubkeys, amount, nonce=None, condition):
        self.amount = amount
        self.condition = condition
        if nonce is None:
            nonce = random.SystemRandom().randint(0, (2**63)-1)
        self.nonce = nonce
        self.recipientpubkeys = recipientpubkeys

    def __repr__(self):
        return "%s(recipientpubkeys=%s, amount=%s, nonce=%s, condition=%s)" % \
               (self.__class__.__name__, self.recipientpubkeys, self.amount, self.nonce, self.condition)



class OutputCondition(IntEnum):
    """The 'type' of the TxOutput.
    """

    singlesig = 1
    multisig = 2
    contract = 3

    def __repr__(self):
        return "%s.%s" % (self.__class__.__name__, self.name)

    def __str__(self):
        return str(self.value)
        #return self.__repr__()

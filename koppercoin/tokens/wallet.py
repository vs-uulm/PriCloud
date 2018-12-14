"""This class implements the wallet.
"""

from koppercoin.crypto import onetime_keys, lww_signature
from koppercoin.tokens import parameters
from koppercoin.tokens import *
from koppercoin.config import save_path
import logging
import koppercoin.logsetup
import json
import binascii
import os
import random


class Wallet():
    # Filetype for wallet
    _filetype = ".pkl"

    class NotFoundError(Exception):
        pass

    class NotEnoughMoneyError(ValueError):
        pass

    class NotEnoughTxOutsError(ValueError):
        pass

    def __init__(self, *,force_new=False, persist=True, blockchain):
        """Creates a wallet. In particular, it tries to load an
        already existing wallet and if none is found creates a new
        one.

        >>> wal = Wallet(force_new=True, persist=False, blockchain=Blockchain())
        >>> wal_ = Wallet(force_new=True, persist=False, blockchain=Blockchain())

        >>> wal_.keypair == wal.keypair
        False

        >>> wal_.trackingkey == wal.trackingkey
        False

        >>> wal_.public_key == wal.public_key
        False

        >>> wal_ == wal
        False
        """
        try:
            # check if we already have a wallet
            if force_new:
                raise Wallet.NotFoundError
            wallet = Wallet._retrieve()
            self.keypair = wallet['keypair']
            self.public_key = wallet['public_key']
            self.trackingkey = wallet['trackingkey']
        except Wallet.NotFoundError:
            # If we have no wallet
            # generate a new one and save it
            self.keypair = onetime_keys.keygen()
            self.public_key = self.keypair[1]
            self.trackingkey = onetime_keys.key_to_trackingkey(self.keypair)
            if persist:
                self._persist()
        # internal cache
        self.txos = set()
        self.unspent_txos = set()
        self.shared_txos = set()
        self.unspent_shared_txos = set()
        self.scan = blockchain.current_block.timestamp
        self.blockchain = blockchain
        self.logger = logging.getLogger(__name__)

    def _persist(self):
        """
        Writes the provided wallet to disk.
        TODO
        Parameter for overwirte
        Check if wallet is a wallet
        """
        # TODO REWORK totally unclear
        # remove blockchain and None entrys
        from koppercoin.tokens import Blockchain
        t = {k: v for k, v in self.__dict__.items() if v and not type(v) == Blockchain}
        with open(os.path.join(save_path, str("wallet") + Wallet._filetype), 'w') as output:
            output.write(json.dumps(t))

    @classmethod
    def _retrieve(cls):
        """
        Trys to find a wallet file on disk and load the wallet from there.
        Throws an WalletNotFoundError error when there is no wallet file.

        :return:
            A wallet in dictionary form.
        """
        # TODO REWORK
        try:
            with open(os.path.join(save_path, str("wallet") + Wallet._filetype), 'r') as inp:
                return json.loads(inp.read())
        except:
            raise Wallet.NotFoundError

    def _scan_is_current(self):
        return self.scan == self.blockchain.current_block.timestamp

    def rescan_blockchain(self):
        # check the blockchain over spend tx, own tx, ... and update database
        # TODO: implement this if "update database" is more clearly defined
        # may provide some additional fields in the db which show if the txout
        # belongs to us
        self.scan = self.blockchain.current_block.timestamp
        self.txos.clear()
        self.unspent_txos.clear()
        for block in self.blockchain:
            for tx in block.transactions:
                # check for own transactions
                (txouts, pk) = self.get_own_txouts_and_tx_pubkey_from_tx(tx)
                if txouts != []:
                    for txout in txouts:
                        self.txos.add(txout)
                        sec_key = self.get_txout_privkey(txout, pk)
                        # compute the keyimage and check if it occurs in an
                        # earlier TxInput
                        # if not, then it is unspent
                        keyimage = lww_signature.keyimage(sec_key)
                        keyimage = binascii.hexlify(keyimage).decode()
                        try:
                            self.blockchain.get_transaction_by_keyimage(keyimage)
                        except KeyError:
                            self.unspent_txos.add(txout)
                # check for shared transactions
                (txouts, pk) = self.get_shared_txouts_and_tx_pubkey_from_tx(tx)
                if txouts != []:
                    for txout in txouts:
                        self.shared_txos.add(txout)
                        sec_key = self.get_txout_privkey(txout, pk)
                        # compute the keyimage and check if it occurs in an
                        # earlier TxInput
                        # if not, then it is unspent
                        keyimage = lww_signature.keyimage(sec_key)
                        keyimage = binascii.hexlify(keyimage).decode()
                        try:
                            self.blockchain.get_transaction_by_keyimage(keyimage)
                        except KeyError:
                            self.unspent_shared_txos.add(txout)
        # TODO maybe persist changes

    # TODO temporary, remove GET methods someday
    # TODO Also: Fix
    def get_own_utxos(self):
        """
        returns a list of unspent transactions which belong to the wallet.
        """
        if not self._scan_is_current():
            self.rescan_blockchain()
        return list(self.unspent_txos)

    def get_shared_utxos(self):
        """
        returns a list of unspent transactions which are shared
        between the wallet and some other address.
        """
        if not self._scan_is_current():
            self.rescan_blockchain()
        return list(self.unspent_shared_txos)

    def get_own_txos(self):
        """
        returns a list of unspent transactions which belong to the wallet.
        """
        if not self._scan_is_current():
            self.rescan_blockchain()
        return list(self.txos)

    def get_shared_txos(self):
        """
        returns a list of unspent transactions which are shared
        between the wallet and some other address.
        """
        if not self._scan_is_current():
            self.rescan_blockchain()
        return list(self.shared_txos)

    def get_own_txouts_and_tx_pubkeys(self):
        """
        returns a list of pairs of TxOutputs and transaction public keys [(txo1,
        pk1),..,(txon, pkn)] which belong to the wallet.
        These may have been spent.
        """
        own_txos = []
        # TODO: if we can mark tx as belonging to us in the db this will be faster
        for block in self.blockchain:
            for tx in block.transactions:
                (txouts, pk) = self.get_own_txouts_and_tx_pubkey_from_tx(tx)
                if txouts != []:
                    own_txos += [(txout, pk) for txout in txouts]
        return own_txos

    def get_shared_txouts_and_tx_pubkeys(self):
        """
        returns a list of pairs of TxOutputs and transaction public keys [(txo1,
        pk1),..,(txon, pkn)] which are multisig transaction outputs
        belonging to the wallet.
        These may have been spent.
        """
        shared_txos = []
        # TODO: if we can mark tx as belonging to us in the db this will be faster
        for block in self.blockchain:
            for tx in block.transactions:
                (txouts, pk) = self.get_shared_txouts_and_tx_pubkey_from_tx(tx)
                if txouts != []:
                    shared_txos += [(txout, pk) for txout in txouts]
        return shared_txos

    def get_balance(self):
        """
        returns the current balance of the account.
        """
        balance = 0
        for own_utxo in self.get_own_utxos():
            balance += own_utxo.amount
        return balance

    @staticmethod
    def _convert_to_std_amounts(value):
        """
        There are standard amounts in transactions to increase the
        size of the anonymity set for the ring signatures.
        These are powers of two.
        This functions takes a value as input and splits it into a
        list of standard amounts.
        :param value: the value which should be split
        :type value: Int
        :returns: A list of standard amounts whose sum is equal to
            value
        :raises ValueError: if the input is smaller or equal than zero

        >>> Wallet._convert_to_std_amounts(5)
        [4, 1]

        >>> Wallet._convert_to_std_amounts(255)
        [128, 64, 32, 16, 8, 4, 2, 1]

        >>> Wallet._convert_to_std_amounts(-2)
        Traceback (most recent call last):
         ...
        ValueError: Value needs to be >0
        """
        result=[]
        if value <= 0:
            raise ValueError("Value needs to be >0")
        rem = value
        while rem > 0:
            max_pow_of_two_dividing_rem = rem.bit_length()+7//8 -1
            result.append(2**max_pow_of_two_dividing_rem)
            rem -= 2**max_pow_of_two_dividing_rem
        assert(sum(result)==value)
        return result


    def gen_transfer_tx(self, anon_size, addresses, amounts, fee):
        """generates a tx which transfers money [amount1,...,amountn]
        to addresses, i.e., public keys [addr1, .., addrn]. The size
        of the anonymity set is anon_size.

        :param anon_size: the size of the anonymity set. 1 means no
            anonymity
        :type anon_size: int
        :param addresses: a list of public keys
        :param amounts: a list of amounts. The i-th amount is sent to
            the i-th address.
        :param fee: the fee included in the transaction.
        :type fee: int
        :returns: a transaction
        :raises Wallet.NotEnoughMoneyError: If there is not enough money
            found to generate the transaction.
        :raises Wallet.NotEnoughTxOutsError: If there are not enough
            TxOutputs found which can be used in the anonymity set.
        """
        #######################################
        # Retrieve the outputs we will spend #
        #######################################
        # Retrieve own txouts, such that their cumulative amount is >=
        # the cumulative amount of the receivers.
        # These will be referenced in the TxInputs
        if self.get_balance() < sum(amounts)+fee:
            print(self.get_balance())
            raise Wallet.NotEnoughMoneyError("Not enough funds!")
        own_txos_and_pubks = self.get_own_txouts_and_tx_pubkeys()
        random.SystemRandom().shuffle(own_txos_and_pubks)
        txos_and_pks_to_be_used = []
        input_amount = 0
        for (own_txo, tx_pk) in own_txos_and_pubks:
            while input_amount < sum(amounts)+fee:
                txos_and_pks_to_be_used.append((own_txo, tx_pk))
                input_amount += own_txo.amount
        change_amount = input_amount - sum(amounts) - fee
        #####################
        # Build the outputs #
        #####################
        txoutputs = []
        # Compute the outputs for the receivers
        keynonce = os.urandom(32) # a nonce for generating the OTPubkeys
        for addr, amnt in zip(addresses, amounts):
            for stdamnt in Wallet._convert_to_std_amounts(amnt):
                (recipient_ot_pk, tx_pk) = onetime_keys.generate_ot_key(addr, keynonce)
                # the tx_pk are all the same, since we use the same keynonce
                recipientpubkey=recipient_ot_pk
                txoutputs.append(TxOutput(amount=stdamnt,
                    condition=OutputCondition.singlesig, recipientpubkeys=[recipientpubkey]))
        # Compute the change outputs which are left and go back to the sender
        if change_amount != 0:
            for stdamnt in Wallet._convert_to_std_amounts(change_amount):
                (recipient_ot_pk, tx_pk) = onetime_keys.generate_ot_key(self.public_key, keynonce)
                # the tx_pk are all the same, since we use the same keynonce
                recipientpubkey=recipient_ot_pk
                txoutputs.append(TxOutput(amount=stdamnt, condition=OutputCondition.singlesig, recipientpubkeys=[recipientpubkey]))
        # shuffle outputs, such that change is indistinguishable
        random.SystemRandom().shuffle(txoutputs)
        ####################
        # Build the inputs #
        ####################
        message_to_sign = json.dumps([_.serialize() for _ in txoutputs], sort_keys = True)
        txinputs = []
        # For each of our txout, find anon_size-1 other txouts, to
        # build the anonymity set referenced in txinput.prevouts
        for (txo, tx_pubkey) in txos_and_pks_to_be_used:
            try:
                anon_txouts = self.blockchain.get_random_output_by_flavor_and_amnt(OutputCondition.singlesig, txo.amount, anon_size-1)
            except ValueError:
                raise Wallet.NotEnoughTxOutsError("""There are not enough TxOutputs
                    found which can be used in the anonymity set.
                    Maybe you want to try decreasing the size of the
                    anonymity set.""")
            # permute the arrays to make our real txo
            # indistinguishable from the others
            refd_txos = anon_txouts + [txo]
            random.SystemRandom().shuffle(refd_txos)
            # sign it correctly
            txout_privkey = self.get_txout_privkey(txo, tx_pubkey)
            ot_rec_ring_keys = [t.recipientpubkeys[0] for t in refd_txos]
            signature = lww_signature.ringsign(ot_rec_ring_keys, txout_privkey, message_to_sign)
            txinputs.append(TxInput.from_prevouts(prevouts=refd_txos, signatures=[signature]))
        ##########################################
        # Build the Tx, given inputs and outputs #
        ##########################################
        (_, tx_pk) = onetime_keys.generate_ot_key(addresses[0], keynonce)
        # it does not matter which address we take, since it should be
        # the same result
        tx = Transaction.gen_regular(inputs=txinputs, outputs=txoutputs, pubkey=tx_pk)
        return tx

    def gen_coinbase_tx(self, blockheight):
        """generates a coinbase transaction, i.e., a transaction for
        earning the mining reward.

        >>> wal = Wallet(force_new=True, persist=False, blockchain=Blockchain())
        >>> tx = wal.gen_coinbase_tx(2)
        >>> tx.is_coinbase
        True
        """
        # set the amount (without the fees)
        amount = parameters.mining_reward_per_blockheight(blockheight)
        # set the recipient
        (onetime_key, tx_pubkey) = onetime_keys.generate_ot_key(self.public_key)
        coinbase_output = TxOutput(amount=amount, condition=OutputCondition.singlesig, recipientpubkeys=[onetime_key])
        coinbase_tx = Transaction.gen_coinbase(output=coinbase_output,pubkey=tx_pubkey)
        return coinbase_tx

    def get_own_txouts_and_tx_pubkey_from_tx(self, tx):
        """returns the transaction outputs of the transaction which
        are owned solely by us, together with the tx_pubkey. I.e.
        ([txout1,..., txoutn], tx_pubkey). This is the information
        required to recover the private key of each txout. If none of
        the txouts are owned by us, we return ([], tx_pubkey).

        >>> wal = Wallet(force_new=True, persist=False, blockchain=Blockchain())
        >>> tx = wal.gen_coinbase_tx(2)
        >>> type(wal.get_own_txouts_and_tx_pubkey_from_tx(tx))
        <class 'tuple'>
        """
        tx_pubkey = tx.pubkey
        # the Tx public key, basically the DH-term
        own_txouts = []
        for txout in tx.outputs:
            # check that this is a singlesig-tx
            if txout.condition == OutputCondition.singlesig:
                ot_pub_keys = txout.recipientpubkeys
                # the onetime public key of the recipient
                ot_key = (ot_pub_keys[0], tx_pubkey)
                txout_recoverable = onetime_keys.recoverable(ot_key, self.trackingkey)
                if txout_recoverable:
                    own_txouts.append(txout)
        return (own_txouts, tx_pubkey)

    def get_shared_txouts_and_tx_pubkey_from_tx(self, tx):
        """returns the multisig transaction outputs of the transaction which
        are shared between us and someone else, together with the tx_pubkey. I.e.
        ([txout1,..., txoutn], tx_pubkey). This is the information
        required to recover the private key of each txout. If none of
        the txouts are owned by us, we return ([], tx_pubkey).
        """
        tx_pubkey = tx.pubkey
        # the Tx public key, basically the DH-term
        shared_txouts = []
        for txout in tx.outputs:
            # only continue with multisig tx
            if txout.condition == OutputCondition.multisig:
                for ot_pub_key in txout.recipientpubkeys:
                    # the onetime public key of the recipient
                    ot_key = (ot_pub_key, tx_pubkey)
                    txout_recoverable = onetime_keys.recoverable(ot_key, self.trackingkey)
                    # check if we can recover one of the privkeys, i.e., if we
                    # are one of the recipients
                    if txout_recoverable:
                        shared_txouts.append(txout)
        return (shared_txouts, tx_pubkey)
        # if we have a multisig tx where multiple of the receivers are
        # ourself, this will occur multiple times in the output.

    def get_txout_privkey(self, txout, tx_pubkey):
        """takes a transaction output txout, together with the public
        key of the transaction containing txout and recovers the
        private key of the transaction which is needed to spend the
        transaction.

        Note that in the case of a multisig-transaction there may be
        more keys needed.
        """
        if txout.condition == OutputCondition.singlesig:
            # the onetime public key
            ot_pub_key = txout.recipientpubkeys[0]
            ot_key = (ot_pub_key, tx_pubkey)
            return onetime_keys.recover_sec_key(ot_key, self.keypair)
        elif txout.condition == OutputCondition.multisig:
            for ot_pub_key in txout.recipientpubkeys:
                ot_key = (ot_pub_key, tx_pubkey)
                if onetime_keys.recoverable(ot_key, self.trackingkey):
                    return onetime_keys.recover_sec_key(ot_key, self.keypair)
        elif txout.condition == OutputCondition.contract:
            raise NotImplementedError

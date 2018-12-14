import unittest
# Set test environment flag
import koppercoin.config
koppercoin.config.test = True

from koppercoin.tokens import *
from koppercoin.tokens.wallet import *
from koppercoin.crypto import onetime_keys, lww_signature
import json

class Mockpersistence():
    def __init__(self):
        pass

    def clear(self):
        pass

    def save(self, object):
        pass

    def commit(self):
        pass

    def load(self, entity):
        pass


def find_next_block_noabrt(block, transactions):
    """
    This function mines a next block. This function cannot be
    aborted until it has found a new block.
    :param block: the currecnt block
    :param transactions: transactions that are to be included in
        the newly created block.
    :type transactions: list
    :returns: a next block
    """
    # Compute as much stuff in advance as we can
    hash_of_possible_block = '0'
    possible_block = Block.from_prevblock(prevblock=block, transactions=transactions)
    # try nonces until we have found a valid block
    while int(possible_block.hash, 16) <= int(block.target, 16):
        possible_block.nonce = str(random.getrandbits(64))
        # gethash returns hex encoded string
    # Now we know that possible_block is a valid next block
    return possible_block


class TestCoinbaseTransactions(unittest.TestCase):
    def setUp(self):
        # get a wallet
        self.bc = Blockchain(persistence=Mockpersistence())
        self.wal = Wallet(persist=False, force_new=True, blockchain=self.bc)
        # create a coinbase_tx
        self.coinbase_tx = self.wal.gen_coinbase_tx(2)

    def test_gen_coinbase(self):
        """
        test if the result of gen_coinbase is a coinbase transaction
        """
        self.assertEquals(self.coinbase_tx.is_coinbase, True)

    def test_valid_coinbase(self):
        """
        test if the result of gen_coinbase is a valid transaction
        """
        self.assertEquals(self.coinbase_tx.is_valid(blockchain=self.bc), True)

    def test_own_coinbase_spendable(self):
        """
        test if we can spend our own coinbase transactions
        """
        # get the spendable txouts from the coinbase_tx and remove the tx_pubkey
        spendable_txouts = self.wal.get_own_txouts_and_tx_pubkey_from_tx(self.coinbase_tx)[0]
        self.assertEquals(spendable_txouts, [self.coinbase_tx.outputs[0]])

    def test_coinbase_fee_amount(self):
        """
        test if fee of a coinbase transaction is 0
        """
        self.assertEquals(self.coinbase_tx.fee, 0)


class TestBlocks(unittest.TestCase):
    def setUp(self):
        self.sndblock = find_next_block_noabrt(genesisblock, [])
        self.bc=Blockchain(persistence=Mockpersistence())
        self.bc.add_block(self.sndblock)

    def test_valid(self):
        """
        test the validity of created blocks
        """
        self.assertEquals(genesisblock.is_valid(blockchain=self.bc), True)
        self.assertEquals(self.sndblock.is_valid(validate_transactions=False, blockchain = self.bc), True)
        self.assertEquals(self.sndblock.is_valid(validate_transactions=True, blockchain = self.bc), True)


class TestTransferTransactions(unittest.TestCase):
    def setUp(self):
        # get a wallet
        self.bc = Blockchain(persistence=Mockpersistence())
        self.wal = Wallet(persist=False, force_new=True, blockchain=self.bc)
        # create a coinbase_tx
        self.coinbase_tx = self.wal.gen_coinbase_tx(2)
        # We put this tx in the next block
        fstblock = find_next_block_noabrt(genesisblock, [self.coinbase_tx])
        # Create a new transaction and really spend the coinbase
        # We split the funds in two TxOutputs, so we need one txin
        # referencing the coinbase
        # and two txouts
        # We begin with the txouts
        # self.coinbase_tx.outputs[0].amount//2-1
        # Note that the fee is therefore 2
        # We ourself are the recipients
        recipientpubkeys_with_tx_key = onetime_keys.generate_ot_keys([self.wal.public_key, self.wal.public_key])
        recipientpubkeys = recipientpubkeys_with_tx_key[0]

        txouts = [TxOutput(amount=self.coinbase_tx.outputs[0].amount//2-1, recipientpubkeys=[recipientpubkeys[i]],
                    condition=OutputCondition.singlesig) for i in range(2)]
        # Now to the txinput
        # First we need the tx_pubkey of the coinbase
        (spendable_txouts, tx_pubkey) = self.wal.get_own_txouts_and_tx_pubkey_from_tx(self.coinbase_tx)
        # Then we recover the txout_privkey which we need to sign
        txout_privkey = self.wal.get_txout_privkey(spendable_txouts[0], tx_pubkey)
        # create the signature which shows that we are authorized to spend the
        # coinbase.
        message_to_sign = json.dumps([_.serialize() for _ in txouts], sort_keys = True)
        # The ringsize is 0, since we do not have other transactions
        # We sign with the recipientkey included in the
        # coinbase_tx
        ot_rec_key = self.coinbase_tx.outputs[0].recipientpubkeys[0]
        signature = lww_signature.ringsign([ot_rec_key],
            txout_privkey, message_to_sign)
        self.txin = TxInput.from_prevouts(prevouts=[self.coinbase_tx.outputs[0]], signatures=[signature])
        self.tx = Transaction.gen_regular(inputs=[self.txin], outputs=txouts, pubkey=recipientpubkeys_with_tx_key[1])
        # Now tx is the new transaction we wanted to create
        # We save it as an attribute so we can use it in further tests
        # after creating the new tx, we store it in the next block
        sndblock = find_next_block_noabrt(fstblock, [self.tx])
        self.bc.add_block(fstblock)
        self.bc.add_block(sndblock)

    def tearDown(self):
        pass

    def test_valid_tx(self):
        """
        test if we can detect valid transactions
        """
        self.assertEquals(self.tx.is_valid(blockchain = self.bc), True)

    def test_doublespend_detection(self):
        """
        test if doublespends are considered invalid
        """
        # We try to spend the coinbase again
        recipientpubkey_with_tx_key = onetime_keys.generate_ot_keys([self.wal.public_key])
        recipientpubkey = recipientpubkey_with_tx_key[0]

        doublespend_txout = TxOutput(amount=4, recipientpubkeys=[recipientpubkey], condition=OutputCondition.singlesig)
        # Now to the txinput
        # First we need the tx_pubkey of the coinbase
        (spendable_txouts, tx_pubkey) = self.wal.get_own_txouts_and_tx_pubkey_from_tx(self.coinbase_tx)
        # Then we recover the txout_privkey which we need to sign
        txout_privkey = self.wal.get_txout_privkey(spendable_txouts[0], tx_pubkey)
        # create the signature which shows that we are authorized to spend the
        # coinbase.
        message_to_sign = json.dumps([doublespend_txout.serialize()], sort_keys = True)
        # The ringsize is 0, since we do not have other transactions
        # We sign with the recipientkey included in the
        # coinbase_tx
        ot_rec_key = self.coinbase_tx.outputs[0].recipientpubkeys[0]
        signature = lww_signature.ringsign([ot_rec_key],
            txout_privkey, message_to_sign)
        doublespend_txin = TxInput.from_prevouts(prevouts=[self.coinbase_tx.outputs[0]], signatures=[signature])
        doublespend_tx = Transaction.gen_regular(inputs=[doublespend_txin], outputs=[doublespend_txout], pubkey=recipientpubkey_with_tx_key[1])
        print(doublespend_txin.keyimages[0])
        print(self.txin.keyimages[0])
        self.bc.get_transaction_by_keyimage(self.txin.keyimages[0])

        self.assertEquals(doublespend_tx.is_doublespend(blockchain = self.bc), True)
        self.assertEquals(doublespend_tx.is_valid(blockchain = self.bc), False)

    def test_non_coinbase_tx_spendable(self):
        """
        test if we can spend our new funds
        """
        spendable_txouts = self.wal.get_own_txouts_and_tx_pubkey_from_tx(self.tx)[0]
        self.assertEquals(spendable_txouts, self.tx.outputs)

    def test_get_own_txouts_and_tx_pubkeys(self):
        """
        test get_own_txouts_and_tx_pubkeys from the wallet
        """
        self.assertEquals(len(self.wal.get_own_txouts_and_tx_pubkeys()), 3)

    def test_amount(self):
        """
        test if we can compute the correct amount of a regular TxOutput
        """
        self.assertEquals(self.tx.outputs[0].amount, 549755813887)

    def test_amount_coinbase(self):
        """
        test if we can compute the correct amount of a coinbase TxOutput
        """
        self.assertEquals(self.coinbase_tx.outputs[0].amount, 1099511627776)
        # the reward from mining plus the included fees

    def test_fee_property(self):
        """
        test if we can compute the correct fee_amount of a regular tx
        """
        self.assertEquals(self.tx.fee, 2)

    def test_serialize_deserialize_identical(self):
        """
        test if t and deserialize(serialize(t)) are IDENTICAL (not same object!)
        """
        self.assertEquals(Transaction.from_json(self.tx.json()).hash, self.tx.hash)


class TestMultisigTransactions(unittest.TestCase):
    def setUp(self):
        # make two wallets
        self.bc = Blockchain(persistence=Mockpersistence())
        self.wal1 = Wallet(persist=False, force_new=True, blockchain=self.bc)
        self.wal2 = Wallet(persist=False, force_new=True, blockchain=self.bc)
        # create a coinbase_tx
        self.coinbase_tx = self.wal1.gen_coinbase_tx(2)
        # We build a multisig transaction which can only be spent by wal1 and
        # wal2 cooperatively
        # First we build the output
        recipientpubkeys_with_tx_key = onetime_keys.generate_ot_keys([self.wal1.public_key, self.wal2.public_key])
        recipientpubkeys = recipientpubkeys_with_tx_key[0]
        txout = TxOutput(amount=self.coinbase_tx.outputs[0].amount-2,
                    condition=OutputCondition.multisig,
                    recipientpubkeys=recipientpubkeys)
        # Now we build the input
        # First we need the tx_pubkey of the coinbase
        (spendable_txouts, tx_pubkey) = self.wal1.get_own_txouts_and_tx_pubkey_from_tx(self.coinbase_tx)
        # Then we recover the txout_privkey which we need to sign
        txout_privkey = self.wal1.get_txout_privkey(spendable_txouts[0], tx_pubkey)
        # create the signature which shows that we are authorized to spend the
        # coinbase.
        message_to_sign = json.dumps([txout.serialize()], sort_keys = True)
        # The ringsize is 0, since we do not have other transactions
        # We sign with the recipientkey included in the
        # coinbase_tx
        ot_rec_key = self.coinbase_tx.outputs[0].recipientpubkeys[0]
        signature = lww_signature.ringsign([ot_rec_key],
            txout_privkey, message_to_sign)
        txin = TxInput.from_prevouts(prevouts=[self.coinbase_tx.outputs[0]], signatures=[signature])
        # Now we build the multisig transaction together
        self.multisig_tx = Transaction.gen_regular(inputs=[txin], outputs=[txout], pubkey=recipientpubkeys_with_tx_key[1])
        # Now we have a coinbase which is spent in a transaction with a
        # multisig-output and fees of 2

        # Next, we spend the multisig-tx to wal3
        self.wal3 = Wallet(persist=False, force_new=True, blockchain=self.bc)
        # First we build the output
        recipientpubkey_with_tx_key = onetime_keys.generate_ot_key(self.wal3.public_key)
        recipientpubkey = recipientpubkey_with_tx_key[0]
        txout = TxOutput(amount=self.multisig_tx.outputs[0].amount-2,
                    condition=OutputCondition.singlesig,
                    recipientpubkeys=[recipientpubkey])
        # Then we build the input
        # First we need the tx_pubkey of the multisig_tx
        (spendable_txouts, tx_pubkey) = self.wal1.get_shared_txouts_and_tx_pubkey_from_tx(self.multisig_tx)
        # Then we recover the txout_privkey which we need to sign
        txout_privkey1 = self.wal1.get_txout_privkey(spendable_txouts[0], tx_pubkey)
        message_to_sign = json.dumps([txout.serialize()], sort_keys = True)
        # The ringsize is 0, since we do not have other transactions
        ot_rec_key = self.multisig_tx.outputs[0].recipientpubkeys[0]
        signature1 = lww_signature.ringsign([ot_rec_key],
            txout_privkey1, message_to_sign)
        # And the same for wallet2
        txout_privkey2 = self.wal2.get_txout_privkey(spendable_txouts[0], tx_pubkey)
        ot_rec_key = self.multisig_tx.outputs[0].recipientpubkeys[1]
        signature2 = lww_signature.ringsign([ot_rec_key],
            txout_privkey2, message_to_sign)
        txin = TxInput.from_prevouts(prevouts=[self.multisig_tx.outputs[0]],
                signatures=[signature2, signature1])
        # Note, how I have switched the signatures
        # Now we build the multisig spend transaction together
        self.multisigspend_tx = Transaction.gen_regular(inputs=[txin], outputs=[txout], pubkey=recipientpubkey_with_tx_key[1])

        # Put all the transactions in blocks
        fstblock = find_next_block_noabrt(genesisblock, [self.coinbase_tx])
        sndblock = find_next_block_noabrt(fstblock, [self.multisig_tx])
        trdblock = find_next_block_noabrt(sndblock, [self.multisigspend_tx])
        self.bc.add_block(fstblock)
        self.bc.add_block(sndblock)
        self.bc.add_block(trdblock)

    def tearDown(self):
        pass

    def test_valid_tx(self):
        """
        test if the transaction with the multisig output is valid
        """
        self.assertEquals(self.multisig_tx.is_valid(blockchain=self.bc), True)
        self.assertEquals(self.multisigspend_tx.is_valid(blockchain=self.bc), True)

    def test_wallet_get_balance(self):
        """
        test if we can compute balance received from a multisig-tx
        """
        self.assertEquals(len(self.wal3.get_own_txouts_and_tx_pubkey_from_tx(self.multisigspend_tx)), 2)
        self.assertEquals(self.wal3.get_balance(), 1099511627772)

    def test_get_shared_txouts_and_tx_pubkeys(self):
        """
        test get_shared_txouts_and_tx_pubkeys from the wallet
        """
        self.assertEquals(len(self.wal1.get_shared_txouts_and_tx_pubkeys()), 1)
        self.assertEquals(len(self.wal2.get_shared_txouts_and_tx_pubkeys()), 1)
        self.assertEquals(len(self.wal3.get_shared_txouts_and_tx_pubkeys()), 0)

    def test_get_shared_txos(self):
        """
        test get_shared_txos from the wallet
        """
        self.assertEquals(self.wal1.get_shared_txos(), self.multisig_tx.outputs)

    def test_get_amount(self):
        """
        test if we can compute the correct amount of a multisig TxOutput
        """
        self.assertEquals(self.multisig_tx.outputs[0].amount, 1099511627774)

    def test_fee_property(self):
        """
        test if we can compute the correct fee_amount of a multisig tx
        """
        self.assertEquals(self.multisig_tx.fee, 2)

    def test_serialize_deserialize_identical(self):
        """
        test if t and from_json(t.json()) are identical
        where t contains a multisig output
        """
        self.assertEquals(Transaction.from_json(self.multisig_tx.json()).hash, self.multisig_tx.hash)


class TestWallet(unittest.TestCase):
    """
    In this class we test the wallet and generation of transactions by
    the wallet.
    """
    def setUp(self):
        # get a wallet
        self.bc = Blockchain(persistence=Mockpersistence())
        self.wal = Wallet(persist=False, force_new=True, blockchain=self.bc)
        # create a coinbase_tx
        self.coinbase_tx = self.wal.gen_coinbase_tx(2)
        # We put this tx in the next block
        fstblock = find_next_block_noabrt(genesisblock, [self.coinbase_tx])
        self.bc.add_block(fstblock)
        # Create a new transaction and spend the coinbase
        tx_amount = self.coinbase_tx.outputs[0].amount//2-1
        tx = self.wal.gen_transfer_tx(1, [self.wal.public_key],
                [tx_amount], 2)
        self.tx = tx
        # after creating the new tx, we store it in the next block
        self.sndblock = find_next_block_noabrt(fstblock, [self.tx])
        self.bc.add_block(self.sndblock)

    def tearDown(self):
        pass

    def test_valid_tx(self):
        """
        test if the wallet built a correct transaction
        """
        self.assertEquals(self.tx.is_valid(blockchain=self.bc), True)

    def test_non_coinbase_tx_spendable(self):
        """
        test if we can spend the newly generated funds
        """
        spendable_txouts_and_pks = self.wal.get_own_txouts_and_tx_pubkey_from_tx(self.tx)
        spendable_txouts = spendable_txouts_and_pks[0]
        self.assertEquals(spendable_txouts, self.tx.outputs)

    def test_fee_property(self):
        """
        test if we can compute the correct fee of a regular tx
        """
        self.assertEquals(self.tx.fee, 2)

    def test_wallet_get_balance(self):
        """
        test if we can compute our balance
        """
        self.assertEquals(self.wal.get_balance(), self.coinbase_tx.outputs[0].amount-2)
        # The 2 has been spent as "fee".
        # Normally they would have been included in the coinbase of the second
        # block. But in the tests there is no coinbase in the second
        # block.


if __name__ == 'main':
    unittest.main()

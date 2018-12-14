"""
Class for the Proof of Retrievability according to Shacham and Waters. The variables are
named according to the paper.
"Compact Proofs of Retrievability"
J. Cryptology, 26(3):442–83, Jul. 2013.
http://cseweb.ucsd.edu/~hovav/papers/sw13.html

All the numbers are currently numbers. When stuff in this class
becomes a bottleneck, a starting point could be to convert all those
numbers to bytes.
"""

from koppercoin.crypto.AbstractProofOfRetrievability import AbstractProofOfRetrievability
from pypbc import *
from Crypto.Random import random as srandom
from Crypto.PublicKey import DSA
import hashlib
import os
import random


def hash(message):
    """computes a hash"""
    return hashlib.sha512(message).digest()


def str_to_bytes(string):
    """Takes a string and returns a byte-representation"""
    return str.encode(string)


def int_to_bytes(n):
    """Takes an integer and returns a byte-representation"""
    return n.to_bytes((n.bit_length() + 7) // 8, 'little') or b'\0'
    # http://stackoverflow.com/questions/846038/convert-a-python-int-into-a-big-endian-string-of-bytes


def bytes_to_int(byte):
    """Takes some Bytes and returns an Integer."""
    return int.from_bytes(byte, 'little')


# The SW-scheme needs a signing algorithm. We will pick DSA for
# this. Since PyCrypto exposes too much stuff, we have implemented a
# wrapper class
class SignatureScheme:
    def keygen(self):
        """Key generation. Returns a (public, private)-keypair"""
        key = DSA.generate(1024)
        return (key.publickey(), key)

    def sign(self, privkey, message):
        """Signs a message"""
        h = hash(message)
        k = srandom.StrongRandom().randint(1, privkey.q-1)
        return privkey.sign(h, k)

    def verify(self, pubkey, message, signature):
        """Verifies a signature

        >>> SigScheme=SignatureScheme()
        >>> (pub, priv) = SigScheme.keygen()
        >>> message = str.encode("abcdef")
        >>> sig = SigScheme.sign(priv, message)
        >>> SigScheme.verify(pub, message, sig)
        True
        """
        h = hash(message)
        return pubkey.verify(h, signature)


class SWProofOfRetrievability(AbstractProofOfRetrievability):
    _s = 2
    # In the Shacham-Waters scheme the file is split into blocks. Each
    # block is s sectors long. Each sector is in Z/pZ.
    # The storage overhead of the encoded file is 1+1/s times the filesize
    _sectorsize_prime = 730750818665451621361119245571504901405976559617
    # _sectorsize_prime is the prime number p
    _sectorsize = 20
    # since splitting the file in parts of exactly p involves division
    # with remainder of big numbers, which is too slow (yes, I had it
    # implemented) we split the file in parts of multiple bytes.
    # How many bytes should we take? The biggest amount of bytes where the
    # numbers which can be represented are smaller than _sectorsize_prime
    # this number is _sectorsize
    _stored_params = """type a
    q 8780710799663312522437781984754049815806883199414208211028653399266475630880222957078625179422662221423155858769582317459277713367317481324925129998224791
    h 12016012264891146079388821366740534204802954401251311822919615131047207289359704531102844802183906537786776
    r 730750818665451621361119245571504901405976559617
    exp2 159
    exp1 107
    sign1 1
    sign0 1
    """
    _params = Parameters(param_string=_stored_params)
    _pairing = Pairing(_params)
    # these parameters are from test_bls from pypbc

    @staticmethod
    def keygen():
        """returns a (public, private)-keypair

        >>> (publick, secretk) = SWProofOfRetrievability.keygen()
        """
        sigscheme = SignatureScheme()
        (spk, ssk) = sigscheme.keygen()
        # signing public key, signing secret key
        alpha = Element.random(SWProofOfRetrievability._pairing, Zr)
        sk = (alpha, ssk)
        # secret key
        generator_G2 = Element.random(SWProofOfRetrievability._pairing, G2)
        v = generator_G2**alpha
        pk = (generator_G2, v, spk)
        return (pk, sk)

    @staticmethod
    def _split_data(data):
        """splits the data in blocks and sectors. The result looks
        like this: [[1,..],[2,..],..]. We also apply a padding."""
        # split the file in sectors
        sectorsize = SWProofOfRetrievability._sectorsize
        sectors = []
        # Each sector consists of sectorsize bytes
        for pointerpos in range(0, len(data), sectorsize):
            mi = data[pointerpos: pointerpos + sectorsize]
            sectors.append(mi)
        # Each block has s sectors
        s = SWProofOfRetrievability._s
        mij = []
        for j in range(0, len(sectors), s):
            mi = sectors[j: j+s]
            mij.append(mi)
        # if the last block does not have s elements, then include as
        # many ones as needed. Note that one is the multiplicative
        # neutral in Z/pZ
        # In fact it is not a padding, in the sense that it can be
        # inverted. We just fill up the blocks in a well-defined way.
        while len(mij[-1]) != SWProofOfRetrievability._s:
            mij[-1] = mij[-1] + [int_to_bytes(1)]
        return mij

    @staticmethod
    def encode(privatekey, publickey, data):
        """encodes the data into chunks and generates the
        authenticators and the filehandle.

        >>> message = "abcdefghijklmnopqrstuvwxyz"*5
        >>> data = bytes(message, 'utf-8')
        >>> (pk, sk) = SWProofOfRetrievability.keygen()
        >>> (mij, authenticators, filehandle) = SWProofOfRetrievability.encode(sk, pk, data)
        >>> SWProofOfRetrievability.encode(sk, pk, data) # doctest: +NORMALIZE_WHITESPACE, +ELLIPSIS
        ([[b'abcdefghijklmnopqrst', b'uvwxyzabcdefghijklmn'],
          [b'opqrstuvwxyzabcdefgh', b'ijklmnopqrstuvwxyzab'],
          [b'cdefghijklmnopqrstuv', b'wxyzabcdefghijklmnop'],
          [b'qrstuvwxyz', b'...']],
         [[..., ...],
          [..., ...],
          [..., ...],
          [..., ...]],
         [[b..., 4,
          [[..., ...],
           [..., ...]]],
          (..., ...)])
        """
        # split the file
        mij = SWProofOfRetrievability._split_data(data)
        # generate the filehandle
        s = SWProofOfRetrievability._s
        u = [Element.random(SWProofOfRetrievability._pairing, G1) for i in range(0, s)]
        # Filename chosen at random from some sufficiently large domain, compare with paper
        filename = os.urandom(32)
        t0 = [filename] + [len(mij)] + [u]
        (alpha, ssk) = privatekey
        sigscheme = SignatureScheme()
        t = [t0] + [sigscheme.sign(ssk, str.encode(str(t0)))]
        filehandle = t
        # filehandle t = [ [filename, #blocks, u1, ..., us], sig]
        # generate one authenticator per block
        authenticators = []
        for i in range(len(mij)):
            # compute H(filename|i) * prod_j u_j^mij
            prod = Element.one(SWProofOfRetrievability._pairing, G1)
            for j in range(s):
                prod *= u[j] ** bytes_to_int(mij[i][j])
            hashval = Element.from_hash(SWProofOfRetrievability._pairing, G1, hash(filename+str_to_bytes(str(i))))
            authenticators.append((hashval * prod) ** alpha)
        return (mij, authenticators, filehandle)

    @staticmethod
    def genChallenge(nonce):
        """Generates a challenge.
        In the Shacham-Waters scheme one needs to know the filelength
        for creating challenges. We are using a nonce and will derive
        the set Q={(i,v_i)} from the nonce in the function
        _expandChallenge."""
        return nonce

    @staticmethod
    def _expandChallenge(nonce, num_of_blocks):
        """takes a nonce and generates a challenge Q={(i,v_i)}
        according to the SW-paper. See also the documentation for
        genChallenge."""
        random.seed(nonce)
        # if this is not generated deterministically we have a huge
        # problem
        indices = random.sample(range(num_of_blocks), num_of_blocks//2)
        indices.sort()
        # coefficients are chosen mod p
        p = SWProofOfRetrievability._sectorsize_prime
        coefficients = [random.randint(1, p-1) for i in indices]
        challenge = list(zip(indices, coefficients))
        return challenge

    @staticmethod
    def genproof(publickey, data, authenticators, challenge, filehandle):
        """generates a proof of retrievability.

        >>> message = "abcdefghijklmnopqrstuvwxyz"*100
        >>> data = bytes(message, 'utf-8')
        >>> (pk, sk) = SWProofOfRetrievability.keygen()
        >>> (mij, authenticators, filehandle) = SWProofOfRetrievability.encode(sk, pk, data)
        >>> challenge = os.urandom(32)
        >>> (sigma, mu) = SWProofOfRetrievability.genproof(pk, data, authenticators, challenge, filehandle)
        """
        # split the file
        mij = SWProofOfRetrievability._split_data(data)
        # recover all values
        (generator, v, spk) = publickey
        [t0, sig] = filehandle
        [filename, len_mij, u] = t0
        if len(mij) != len_mij:
            raise InvalidInputError("Stated number of blocks does not match real number of blocks")
        sigscheme = SignatureScheme()
        if not sigscheme.verify(spk, str.encode(str(t0)), sig):
            raise InvalidInputError("Signature contained in filehandle does not verify")
        # generate the challenge set
        Q_chal = SWProofOfRetrievability._expandChallenge(challenge, len_mij)
        # compute sigma, the aggregated authenticators
        sigma = Element.one(SWProofOfRetrievability._pairing, G1)
        for (index, coeff) in Q_chal:
            sigma *= authenticators[index]**coeff
        # compute mu, the list of the aggregated blocks
        mu = []
        p = SWProofOfRetrievability._sectorsize_prime
        for j in range(SWProofOfRetrievability._s):
            mu_j = 0
            for (index, coeff) in Q_chal:
                mu_j = (mu_j + coeff * bytes_to_int(mij[index][j])) % p
            mu.append(mu_j)
        return (sigma, mu)

    @staticmethod
    def verify(proof, publickey, challenge, filehandle):
        """verifies a proof of retrievability.

        >>> message = "abcdefghijklmnopqrstuvwxyz"*100
        >>> data = bytes(message, 'utf-8')
        >>> (pk, sk) = SWProofOfRetrievability.keygen()
        >>> (mij, authenticators, filehandle) = SWProofOfRetrievability.encode(sk, pk, data)
        >>> challenge = os.urandom(32)
        >>> proof = SWProofOfRetrievability.genproof(pk, data, authenticators, challenge, filehandle)
        >>> SWProofOfRetrievability.verify(proof, pk, challenge, filehandle)
        True
        """
        # parse all the data
        (generator, v, spk) = publickey
        [t0, sig] = filehandle
        [filename, len_mij, u] = t0
        (sigma, mu) = proof
        Q_chal = SWProofOfRetrievability._expandChallenge(challenge, len_mij)
        sigscheme = SignatureScheme()
        # check if signature in filehandle is correct
        if not sigscheme.verify(spk, str.encode(str(t0)), sig):
            return False
        # for verification we need to check if RHS = LHS
        # compute LHS = e[ H(filename|i)^coeff * prod_j u_j^muj , v ]
        # prodhash = H(filename|i)^coeff
        # produ =  prod_j u_j^muj
        prodhash = Element.one(SWProofOfRetrievability._pairing, G1)
        for (i, coeff) in Q_chal:
            hashval = Element.from_hash(SWProofOfRetrievability._pairing, G1, hash(filename+str_to_bytes(str(i))))
            prodhash *= hashval ** coeff
        produ = Element.one(SWProofOfRetrievability._pairing, G1)
        for j in range(SWProofOfRetrievability._s):
            produ *= u[j] ** mu[j]
        pairing = SWProofOfRetrievability._pairing
        LHS = pairing.apply(prodhash*produ, v)
        # RHS = e(sigma, generator)
        RHS = pairing.apply(sigma, generator)
        if RHS == LHS:
            return True
        return False


class InvalidInputError(Exception):
    pass

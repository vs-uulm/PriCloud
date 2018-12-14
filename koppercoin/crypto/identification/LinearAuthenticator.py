"""
This class implements Homomorphic Linear Authenticators as defined in

Ateniese, Kamara, Katz: "Proofs of Storage from Homomorphic Identification Protocols",
ASIACRYPT 2009
http://dx.doi.org/10.1007/978-3-642-10366-7_19

A Homomorphic linear authenticator is a kind of a ring signature and
can be obtained from any identification protocol.
The transformation from any identification protocol implementing
AbstractIdP to a homomorphic linear authenticator is implemented in
this file.
"""

import hmac
import hashlib
import random
import json
from koppercoin.crypto.identification.GQProtocol import GQProtocol
from koppercoin.crypto.identification.ShoupProtocol import ShoupProtocol

def _int_to_bytes(n):
    """Takes an integer and returns a byte-representation"""
    return n.to_bytes((n.bit_length() + 7) // 8, 'little') or b'\0'
    # http://stackoverflow.com/questions/846038/convert-a-python-int-into-a-big-endian-string-of-bytes

def _bytes_to_int(byte):
    """Takes some Bytes and returns an Integer."""
    return int.from_bytes(byte, 'little')


def IdProtocol_to_LinearAuthenticator(idp, splitfile):
    """
    converts an identification protocol to a linear authenticator

    :param idp: an identification protocol implementing AbstractIdP
    :param splitfile: the functon which is used to split the file into
    chunks. Take as input the file as a bytestring, together with the
    public key, to determine the group where the chunks should exist.
    Returns a list of chunks.

    :returns: a class implementing linear authenticators with static methods

    >>> (publickey, secretkey) = GQLinearAuthenticator.gen()
    >>> message = bytes("abcdefghijklmnopqrstuvwxyz"*50, 'utf-8')
    >>> chunks = GQLinearAuthenticator.splitfile(message, publickey)
    >>> (tags, st) = GQLinearAuthenticator.tag(secretkey, publickey, chunks)
    >>> challenge = [random.SystemRandom().randint(1,2000) for i in range(len(tags))]
    >>> tau = GQLinearAuthenticator.auth(publickey, chunks, tags, challenge)
    >>> mu = sum([_bytes_to_int(chunks[i]) * challenge[i] for i in range(len(chunks))])
    >>> GQLinearAuthenticator.vrfy(publickey, st, mu, challenge, tau)
    True

    >>> (publickey, secretkey) = ShoupLinearAuthenticator.gen()
    >>> message = bytes("abcdefghijklmnopqrstuvwxyz"*15, 'utf-8')
    >>> chunks = ShoupLinearAuthenticator.splitfile(message, publickey)
    >>> (tags, st) = ShoupLinearAuthenticator.tag(secretkey, publickey, chunks)
    >>> challenge = [random.SystemRandom().randint(1,2000) for i in range(len(tags))]
    >>> tau = ShoupLinearAuthenticator.auth(publickey, chunks, tags, challenge)
    >>> mu = sum([_bytes_to_int(chunks[i]) * challenge[i] for i in range(len(chunks))])
    >>> ShoupLinearAuthenticator.vrfy(publickey, st, mu, challenge, tau)
    True
    """
    class LinearAuthenticator():
        """
        This class implements linear authenticators.
        """

        @staticmethod
        def gen():
            """Computes a (public, private)-keypair."""
            return idp.setup()

        @staticmethod
        def splitfile(f, publickey):
            """
            Takes a file and splits in into chunks.
            The size of the chunks is defined by the group in which the
            publickey lives

            :param f: a file encoded as Bytestring
            :returns: a list of chunks, encoded as integers
            """
            return splitfile(f, publickey)

        @staticmethod
        def tag(secretkey, publickey, chunks):
            """is a probabilistic algorithm run by the client to tag a
            file chunks.

            :param secretkey: the secret key
            :param publickey: the public key
            :param chunks: the file split in chunks with splitfile

            :returns: a vector of tags tags and state information st.
            """
            st = (random.SystemRandom().getrandbits(32), len(chunks))
            tags = []
            for i in range(len(chunks)):
                rand = hmac.new(str.encode(json.dumps(st)), _int_to_bytes(i), digestmod=hashlib.sha256).digest()
                tags.append(idp.resp(publickey, secretkey, rand, _bytes_to_int(chunks[i])))
            return (tags, st)

        @staticmethod
        def auth(publickey, chunks, tags, challenge):
            """is a probabilistic algorithm run by the server to generate
            a tag.

            :param publickey: The public key
            :param chunks: the file split in chunks with splitfile
            :param tags: a vector of tags
            :param challenge: a challenge vector
            :returns: a tag tau
            """
            return idp.combine_3(challenge, tags)

        @staticmethod
        def vrfy(publickey, st, mu, challenge, tau):
            """is the algorithm used to verify a tag.

            :param publickey: the public key
            :param st: the state information
            :param mu: corresponds to the linear combination of the filechunks
            :param challenge: the challenge vector
            :param tau: the tag generated by the prover with Auth.
            :returns: True iff the interaction is valid.
            """
            alpha = []
            for i in range(len(challenge)):
                rand = hmac.new(str.encode(json.dumps(st)), _int_to_bytes(i), digestmod=hashlib.sha256).digest()
                alpha.append(idp.comm(publickey, rand))
            return idp.vrfy(publickey, idp.combine_1(challenge, alpha), mu, tau)

    return LinearAuthenticator # return the whole class


def _gqsplitfile(f, publickey):
    # determine the size of a chunk
    chunksize = (publickey[-1].bit_length() + 7) // 8
    chunks = []
    for j in range(0, len(f), chunksize):
        chunks.append(f[j: j+chunksize])
    return chunks

GQLinearAuthenticator = IdProtocol_to_LinearAuthenticator(GQProtocol, _gqsplitfile)
"""
This class is the result of applying the transformation from a
homomorphic identification protocol to a linear authenticator to
the GQ identification protocol.
"""

def _shoupsplitfile(f, publickey):
    return _gqsplitfile(f, publickey)
    # incidentally the splitting from the gq-protocol works

ShoupLinearAuthenticator = IdProtocol_to_LinearAuthenticator(ShoupProtocol, _shoupsplitfile)
"""
This class is the result of applying the transformation from a
homomorphic identification protocol to a linear authenticator to
the Shoup identification protocol.
"""

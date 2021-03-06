"""
This class implements the Homomorphic Identification Protocol of
Shoup

Shoup
On the Security of a Practical Identification Scheme
http://dx.doi.org/10.1007/s001459900056

Ateniese, Kamara, Katz: "Proofs of Storage from Homomorphic
Identification Protocols",
ASIACRYPT 2009
http://dx.doi.org/10.1007/978-3-642-10366-7_19
"""

from koppercoin.crypto.identification.AbstractIdentificationProtocol import AbstractIdP
import random
import gmpy
import hashlib

class ShoupProtocol(AbstractIdP):
    @staticmethod
    def setup():
        """Computes a (public, private)-keypair.
        
        >>> (publickey, secretkey) = ShoupProtocol.setup()
        """
        # generate the primes
        p = 0
        while p % 4 != 3:
            p = random.SystemRandom().getrandbits(1024)
            p = int(gmpy.next_prime(p))
        q = 4
        while q % 4 != 3:
            q = random.SystemRandom().getrandbits(1024)
            q = int(gmpy.next_prime(q))
        n = p*q
        # search for a quadratic residue mod n
        y = random.SystemRandom().getrandbits(1024) % n
        y = pow(y,2,n)
        publickey = (y, n)
        secretkey = (p, q)
        return (publickey, secretkey)

    @staticmethod
    def comm(publickey, r):
        """
        is a probabilistic algorithm run by the prover to generate
        the first message. The input is the public key and a nonce r.
        The result is an integer and the modulus n, since we need to
        define the ring in which the integer lives.

        >>> import os
        >>> (publickey, secretkey) = ShoupProtocol.setup()
        >>> ShoupProtocol.comm(publickey, os.urandom(2048)) # doctest: +ELLIPSIS
        (..., ...)
        """
        # We need to view r as having positive jacobi symbol
        # since any quadratic residue has a positive jacobi symbol, we
        # simply square it.
        (y, n) = publickey
        r = pow(int.from_bytes(r, "little"), 2, n)
        return (r, n)

    @staticmethod
    def genChallenge(nonce):
        """returns a challenge."""
        pseudorand = hashlib.sha512(nonce).digest()
        challenge = int.from_bytes(pseudorand, "little")
        return challenge

    @staticmethod
    def resp(publickey, secretkey, r, challenge):
        """is a probabilistic algorithm run by the prover to generate
        the third message. The input is the public key, the secret
        key, as well as a nonce r and the challenge itself, generated
        by genChallenge.
        The result of this function is the response as well as the
        modulus n.

        >>> import os
        >>> (publickey, secretkey) = ShoupProtocol.setup()
        >>> r = os.urandom(2048)
        >>> challenge = ShoupProtocol.genChallenge(os.urandom(32))
        >>> ShoupProtocol.resp(publickey, secretkey, r, challenge) # doctest: +ELLIPSIS
        (mpz(...), ...)
        """
        (y, n) = publickey
        (p, q) = secretkey
        # We output a random 2^(3*5)th root of +- r * y ^challenge, where
        # the sign is chosen such that a root exists.
        r = pow(int.from_bytes(r, "little"), 2, n)
        base = r * pow(y, challenge, n)
        # Choose the sign accordingly
        if gmpy.jacobi(base, n) <= 0:
            base = (n - base) % n
        s = gmpy.invert(p,q)
        t = gmpy.invert(q,p)
        for i in range(3*5): # 5 is the security parameter
            # In this loop we compute modular roots
            # Since p,q = 3 mod 4, a root mod p is just pow(a, (p + 1) / 4, p)
            # but we need to use the chinese remainder theorem to lift
            # if to mod n
            # compute mod p
            ap = base % p
            ap = pow(base, (p + 1) // 4, p)
            # choose the one which is a quadratic residue
            if gmpy.jacobi(ap,p) <= 0:
                ap = (p - ap) % p
            # compute mod q
            aq = base % q
            aq = pow(base, (q + 1) // 4, q)
            # choose the one which is a quadratic residue
            if gmpy.jacobi(aq,q) <= 0:
                aq = (q - aq) % q
            # we have s, t, such that sp+tq = 1
            # so the solution is simply ap*t*q + aq*s*p
            base = ap*t*q+aq*s*p
        return (base, n)

    @staticmethod
    def vrfy(publickey, comm, challenge, resp):
        """is the algorithm used to verify the interaction.

        :param publickey: the public key
        :param comm: is the second message (commit) generated by the prover with comm. 
        :param challenge: the challenge generated by genChallenge.
        :param resp: the response generated by the prover with resp.
        :returns: True iff the interaction is valid.

        >>> import os
        >>> (publickey, secretkey) = ShoupProtocol.setup()
        >>> r = os.urandom(2048)
        >>> comm = ShoupProtocol.comm(publickey, r)
        >>> challenge = ShoupProtocol.genChallenge(os.urandom(32))
        >>> resp = ShoupProtocol.resp(publickey, secretkey, r, challenge)
        >>> ShoupProtocol.vrfy(publickey, comm, challenge, resp)
        True

        >>> import os
        >>> (publickey, secretkey) = ShoupProtocol.setup()
        >>> r = os.urandom(2048)
        >>> comm = ShoupProtocol.comm(publickey, r)
        >>> challenge = ShoupProtocol.genChallenge(os.urandom(32))
        >>> r = os.urandom(2048) # For the response we choose a different r
        >>> resp = ShoupProtocol.resp(publickey, secretkey, r, challenge)
        >>> ShoupProtocol.vrfy(publickey, comm, challenge, resp)
        False
        """
        (y, n) = publickey
        lhs = pow(resp[0], pow(2,(3*5)), n)
        (comm, _) = comm
        rhs = (comm * pow(y, challenge, n)) % n
        if lhs == rhs or lhs == (n-rhs) % n:
            return True
        else:
            return False

    @staticmethod
    def combine_1(c, alpha):
        """Since this is about homomorphic identification protocols,
        we need to have combiner functions. The notation for this is
        straight out of the paper. combine_1 combines the commits comm.
        combine_3 is used to combine the responses Resp.

        Note that there is not combine_2. The challenges are combined
        by a simple linear combination.
        If any of this is not clear, please read the paper mentioned
        above.
        
        The alpha need to be computed by the same publickey. Otherwise
        the alphas are in different rings, since the modulus n is not
        the same. In this case we have undefined behaviour.

        :param c: a coefficient vector to aggregate the commits.
        :param alpha: a list of commits output by comm
        """
        n = alpha[0][1]
        result = 1
        for i in range(len(alpha)):
            comm = alpha[i]
            result = (result * pow(comm[0],c[i],n)) % n
        return (result, n)

    @staticmethod
    def combine_3(c, gamma):
        """combine_3 is used to combine the responses Resp.

        :param c: a coefficient vector to aggregate the commits.
        :param gamma: a list of responses output by Resp.

        >>> import os
        >>> (publickey, secretkey) = ShoupProtocol.setup()
        >>> rs = [os.urandom(2048) for i in range(3)]
        >>> comms = [ShoupProtocol.comm(publickey, r) for r in rs]
        >>> challenges = [ShoupProtocol.genChallenge(os.urandom(32)) for i in range(3)]
        >>> resps = [ShoupProtocol.resp(publickey, secretkey, rs[i], challenges[i]) for i in range(3)]
        >>> c = [2,3,5]
        >>> aggregated_challenges = sum([c[i] * challenges[i] for i in range(3)])
        >>> ShoupProtocol.vrfy(publickey, ShoupProtocol.combine_1(c, comms), aggregated_challenges, ShoupProtocol.combine_3(c, resps))
        True
        """
        n = gamma[0][1]
        result = 1
        for i in range(len(gamma)):
            resp = gamma[i]
            result = (result * pow(resp[0],c[i],n)) % n
        return (result, n)

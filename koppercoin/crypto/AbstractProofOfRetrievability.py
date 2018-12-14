from abc import ABCMeta, abstractmethod

"""This class implements an interface for proofs of retrievability."""
class AbstractProofOfRetrievability(metaclass=ABCMeta):
    @staticmethod
    @abstractmethod
    def keygen():
        """Compute a (public, private)-keypair for a proof of
        retrievability.

        :returns: tuple -- the (public, private)-keypair.
        """
        pass

    @staticmethod
    @abstractmethod
    def encode(privatekey, publickey, data):
        """encode the data into chunks and generates the
        authenticators, a.k.a. tags, homomorphic linear
        authenticators and a filehandle for identifying the file later
        on.

        :param privatekey: The private key to use.
        :param publickey: The public key to use.
        :param data: The data which should be encoded.
        :returns: tuple -- (fileblocks, authenticators, filehandle)
        """
        pass

    @staticmethod
    @abstractmethod
    def genChallenge(nonce):
        """generates a challenge."""
        pass

    @staticmethod
    @abstractmethod
    def genproof(publickey, data, authenticators, challenge):
        """This function generates a proof of retrievability.

        :param publickey: The public key of the prover.
        :param data: The data over which retrievability should be proven.
        :param authenticators: The authenticators generated by the encode method.
        :param challenge: The challenge, generated by the method genChallenge.
        """
        pass

    @staticmethod
    @abstractmethod
    def verify(proof, publickey, challenge, filehandle):
        """verifies a proof of retrievability.

        :param proof: The proof of retrievability.
        :param publickey: The publickey of the prover.
        :param challenge: the challenge used in the generation of the proof.
        :param filehandle: The filehandle of the file over which retrievability was proven.
        :returns: Bool -- True iff the proof is valid.

        """
        pass
"""
This code implements onetime public keys as explained in the
Cryptonote Whitepaper of Nicolas van Saberhagen p. 7, 8
https://cryptonote.org/whitepaper.pdf
"""

import os
import binascii
from koppercoin.crypto import ietf_ed25519, lww_signature


def keygen():
    """Returns a longtime keypair (secret, public) such that one can
    derive further keys from the public key.
    These are basically two usual ECC-keypairs.
    """
    (secret1, public1) = lww_signature.keygen()
    (secret2, public2) = lww_signature.keygen()
    return ((secret1, secret2), (public1, public2))


def key_to_trackingkey(key):
    """Takes a keypair and returns the tracking key."""
    ((a, _), (_, B)) = key
    return (a, B)


def generate_ot_key(public_key, nonce=None):
    """Derives a onetime publickey.
    The corresponding onetime private key can only be recovered with
    knowledge of the private_key of the public_key.
    More exactly the output is (ot_pubkey, dh_key), where dh_key and
    the private key corresponding to the public_key in the input are
    needed to compute ot_privkey, the onetime private key.

    The nonce should be unique modulo the group order and can be
    reused for different public keys. It will be generated
    automaticaly if not set.

    >>> import os
    >>> nonce = os.urandom(32)
    >>> (_, pk) = keygen()
    >>> ot_key = generate_ot_key(pk, nonce)

    >>> (_, pk) = keygen()
    >>> ot_key = generate_ot_key(pk)
    """
    if not nonce:
        nonce = os.urandom(32)
    (A, B) = public_key
    (A, B) = (binascii.unhexlify(A), binascii.unhexlify(B))
    nonce = int.from_bytes(nonce, "little") % ietf_ed25519.q
    hashval = ietf_ed25519.sha512(
                ietf_ed25519.point_compress(
                  ietf_ed25519.point_mul(
                      nonce,
                      ietf_ed25519.point_decompress(A))))
    first = ietf_ed25519.point_mul(
                int.from_bytes(hashval, "little"),
                ietf_ed25519.G)
    second = ietf_ed25519.point_decompress(B)
    ot_pubkey = ietf_ed25519.point_add(first, second)
    dh_key = ietf_ed25519.point_mul(nonce, ietf_ed25519.G)
    # In the Cryptonote Whitepaper dh_key is called R
    # Next we compress the points
    ot_pubkey = binascii.hexlify(ietf_ed25519.point_compress(ot_pubkey)).decode()
    dh_key = binascii.hexlify(ietf_ed25519.point_compress(dh_key)).decode()
    return (ot_pubkey, dh_key)


def generate_ot_keys(public_keys, nonce=None):
    """Derives a list of onetime publickeys using the same nonce.
    The input is a list of public keys.
    Each corresponding onetime private key can only be recovered with
    knowledge of the private_key of the public_key.
    The output is ([ot_pubkey1, ot_pubkey2, ...], dh_key).
    The dh_keys are the same for all ot_pubkeys since the nonce is the
    same.
    Compare with the documentation of generate_ot_key.
    The nonce should be unique modulo the group order and can be
    reused for different public keys. It will be generated
    automaticaly if not set.

    This is a batch-processing version of the function generate_ot_key.

    >>> public_keys = [keygen()[1] for i in range(3)]
    >>> ot_keys = generate_ot_keys(public_keys)
    """
    if not nonce:
        nonce = os.urandom(32)
    ot_keys_with_dh_keys = [generate_ot_key(pk, nonce) for pk in public_keys]
    # dh_keys are the same since the nonce is the same.
    dh_key = ot_keys_with_dh_keys[0][1]
    ot_pubkkeys = [ot_keys_with_dh[0] for ot_keys_with_dh in ot_keys_with_dh_keys]
    return (ot_pubkkeys, dh_key)


def recoverable(ot_key, tracking_key):
    """Takes a onetime key and a tracking key and returns if
    the private onetime key is recoverable.

    >>> longterm_key = keygen()
    >>> longterm_pub = longterm_key[1]
    >>> ot_key = generate_ot_key(longterm_pub)
    >>> trackingkey = key_to_trackingkey(longterm_key)

    >>> recoverable(ot_key, trackingkey)
    True

    >>> wrong_lt_key = keygen()
    >>> wrong_lt_pub = wrong_lt_key[1]
    >>> wrong_trackingkey = key_to_trackingkey(wrong_lt_key)
    >>> recoverable(ot_key, wrong_trackingkey)
    False
    """
    (ot_pubkey, dh_key) = ot_key
    (ot_pubkey, dh_key) = (binascii.unhexlify(ot_pubkey), binascii.unhexlify(dh_key))
    (a, B) = tracking_key
    hashval = ietf_ed25519.sha512(
                ietf_ed25519.point_compress(
                  ietf_ed25519.point_mul(
                      int(a, 16),
                      ietf_ed25519.point_decompress(dh_key))))
    first = ietf_ed25519.point_mul(
                int.from_bytes(hashval, "little"),
                ietf_ed25519.G)
    second = ietf_ed25519.point_decompress(binascii.unhexlify(B))
    key_ = ietf_ed25519.point_compress(
            ietf_ed25519.point_add(first, second))
    return ot_pubkey == key_


def recover_sec_key(ot_key, keypair):
    """Takes a onetime public key and a keypair and recovers the
    onetime secret key if possible.

    >>> longterm_key = keygen()
    >>> longterm_pub = longterm_key[1]
    >>> ot_key = generate_ot_key(longterm_pub)
    >>> (ot_pubkey, dh_key) = ot_key
    >>> trackingkey = key_to_trackingkey(longterm_key)

    >>> recovered_sec_key = recover_sec_key(ot_key, longterm_key)
    >>> lww_signature.secret_to_public(recovered_sec_key) == ot_pubkey
    True
    """
    (ot_pubkey, dh_key) = ot_key
    ((a, b), (A, B)) = keypair

    first = ietf_ed25519.sha512(
                ietf_ed25519.point_compress(
                  ietf_ed25519.point_mul(
                      int(a, 16),
                      ietf_ed25519.point_decompress(binascii.unhexlify(dh_key)))))
    first = int.from_bytes(first, "little")
    second = int(b, 16)
    ot_sec_key = first + second
    ot_sec_key = hex(ot_sec_key)
    # Check correctness
    assert(ot_pubkey == lww_signature.secret_to_public(ot_sec_key))
    return ot_sec_key

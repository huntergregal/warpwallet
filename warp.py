import argparse
import binascii
import bitcoin
import concurrent.futures
import itertools
import random
import scrypt
import string
import sys

from passlib.utils.pbkdf2 import pbkdf2

#ARGS
parser = argparse.ArgumentParser(description="warpwallet cracker.")
#Cusstom outfile
parser.add_argument('-a', '--address', dest='addr', help='bitcoin address to brute', required = True)
parser.add_argument('-t', '--threads', dest='threads', help='number of threads', required = True)
parser.add_argument('-p', '--pass', dest='passLength', help='length of passhrase', required = True)
#parse
args = parser.parse_args()

keyspace = string.ascii_letters + string.digits
_pub_key = (args.addr).strip()


def xor(s1, s2):
    return "".join(chr(ord(a) ^ ord(b)) for a, b in zip(s1, s2))


def warp(passphrase, salt=""):
    s1 = scrypt.hash(passphrase + "\x01", salt+"\x01", N=2**18, r=8, p=1,
                     buflen=32)
    s2 = pbkdf2(passphrase + "\x02", salt=salt+"\x02", keylen=32, rounds=2**16,
                prf="hmac-sha256")
    key = binascii.hexlify(xor(s1, s2))
    return key, bitcoin.pubtoaddr(bitcoin.privtopub(key))


def _pbkdf2(passphrase, salt=""):
    return pbkdf2(passphrase + "\x02", salt=salt+"\x02", keylen=32,
                  rounds=2**16, prf="hmac-sha256")


def _scrypt(passphrase, salt=""):
    return scrypt.hash(passphrase + "\x01", salt+"\x01", N=2**18, r=8, p=1,
                       buflen=32)


def when(passphrase, *futures):
    result = []
    def foo(f):
        result.append(f.result())
        if len(result) == len(futures):
            key = binascii.hexlify(xor(*result))
            pub = bitcoin.pubtoaddr(bitcoin.privtopub(key))
            if pub == _pub_key:
                print "Found passphrase: ", passphrase
                print key , "->", pub
    for future in futures:
        future.add_done_callback(foo)


with concurrent.futures.ProcessPoolExecutor(max_workers=int(args.threads)) as executor:
    for p in itertools.imap(lambda t: "".join(t), itertools.product(keyspace, repeat=int(args.passLength))):
        when(p, executor.submit(_scrypt, p), executor.submit(_pbkdf2, p))

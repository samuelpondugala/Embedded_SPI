import os
import hashlib

def generate_data(size):
    return os.urandom(size)

def checksum(data):
    return hashlib.md5(data).hexdigest()

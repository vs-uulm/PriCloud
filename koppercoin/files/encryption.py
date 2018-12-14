#from nacl.public import SealedBox
# sealdbox only in 1.2.0
# use ephemereal keys later
from nacl.utils import random
from nacl.secret import SecretBox
import json
import base64

_separator = b'//body//'

def encrypt(file, privkey, recipients):
    # ignores privkey and recipients for now
    key = random(SecretBox.KEY_SIZE)
    box = SecretBox(key)
    enc = box.encrypt(file.encode("utf-8"))
    jsondata = json.dumps({"version":"0.1","key":base64.b64encode(key).decode("utf-8")})
    return jsondata.encode("utf-8")+_separator+enc


def decrypt(data, privkey):
    j,enc = data.split(sep=_separator, maxsplit=1)
    jsondata = json.loads(j.decode("utf-8"))
    key = base64.b64decode(jsondata["key"].encode("utf-8"))
    version = jsondata["version"]
    if version == "0.1":
        box = SecretBox(key)
        return box.decrypt(enc).decode("utf-8")
    else:
        raise NotImplementedError("Filetype not supported.")


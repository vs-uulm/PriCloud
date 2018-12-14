"""
This script evaluates the size of the LWW linkable ring signatures
implemented in koppercoin.crypto.lww_signature
"""
from koppercoin.crypto.lww_signature import *
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
plt.style.use('ggplot')
import jsonpickle
from pympler import asizeof
import gc

# The ringsizes which will be tested
ringsizes = range(1, 21)

memsizes = pd.DataFrame(np.zeros(len(ringsizes)), index=ringsizes)

for ringsize in ringsizes:
    print("Running LWW-Signature on Ringsize " + str(ringsize) + " from " + str(list(ringsizes)))

    # generate key of other participants in the anonymity set
    public_keys = [keygen()[1] for j in range(ringsize)]
    m = "some message"
    (sec, pub) = keygen()
    public_keys.append(pub)

    # generate the signature
    sig = ringsign(public_keys, sec, m)

    # Save its size
    memsizes[0][ringsize] = asizeof.asizeof(sig)

    print("Size of memsizes object is " + str(asizeof.asizeof(memsizes)) + " Bytes")
    print("Number of gc-tracked objects: " + str(len(gc.get_objects())))

# Save the data in complicated JSON-format
with open('memsizes_LWWsig.json', 'w') as f:
    json_obj = jsonpickle.encode(memsizes)
    f.write(json_obj)

print("Running postprocessing steps")

# Save the data in handy .csv
memsizes.to_csv('memsizes_LWWsig.csv')

# Set up the plot
plt.figure()
plt.rc('text', usetex=True)
plt.rc('font', family='serif')

# plot it
memsizes.plot(style='bo', legend=None)

plt.xlabel('Size of the Ring')
plt.ylabel('Memory Size in Bytes')
plt.title('Memory Measurements for LWW-signatures')
#plt.legend(loc='upper left')
plt.savefig('memsizes_LWWsig.png')

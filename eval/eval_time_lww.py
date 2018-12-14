"""
This script evaluates the performance of the LWW Linkable Ring
Signature Scheme implemented in koppercoin.crypto.lww_signature
"""
from koppercoin.crypto.lww_signature import *
import time
import pandas as pd
import matplotlib.pyplot as plt
plt.style.use('ggplot')
import jsonpickle
from pympler import asizeof
import gc

# The ringsizes which will be tested
ringsizes = range(1, 21)
# The number of runs per ringsize
runs = 20

timings = {'keygen': [],
           'ringsign': [],
           'verify': []}

for i in range(len(ringsizes)):
    print("Running LWW-Signature on Ringsize " + str(ringsizes[i]) + " from " + str(list(ringsizes)))
    timings['keygen'].append([])
    timings['ringsign'].append([])
    timings['verify'].append([])
    for run in range(runs):

        # generate key of other participants in the anonymity set
        public_keys = [keygen()[1] for j in range(ringsizes[i])]
        m = "some message"

        time_pre = time.time()
        (sec, pub) = keygen()
        time_post = time.time()
        duration = time_post - time_pre
        timings['keygen'][i].append(duration)

        public_keys.append(pub)

        time_pre = time.time()
        sig = ringsign(public_keys, sec, m)
        time_post = time.time()
        duration = time_post - time_pre
        timings['ringsign'][i].append(duration)

        time_pre = time.time()
        verify(public_keys, m, sig)
        time_post = time.time()
        duration = time_post - time_pre
        timings['verify'][i].append(duration)

    print("Size of timing object is " + str(asizeof.asizeof(timings)) + " Bytes")
    print("Number of gc-tracked objects: " + str(len(gc.get_objects())))

    # Save the data in complicated JSON-format
    with open('timings_LWWsig.json', 'w') as f:
        json_obj = jsonpickle.encode(timings)
        f.write(json_obj)

print("Running postprocessing steps")

# Transform to handy Dataframes
for algo in ['keygen', 'ringsign', 'verify']:
    timings[algo] = pd.DataFrame(timings[algo]).T
    timings[algo].columns = ringsizes

for algo in ['keygen', 'ringsign', 'verify']:
    # Save the data in handy .csv
    timings[algo].to_csv('timings_LWWsig_'+str(algo)+'.csv')

    # Set up the plot
    plt.figure()
    plt.xlabel('Size of the Ring')
    plt.ylabel('Time in sec')
    plt.title('Time Measurements for ' + str(algo))

    # Plot the values
    timings[algo].boxplot()
    plt.legend(loc='upper left')
    # Save the figure
    plt.savefig('timings_LWWsig_'+str(algo)+'.png')

# Comparison between the average times of all of them
plt.figure()
plt.rc('text', usetex=True)
plt.rc('font', family='serif')

plt.xlabel('Size of the Ring')
plt.ylabel('Time in sec')
plt.title('Time Measurements for LWW-Signatures')
# Build a DataFrame with all the timing data
df = pd.DataFrame([timings[key].mean() for key in timings.keys()], index=timings.keys())
df = df.transpose()
# plot it
df.keygen.plot(style='bo')
df.verify.plot(style='gv')
# df.genchallenge.plot(style='r^')
# df.genproof.plot(style='c>')
df.ringsign.plot(style='m<')

plt.legend(loc='upper left')
plt.savefig('timings_LWWsig_all.png')

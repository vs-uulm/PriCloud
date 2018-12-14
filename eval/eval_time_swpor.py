"""
This script evaluates the performance of the Shacham-Waters Proof of
retrievability implemented in
koppercoin.crypto.SWProofofRetrievability
"""
from koppercoin.crypto.SWProofOfRetrievability import *
import time
import pandas as pd
import matplotlib.pyplot as plt
plt.style.use('ggplot')
import os
import jsonpickle
from pympler import asizeof
import gc

# The messagesizes which will be tested
messagesizes = range(50, 201, 50)
# The number of runs per messagesize
runs = 2

timings = {'keygen': [],
           'encode': [],
           'genchallenge': [],
           'genproof': [],
           'verify': []}

for i in range(len(messagesizes)):
    print("Running PoR on messagesize " + str(messagesizes[i]) + " from " + str(list(messagesizes)))
    timings['keygen'].append([])
    timings['encode'].append([])
    timings['genchallenge'].append([])
    timings['genproof'].append([])
    timings['verify'].append([])
    for run in range(runs):
        data = os.urandom(messagesizes[i]*1024)

        time_pre = time.time()
        (pk, sk) = SWProofOfRetrievability.keygen()
        time_post = time.time()
        duration = time_post - time_pre
        timings['keygen'][i].append(duration)

        time_pre = time.time()
        (mij, authenticators, filehandle) = SWProofOfRetrievability.encode(sk, pk, data)
        time_post = time.time()
        duration = time_post - time_pre
        timings['encode'][i].append(duration)

        time_pre = time.time()
        challenge = os.urandom(32)
        time_post = time.time()
        duration = time_post - time_pre
        timings['genchallenge'][i].append(duration)

        time_pre = time.time()
        proof = SWProofOfRetrievability.genproof(pk, data, authenticators, challenge, filehandle)
        time_post = time.time()
        duration = time_post - time_pre
        timings['genproof'][i].append(duration)

        time_pre = time.time()
        SWProofOfRetrievability.verify(proof, pk, challenge, filehandle)
        time_post = time.time()
        duration = time_post - time_pre
        timings['verify'][i].append(duration)

    print("Size of timing object is " + str(asizeof.asizeof(timings)) + " Bytes")
    print("Number of gc-tracked objects: " + str(len(gc.get_objects())))

    # Save the data in complicated JSON-format
    with open('timings_SWPoR.json', 'w') as f:
        json_obj = jsonpickle.encode(timings)
        f.write(json_obj)

print("Running postprocessing steps")

# Transform to handy Dataframes
for algo in ['keygen', 'encode', 'genchallenge', 'genproof', 'verify']:
    timings[algo] = pd.DataFrame(timings[algo]).T
    timings[algo].columns = messagesizes

for algo in ['keygen', 'encode', 'genchallenge', 'genproof', 'verify']:
    # Save the data in handy .csv
    timings[algo].to_csv('timings_SWPoR_'+str(algo)+'.csv')

    # Set up the plot
    plt.figure()
    plt.rc('text', usetex=True)
    plt.rc('font', family='serif')
    plt.xlabel('Filesize in Kb')
    plt.ylabel('Time in sec')
    plt.title('Time Measurements for ' + str(algo))

    # Plot the values
    timings[algo].boxplot()
    plt.legend(loc='upper left')
    # Save the figure
    plt.savefig('timings_SWPoR_'+str(algo)+'.png')

# Comparison between the average times of all of them
plt.figure()
plt.rc('text', usetex=True)
plt.rc('font', family='serif')
plt.xlabel('Filesize in Kb')
plt.ylabel('Time in sec')
plt.title('Time Measurements for the Proof of Retrievability')
# Build a DataFrame with all the timing data
df = pd.DataFrame([timings[key].mean() for key in timings.keys()], index=timings.keys())
df = df.transpose()
# plot it
df.keygen.plot(style='bo')
df.verify.plot(style='gv')
df.genchallenge.plot(style='r^')
df.genproof.plot(style='c>')
df.encode.plot(style='m<')

plt.legend(loc='upper left')
plt.savefig('timings_SWPoR_all.png')

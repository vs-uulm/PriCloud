"""
This script evaluates the performance of the
AKKEffProofOfRetrievability Proof of
retrievability implemented in
koppercoin.crypto.AKKEffProofOfRetrievability.py
"""
from koppercoin.crypto.AKKEffProofOfRetrievability import *
from koppercoin.crypto.AKKProofOfRetrievability import GQProofOfRetrievability as SlowGQProofOfRetrievability
import time
import pandas as pd
import matplotlib.pyplot as plt
plt.style.use('ggplot')
import os
import jsonpickle
from pympler import asizeof
import gc


# which timings should we compute?
# set to 1 if we should compute it, otherwise 0
(gq, schnorr, okamoto, shoup, sw) = (1,0,0,1,1)

# The messagesizes which will be tested
messagesizes = range(250, 4001, 250)
# messagesizes = range(300, 501, 50)
# The number of runs per messagesize
runs = 10

if gq:
    gqtimings = {'keygen': [],
               'encode': [],
               'genchallenge': [],
               'genproof': [],
               'verify': []}

if schnorr:
    schnorrtimings = {'keygen': [],
               'encode': [],
               'genchallenge': [],
               'genproof': [],
               'verify': []}

if okamoto:
    okamototimings = {'keygen': [],
               'encode': [],
               'genchallenge': [],
               'genproof': [],
               'verify': []}

if shoup:
    shouptimings = {'keygen': [],
               'encode': [],
               'genchallenge': [],
               'genproof': [],
               'verify': []}

if sw:
    swtimings = {'keygen': [],
               'encode': [],
               'genchallenge': [],
               'genproof': [],
               'verify': []}

for i in range(len(messagesizes)):
    print("Running PoR on messagesize " + str(messagesizes[i]) + " from " + str(list(messagesizes)))
    if gq:
        gqtimings['keygen'].append([])
        gqtimings['encode'].append([])
        gqtimings['genchallenge'].append([])
        gqtimings['genproof'].append([])
        gqtimings['verify'].append([])

    if schnorr:
        schnorrtimings['keygen'].append([])
        schnorrtimings['encode'].append([])
        schnorrtimings['genchallenge'].append([])
        schnorrtimings['genproof'].append([])
        schnorrtimings['verify'].append([])

    if okamoto:
        okamototimings['keygen'].append([])
        okamototimings['encode'].append([])
        okamototimings['genchallenge'].append([])
        okamototimings['genproof'].append([])
        okamototimings['verify'].append([])


    if shoup:
        shouptimings['keygen'].append([])
        shouptimings['encode'].append([])
        shouptimings['genchallenge'].append([])
        shouptimings['genproof'].append([])
        shouptimings['verify'].append([])

    if sw:
        swtimings['keygen'].append([])
        swtimings['encode'].append([])
        swtimings['genchallenge'].append([])
        swtimings['genproof'].append([])
        swtimings['verify'].append([])

    for run in range(runs):
        data = os.urandom(messagesizes[i]*1024)

        # GQProofOfRetrievability
        if gq:
            print("Computing GQProofOfRetrievability")
            time_pre = time.time()
            (pk, sk) = GQProofOfRetrievability.keygen()
            time_post = time.time()
            duration = time_post - time_pre
            gqtimings['keygen'][i].append(duration)

            time_pre = time.time()
            (mij, authenticators, filehandle) = GQProofOfRetrievability.encode(sk, pk, data)
            time_post = time.time()
            duration = time_post - time_pre
            gqtimings['encode'][i].append(duration)

            time_pre = time.time()
            challenge = os.urandom(32)
            time_post = time.time()
            duration = time_post - time_pre
            gqtimings['genchallenge'][i].append(duration)

            time_pre = time.time()
            proof = GQProofOfRetrievability.genproof(pk, data, authenticators, challenge)
            time_post = time.time()
            duration = time_post - time_pre
            gqtimings['genproof'][i].append(duration)

            time_pre = time.time()
            a = GQProofOfRetrievability.verify(proof, pk, challenge, filehandle)
            time_post = time.time()
            duration = time_post - time_pre
            gqtimings['verify'][i].append(duration)

        # SchnorrProofOfRetrievability
        if schnorr:
            print("Computing SchnorrProofOfRetrievability")
            time_pre = time.time()
            (pk, sk) = SchnorrProofOfRetrievability.keygen()
            time_post = time.time()
            duration = time_post - time_pre
            schnorrtimings['keygen'][i].append(duration)

            time_pre = time.time()
            (mij, authenticators, filehandle) = SchnorrProofOfRetrievability.encode(sk, pk, data)
            time_post = time.time()
            duration = time_post - time_pre
            schnorrtimings['encode'][i].append(duration)

            time_pre = time.time()
            challenge = os.urandom(32)
            time_post = time.time()
            duration = time_post - time_pre
            schnorrtimings['genchallenge'][i].append(duration)

            time_pre = time.time()
            proof = SchnorrProofOfRetrievability.genproof(pk, data, authenticators, challenge)
            time_post = time.time()
            duration = time_post - time_pre
            schnorrtimings['genproof'][i].append(duration)

            time_pre = time.time()
            a = SchnorrProofOfRetrievability.verify(proof, pk, challenge, filehandle)
            time_post = time.time()
            duration = time_post - time_pre
            schnorrtimings['verify'][i].append(duration)

        # OkamotoProofOfRetrievability
        if okamoto:
            print("Computing OkamotoProofOfRetrievability")
            time_pre = time.time()
            (pk, sk) = OkamotoProofOfRetrievability.keygen()
            time_post = time.time()
            duration = time_post - time_pre
            okamototimings['keygen'][i].append(duration)

            time_pre = time.time()
            (mij, authenticators, filehandle) = OkamotoProofOfRetrievability.encode(sk, pk, data)
            time_post = time.time()
            duration = time_post - time_pre
            okamototimings['encode'][i].append(duration)

            time_pre = time.time()
            challenge = os.urandom(32)
            time_post = time.time()
            duration = time_post - time_pre
            okamototimings['genchallenge'][i].append(duration)

            time_pre = time.time()
            proof = OkamotoProofOfRetrievability.genproof(pk, data, authenticators, challenge)
            time_post = time.time()
            duration = time_post - time_pre
            okamototimings['genproof'][i].append(duration)

            time_pre = time.time()
            a = OkamotoProofOfRetrievability.verify(proof, pk, challenge, filehandle)
            time_post = time.time()
            duration = time_post - time_pre
            okamototimings['verify'][i].append(duration)

        # ShoupProofOfRetrievability
        if shoup:
            print("Computing ShoupProofOfRetrievability")
            time_pre = time.time()
            (pk, sk) = ShoupProofOfRetrievability.keygen()
            time_post = time.time()
            duration = time_post - time_pre
            shouptimings['keygen'][i].append(duration)

            time_pre = time.time()
            (mij, authenticators, filehandle) = ShoupProofOfRetrievability.encode(sk, pk, data)
            time_post = time.time()
            duration = time_post - time_pre
            shouptimings['encode'][i].append(duration)

            time_pre = time.time()
            challenge = os.urandom(32)
            time_post = time.time()
            duration = time_post - time_pre
            shouptimings['genchallenge'][i].append(duration)

            time_pre = time.time()
            proof = ShoupProofOfRetrievability.genproof(pk, data, authenticators, challenge)
            time_post = time.time()
            duration = time_post - time_pre
            shouptimings['genproof'][i].append(duration)

            time_pre = time.time()
            a = ShoupProofOfRetrievability.verify(proof, pk, challenge, filehandle)
            time_post = time.time()
            duration = time_post - time_pre
            shouptimings['verify'][i].append(duration)

        # SWProofOfRetrievability
        if sw:
            print("Computing SWProofOfRetrievability")
            time_pre = time.time()
            (pk, sk) = SWProofOfRetrievability.keygen()
            time_post = time.time()
            duration = time_post - time_pre
            swtimings['keygen'][i].append(duration)

            time_pre = time.time()
            (mij, authenticators, filehandle) = SWProofOfRetrievability.encode(sk, pk, data)
            time_post = time.time()
            duration = time_post - time_pre
            swtimings['encode'][i].append(duration)

            time_pre = time.time()
            challenge = os.urandom(32)
            time_post = time.time()
            duration = time_post - time_pre
            swtimings['genchallenge'][i].append(duration)

            time_pre = time.time()
            proof = SWProofOfRetrievability.genproof(pk, data, authenticators, challenge)
            time_post = time.time()
            duration = time_post - time_pre
            swtimings['genproof'][i].append(duration)

            time_pre = time.time()
            a = SWProofOfRetrievability.verify(proof, pk, challenge, filehandle)
            time_post = time.time()
            duration = time_post - time_pre
            swtimings['verify'][i].append(duration)

    # Save the data in complicated JSON-format
    if gq:
        with open('timings_GQPoR.json', 'w') as f:
            json_obj = jsonpickle.encode(gqtimings)
            f.write(json_obj)
    if schnorr:
        with open('timings_SchnorrPoR.json', 'w') as f:
            json_obj = jsonpickle.encode(schnorrtimings)
            f.write(json_obj)
    if okamoto:
        with open('timings_OkamotoPoR.json', 'w') as f:
            json_obj = jsonpickle.encode(okamototimings)
            f.write(json_obj)
    if shoup:
        with open('timings_ShoupPoR.json', 'w') as f:
            json_obj = jsonpickle.encode(shouptimings)
            f.write(json_obj)
    if sw:
        with open('timings_SWPoR.json', 'w') as f:
            json_obj = jsonpickle.encode(swtimings)
            f.write(json_obj)

print("Running postprocessing steps")

# Transform to handy Dataframes
for algo in ['keygen', 'encode', 'genchallenge', 'genproof', 'verify']:
    if gq:
        gqtimings[algo] = pd.DataFrame(gqtimings[algo]).T
        gqtimings[algo].columns = messagesizes
    if schnorr:
        schnorrtimings[algo] = pd.DataFrame(schnorrtimings[algo]).T
        schnorrtimings[algo].columns = messagesizes
    if okamoto:
        okamototimings[algo] = pd.DataFrame(okamototimings[algo]).T
        okamototimings[algo].columns = messagesizes
    if shoup:
        shouptimings[algo] = pd.DataFrame(shouptimings[algo]).T
        shouptimings[algo].columns = messagesizes
    if sw:
        swtimings[algo] = pd.DataFrame(swtimings[algo]).T
        swtimings[algo].columns = messagesizes

for algo in ['keygen', 'encode', 'genchallenge', 'genproof', 'verify']:
    # Save the data in handy .csv
    if gq:
        gqtimings[algo].to_csv('timings_GQPoR_'+str(algo)+'.csv')
    if schnorr:
        schnorrtimings[algo].to_csv('timings_SchnorrPoR_'+str(algo)+'.csv')
    if okamoto:
        okamototimings[algo].to_csv('timings_OkamotoPoR_'+str(algo)+'.csv')
    if shoup:
        shouptimings[algo].to_csv('timings_ShoupPoR_'+str(algo)+'.csv')
    if sw:
        swtimings[algo].to_csv('timings_SWPoR_'+str(algo)+'.csv')

    # GQ
    if gq:
        # Set up the plot
        plt.figure()
        plt.rc('text', usetex=True)
        plt.rc('font', family='serif')
        plt.xlabel('Filesize in Kb')
        plt.ylabel('Time in sec')
        plt.title('Time Measurements for ' + str(algo))
        # Plot the values
        gqtimings[algo].boxplot()
        plt.legend(loc='upper left')
        # Save the figure
        plt.savefig('timings_GQPoR_'+str(algo)+'.png')

    # Schnorr
    if schnorr:
        # Set up the plot
        plt.figure()
        plt.rc('text', usetex=True)
        plt.rc('font', family='serif')
        plt.xlabel('Filesize in Kb')
        plt.ylabel('Time in sec')
        plt.title('Time Measurements for ' + str(algo))
        # Plot the values
        schnorrtimings[algo].boxplot()
        plt.legend(loc='upper left')
        # Save the figure
        plt.savefig('timings_SchnorrPoR_'+str(algo)+'.png')

    # Okamoto
    if okamoto:
        # Set up the plot
        plt.figure()
        plt.rc('text', usetex=True)
        plt.rc('font', family='serif')
        plt.xlabel('Filesize in Kb')
        plt.ylabel('Time in sec')
        plt.title('Time Measurements for ' + str(algo))
        # Plot the values
        okamototimings[algo].boxplot()
        plt.legend(loc='upper left')
        # Save the figure
        plt.savefig('timings_OkamotoPoR_'+str(algo)+'.png')

    # Shoup
    if shoup:
        # Set up the plot
        plt.figure()
        plt.rc('text', usetex=True)
        plt.rc('font', family='serif')
        plt.xlabel('Filesize in Kb')
        plt.ylabel('Time in sec')
        plt.title('Time Measurements for ' + str(algo))
        # Plot the values
        shouptimings[algo].boxplot()
        plt.legend(loc='upper left')
        # Save the figure
        plt.savefig('timings_ShoupPoR_'+str(algo)+'.png')

    # SW
    if sw:
        # Set up the plot
        plt.figure()
        plt.rc('text', usetex=True)
        plt.rc('font', family='serif')
        plt.xlabel('Filesize in Kb')
        plt.ylabel('Time in sec')
        plt.title('Time Measurements for ' + str(algo))
        # Plot the values
        swtimings[algo].boxplot()
        plt.legend(loc='upper left')
        # Save the figure
        plt.savefig('timings_SWPoR_'+str(algo)+'.png')


# GQ
if gq:
    # Comparison between the average times of all of them
    plt.figure()
    plt.rc('text', usetex=True)
    plt.rc('font', family='serif')
    plt.xlabel('Filesize in Kb')
    plt.ylabel('Time in sec')
    plt.title('Time Measurements for the Proof of Retrievability')
    # Build a DataFrame with all the timing data
    df = pd.DataFrame([gqtimings[key].mean() for key in gqtimings.keys()], index=gqtimings.keys())
    df = df.transpose()
    # plot it
    df.keygen.plot(style='bo')
    df.verify.plot(style='gv')
    df.genchallenge.plot(style='r^')
    df.genproof.plot(style='c>')
    df.encode.plot(style='m<')

    plt.legend(loc='upper left')
    plt.savefig('timings_GQPoR_all.png')

# Schnorr
if schnorr:
    # Comparison between the average times of all of them
    plt.figure()
    plt.rc('text', usetex=True)
    plt.rc('font', family='serif')
    plt.xlabel('Filesize in Kb')
    plt.ylabel('Time in sec')
    plt.title('Time Measurements for the Proof of Retrievability')
    # Build a DataFrame with all the timing data
    df = pd.DataFrame([schnorrtimings[key].mean() for key in schnorrtimings.keys()], index=schnorrtimings.keys())
    df = df.transpose()
    # plot it
    df.keygen.plot(style='bo')
    df.verify.plot(style='gv')
    df.genchallenge.plot(style='r^')
    df.genproof.plot(style='c>')
    df.encode.plot(style='m<')

    plt.legend(loc='upper left')
    plt.savefig('timings_SchnorrPoR_all.png')

# Okamoto
if okamoto:
    # Comparison between the average times of all of them
    plt.figure()
    plt.rc('text', usetex=True)
    plt.rc('font', family='serif')
    plt.xlabel('Filesize in Kb')
    plt.ylabel('Time in sec')
    plt.title('Time Measurements for the Proof of Retrievability')
    # Build a DataFrame with all the timing data
    df = pd.DataFrame([okamototimings[key].mean() for key in okamototimings.keys()], index=okamototimings.keys())
    df = df.transpose()
    # plot it
    df.keygen.plot(style='bo')
    df.verify.plot(style='gv')
    df.genchallenge.plot(style='r^')
    df.genproof.plot(style='c>')
    df.encode.plot(style='m<')

    plt.legend(loc='upper left')
    plt.savefig('timings_OkamotoPoR_all.png')

# Shoup
if shoup:
    # Comparison between the average times of all of them
    plt.figure()
    plt.rc('text', usetex=True)
    plt.rc('font', family='serif')
    plt.xlabel('Filesize in Kb')
    plt.ylabel('Time in sec')
    plt.title('Time Measurements for the Proof of Retrievability')
    # Build a DataFrame with all the timing data
    df = pd.DataFrame([shouptimings[key].mean() for key in shouptimings.keys()], index=shouptimings.keys())
    df = df.transpose()
    # plot it
    df.keygen.plot(style='bo')
    df.verify.plot(style='gv')
    df.genchallenge.plot(style='r^')
    df.genproof.plot(style='c>')
    df.encode.plot(style='m<')

    plt.legend(loc='upper left')
    plt.savefig('timings_ShoupPoR_all.png')

# SW
if sw:
    # Comparison between the average times of all of them
    plt.figure()
    plt.rc('text', usetex=True)
    plt.rc('font', family='serif')
    plt.xlabel('Filesize in Kb')
    plt.ylabel('Time in sec')
    plt.title('Time Measurements for the Proof of Retrievability')
    # Build a DataFrame with all the timing data
    df = pd.DataFrame([swtimings[key].mean() for key in swtimings.keys()], index=swtimings.keys())
    df = df.transpose()
    # plot it
    df.keygen.plot(style='bo')
    df.verify.plot(style='gv')
    df.genchallenge.plot(style='r^')
    df.genproof.plot(style='c>')
    df.encode.plot(style='m<')

    plt.legend(loc='upper left')
    plt.savefig('timings_SWPoR_all.png')

import pandas as pd
import numpy as np
import os
import time
import datetime
import math
from htm.bindings.sdr import SDR, Metrics
from htm.encoders.rdse import RDSE, RDSE_Parameters
from htm.encoders.date import DateEncoder
from htm.bindings.algorithms import SpatialPooler
from htm.bindings.algorithms import TemporalMemory
from htm.algorithms.anomaly_likelihood import AnomalyLikelihood
from htm.bindings.algorithms import Predictor

def building_htm(len_data):
    global enc_info
    global sp_info
    global tm_info
    global anomaly_history
    global predictor
    global predictor_resolution
    global tm
    global sp
    global scalarEncoder
    global encodingWidth
    global dateEncoder

    # Initial message
    print("Building HTM for predicting trends...")

    # Default parameters in HTM
    default_parameters = {
        # there are 2 (3) encoders: "value" (RDSE) & "time" (DateTime weekend, timeOfDay)
        'enc': {
            "value" :
                {'resolution': 0.88, 'size': 700, 'sparsity': 0.02},
            "time": 
                {'timeOfDay': (30, 1)} #, 'weekend': 21}
        },
        'predictor': {'sdrc_alpha': 0.1},
        'sp': {'boostStrength': 3.0,
                'columnCount': 1638,
                'localAreaDensity': 0.04395604395604396,
                'potentialPct': 0.85,
                'synPermActiveInc': 0.04,
                'synPermConnected': 0.13999999999999999,
                'synPermInactiveDec': 0.006},
        'tm': {'activationThreshold': 17,
                'cellsPerColumn': 13,
                'initialPerm': 0.21,
                'maxSegmentsPerCell': 128,
                'maxSynapsesPerSegment': 64,
                'minThreshold': 10,
                'newSynapseCount': 32,
                'permanenceDec': 0.1,
                'permanenceInc': 0.1},
        'anomaly': {
        'likelihood': 
            {'probationaryPct': 0.1,
                'reestimationPeriod': 100}
        }
    }

    # Make the encoder
    print("- Make the encoder")
    dateEncoder = DateEncoder(timeOfDay= default_parameters["enc"]["time"]["timeOfDay"])
    scalarEncoderParams             = RDSE_Parameters()
    scalarEncoderParams.size        = default_parameters["enc"]["value"]["size"]
    scalarEncoderParams.sparsity    = default_parameters["enc"]["value"]["sparsity"]
    scalarEncoderParams.resolution  = default_parameters["enc"]["value"]["resolution"]
    scalarEncoder = RDSE( scalarEncoderParams )
    encodingWidth = (dateEncoder.size + scalarEncoder.size)
    enc_info = Metrics( [encodingWidth], 999999999)
    
    # Make the SP
    print("- Make the SP")
    spParams = default_parameters["sp"]
    sp = SpatialPooler(
        inputDimensions            = (encodingWidth,),
        columnDimensions           = (spParams["columnCount"],),
        potentialPct               = spParams["potentialPct"],
        potentialRadius            = encodingWidth,
        globalInhibition           = True,
        localAreaDensity           = spParams["localAreaDensity"],
        synPermInactiveDec         = spParams["synPermInactiveDec"],
        synPermActiveInc           = spParams["synPermActiveInc"],
        synPermConnected           = spParams["synPermConnected"],
        boostStrength              = spParams["boostStrength"],
        wrapAround                 = True
    )
    sp_info = Metrics( sp.getColumnDimensions(), 999999999 )

    # Temporal Memory Parameters
    print("- Make the TM")
    tmParams = default_parameters["tm"]
    tm = TemporalMemory(
        columnDimensions          = (spParams["columnCount"],),
        cellsPerColumn            = tmParams["cellsPerColumn"],
        activationThreshold       = tmParams["activationThreshold"],
        initialPermanence         = tmParams["initialPerm"],
        connectedPermanence       = spParams["synPermConnected"],
        minThreshold              = tmParams["minThreshold"],
        maxNewSynapseCount        = tmParams["newSynapseCount"],
        permanenceIncrement       = tmParams["permanenceInc"],
        permanenceDecrement       = tmParams["permanenceDec"],
        predictedSegmentDecrement = 0.0,
        maxSegmentsPerCell        = tmParams["maxSegmentsPerCell"],
        maxSynapsesPerSegment     = tmParams["maxSynapsesPerSegment"]
    )
    tm_info = Metrics( [tm.numberOfCells()], 999999999 )

    # Setup Likelihood
    print("- Make Anomaly Score/Likelihood")
    anParams           = default_parameters["anomaly"]["likelihood"]
    probationaryPeriod = int(math.floor(float(anParams["probationaryPct"])*len_data))
    learningPeriod     = int(math.floor(probationaryPeriod / 2.0))
    anomaly_history    = AnomalyLikelihood(learningPeriod= learningPeriod,
                                        estimationSamples= probationaryPeriod - learningPeriod,
                                        reestimationPeriod= anParams["reestimationPeriod"])

    # Make predictor
    print("- Make the predictor")
    predictor = Predictor( steps=[1, 5], alpha=default_parameters["predictor"]['sdrc_alpha'] )
    predictor_resolution = 1
    
    # End message
    print("Finish the building of HTM")

# Define function to get the CPU, RAM and Networking status
def get_resources_values():
    # Get date in epoch Time
    date_end = int(time.time())
    date_end = time.localtime(date_end)
    if date_end.tm_sec >= 0 and date_end.tm_sec <=30:   # Convert seconds to a valid interval in Grafana
        date_sec = 0
    else:
        date_sec = 30
    date_end = list(date_end)
    date_end[5] = date_sec
    date_end = tuple(date_end)
    date_end = int(time.mktime(date_end))   # To epoch time
    date_start = date_end - 300   # Five minutes before
    # Used CPU in %
    get_cpu_usage = "curl -u admin:orion -sb -H \"Accept: application/json\" \"http://10.80.81.189:3000/api/datasources/proxy/1/api/v1/query_range?query=sum%20by%20(mode)(irate(node_cpu_seconds_total%7Bmode%3D%27idle%27%2Cinstance%3D%2210.80.81.165%3A9100%22%2Cjob%3D%22openstack%22%7D%5B5m%5D))%20*%20100&start="+str(date_start)+"&end="+str(date_end)+"&step=30\" | jq -r \'.data.result[].values[-1][1]\'"
    # Free RAM in Bytes
    get_ram_free = "curl -u admin:orion -sb -H \"Accept: application/json\" \"http://10.80.81.189:3000/api/datasources/proxy/1/api/v1/query_range?query=node_memory_MemFree_bytes%7Binstance%3D%2210.80.81.165%3A9100%22%2Cjob%3D%22openstack%22%7D&start="+str(date_start)+"&end="+str(date_end)+"&step=30\" | jq -r \'.data.result[].values[-1][1]\'"
    get_ram_total = 4141236224  # 4 GiB Memory
    # Transmitted rate (bps) in network
    get_network_usage = "curl -u admin:orion -sb -H \"Accept: application/json\" \"http://10.80.81.189:3000/api/datasources/proxy/1/api/v1/query_range?query=irate(node_network_transmit_bytes_total%7Binstance%3D%2210.80.81.165%3A9100%22%2Cjob%3D%22openstack%22%7D%5B5m%5D)*8&start="+str(date_start)+"&end="+str(date_end)+"&step=30\" | jq -r \'.data.result[].values[-1][1]\'"
    # Resources status
    cpu_usage = 100 - float(os.popen(get_cpu_usage).read())
    ram_usage = 100 * (float(get_ram_total) - float(os.popen(get_ram_free).read()))/float(get_ram_total)
    thrgpt_usage = os.popen(get_network_usage).read()
    # Return values
    return cpu_usage, ram_usage, thrgpt_usage

def cpu_algorithm(cpu_usage,n_instances):
    global threshold_cpu_max
    global threshold_cpu_min
    global predictions
    global anomaly
    global anomalyProb

    threshold_cpu_max = 95
    threshold_cpu_min = 5
    predictions = {1: [], 5: []}
    anomaly     = []
    anomalyProb = []

    # Auto-scaling Algorithm for CPU values
    consumptionBits = scalarEncoder.encode(cpu_usage)

    # Concatenate all these encodings into one large encoding for Spatial Pooling.
    encoding = SDR( encodingWidth ).concatenate([consumptionBits, dateBits])
    enc_info.addData( encoding )

    # Create an SDR to represent active columns, This will be populated by the
    # compute method below. It must have the same dimensions as the Spatial Pooler.
    activeColumns = SDR( sp.getColumnDimensions() )

    # Execute Spatial Pooling algorithm over input space.
    sp.compute(encoding, True, activeColumns)
    sp_info.addData( activeColumns )

    # Execute Temporal Memory algorithm over active mini-columns.
    tm.compute(activeColumns, learn=True)
    tm_info.addData( tm.getActiveCells().flatten() )

    # Predict what will happen, and then train the predictor based on what just happened.
    pdf = predictor.infer( tm.getActiveCells() )
    for n in (1, 5):
        if pdf[n]:
            predictions[n].append( np.argmax( pdf[n] ) * predictor_resolution )
        else:
            predictions[n].append(float('nan'))

    # Compute Anomaly Likelihood
    anomalyLikelihood = anomaly_history.anomalyProbability( cpu_usage, tm.anomaly )
    anomaly.append( tm.anomaly )
    anomalyProb.append( float(2*(1-anomalyLikelihood)) )

    # Learning
    predictor.learn(count, tm.getActiveCells(), int( cpu_usage / predictor_resolution))

    # Algorithm
    pd_cpu_usage = float(predictions[1][-1])
    print("cpu_usage is:", cpu_usage)
    print("pd_cpu_usage is:", pd_cpu_usage)
    if (cpu_usage > threshold_cpu_max) and (n_instances == 1):
        if (pd_cpu_usage > threshold_cpu_max):
            print("The system will saturate")
            os.system("sh ~/autoscaling/autoscale.sh")
            n_instances = n_instances + 1
        else:
            print("The system is beautiful!")
    
    # Return Prediction
    return pd_cpu_usage

# Define main global variables
def global_thresholds():
    print("Define main Global Variables for autoscaling...")
    global threshold_ram_max
    global threshold_ram_min
    threshold_ram_max = 80
    threshold_ram_min = 5
    print("Global variables have already been defined!")

def stress_server(data):
    # Initial Message
    print("Come to stress the server...")
    
    # Variables
    global dateBits
    global count
    global n_instances

    inputs      = []
    count       = 0
    n_instances = 1
    pd_cpu_usage = 0
    pd_ram_usage = 0
    pd_thrgpt_usage = 0
    thrgpt_usage = []
    server_ep   = "http://10.80.81.165/"
    for index, row in data.iterrows():
        # Use count control variable
        count = count + 1

        # Control Message
        print("####################")
        print("ITERATION NUMBER: ", count)
        print("####################")
        
        # Convert date string into Python date object. # 2020-06-01 00:15:00
        dateString = datetime.datetime.strptime(str(index), "%Y-%m-%d %H:%M:%S")
        print("Process date: ", dateString)

        # Call the encoders to create bit representations for each value.  These are SDR objects.
        dateBits        = dateEncoder.encode(dateString)

        # Convert data value string into float.
        consumption = float(row[0])/1024
        inputs.append( consumption )

        # Get the row value in bytes.
        avg_bytes = row[0]*(1024**3)

        # Asume that a GET HTTP petition has a lenght of 500 bytes. So, how many requests are made per sample?
        length_httpget = 500   # In bytes.

        # rps (request per sample)
        rps = avg_bytes//length_httpget   # Integer part of division.

        # Asume only the 0.00001% of this rps for testing. For instance, a neighborhood in a big city. 
        # Consider that I not implemented a LB system, the else condition allow divide the load to the 
        # server as a load balancer system.
        if n_instances == 1:
            factor = 10
            rps = int(rps//(100000*factor))
        else:
            factor = 80
            rps = int(rps//(100000*factor))
        print("rps:", rps)
        
        # Use Apache Bench for stress the server
        if rps > 10000:
            command_cpu = "ab -n "+str(rps)+" -c 1000 "+str(server_ep)+" &"
        else:
            command_cpu = "ab -n "+str(rps)+" -c 100 "+str(server_ep)+" &"

        # Read resources values
        cpu_usage, ram_usage, thrgpt_usage_to_append =  get_resources_values()
        thrgpt_usage.append(thrgpt_usage_to_append)
        print("ram usage is:", ram_usage)
        print("throughput value is:", thrgpt_usage_to_append)

        # CPU Algorithm
        pd_cpu_usage = cpu_algorithm(cpu_usage,n_instances)
        
        # Sleep a 1/4500 elapse time.
        s = int(rps//4500)
        s_ram = s*1.0

        # Generate some stress test forever to original instance
        if n_instances == 1:
            stress_ram = "3G"
        else:
            stress_ram = "1G"

        # Execute the stress CPU, NIC and RAM test.
        os.system(command_cpu)
        os.system("ssh debian@172.16.101.10 'stress-ng --vm 1 --vm-bytes "+str(stress_ram)+" --timeout "+str(s_ram)+"' &")

        # Sleep for a time.
        if n_instances == 1:
            time.sleep(s)
            print("Sleep for:", s, "seconds")
        else:
            time.sleep(2*s)
            print("Sleep for:", 2*s, "seconds")
        
        print()

def main():
    data = pd.read_excel('../docs/files/Thesis_Real_Mobile_Data_DL_Traffic_202006.xlsx', index_col=0)
    building_htm(len(data))
    global_thresholds()
    stress_server(data)

if __name__ == "__main__":
    main()

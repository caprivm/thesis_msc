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
        # There are 2 (3) encoders: "value" (RDSE) & "time" (DateTime weekend, timeOfDay)
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
    print("- Finish the building of HTM!")

def get_resources_values():
    ##################################################################
    # GET DATE IN EPOCH TIME AND ADJUST TO A VALID INTERVAL IN GRAFANA
    ##################################################################
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
    date_start = date_end - 300             # Five minutes before

    ######################
    # GET RESOURCES VALUES
    ######################
    get_cpu_usage = "curl -u admin:orion -sb -H \"Accept: application/json\" \"http://10.80.81.189:3000/api/datasources/proxy/1/api/v1/query_range?query=sum%20by%20(mode)(irate(node_cpu_seconds_total%7Bmode%3D%27idle%27%2Cinstance%3D%2210.80.81.165%3A9100%22%2Cjob%3D%22openstack%22%7D%5B5m%5D))%20*%20100&start="+str(date_start)+"&end="+str(date_end)+"&step=30\" | jq -r \'.data.result[].values[-1][1]\'"
    get_ram_free = "curl -u admin:orion -sb -H \"Accept: application/json\" \"http://10.80.81.189:3000/api/datasources/proxy/1/api/v1/query_range?query=node_memory_MemFree_bytes%7Binstance%3D%2210.80.81.165%3A9100%22%2Cjob%3D%22openstack%22%7D&start="+str(date_start)+"&end="+str(date_end)+"&step=30\" | jq -r \'.data.result[].values[-1][1]\'"
    get_ram_total = 4141236224  
    get_network_usage = "curl -u admin:orion -sb -H \"Accept: application/json\" \"http://10.80.81.189:3000/api/datasources/proxy/1/api/v1/query_range?query=irate(node_network_transmit_bytes_total%7Binstance%3D%2210.80.81.165%3A9100%22%2Cjob%3D%22openstack%22%7D%5B5m%5D)*8&start="+str(date_start)+"&end="+str(date_end)+"&step=30\" | jq -r \'.data.result[].values[-1][1]\'"
    # Resources status
    cpu_usage = 100 - float(os.popen(get_cpu_usage).read())                                                 # Used CPU in percentage
    ram_usage = 100 * (float(get_ram_total) - float(os.popen(get_ram_free).read()))/float(get_ram_total)    # Free RAM in Bytes, consider 4 GiB Memory
    thrgpt_usage = os.popen(get_network_usage).read()                                                       # Transmitted rate (bps) in network

    return cpu_usage, ram_usage, thrgpt_usage

def cpu_algorithm(cpu_usage,n_instances):
    global threshold_cpu_max
    global threshold_cpu_min
    global predictions
    global anomaly
    global anomalyProb

    threshold_cpu_max = 95
    threshold_cpu_min = 5
    time_sleeping     = 30
    predictions = {1: [], 5: []}
    anomaly     = []
    anomalyProb = []

    ##############################
    # MAKE THE PREDICTION WITH HTM
    ##############################
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
    
    ###########################
    # ALGORITHM FOR AUTOSCALING
    ###########################
    pd_cpu_usage = float(predictions[1][-1])
    print("cpu_usage is:", cpu_usage)
    print("pd_cpu_usage is:", pd_cpu_usage)
    if (cpu_usage > threshold_cpu_max) and (n_instances == 1):
        if (pd_cpu_usage > threshold_cpu_max):
            print("The system will saturate")
            os.system("sh ~/autoscaling/autoscale.sh")
            n_instances = n_instances + 1
        else:
            time.sleep(time_sleeping)  # Sleep while new data is getting
            if (cpu_usage > threshold_cpu_max) and (n_instances == 1):
                print("Wrong prediction. The system will saturate.")
                os.system("sh ~/autoscaling/autoscale.sh")
                n_instances = n_instances + 1
            else:
                if (pd_cpu_usage > threshold_cpu_max):
                    time.sleep(time_sleeping)
                    if (cpu_usage > threshold_cpu_max) and (n_instances == 1):
                        print("Correct prediction. The system will saturate.")
                        os.system("sh ~/autoscaling/autoscale.sh")
                        n_instances = n_instances + 1
                    else:
                        time.sleep(time_sleeping)
                        print("The system it was not saturate.")
                else:
                    time.sleep(time_sleeping)
                    print("The system will not saturate.")
    else:
        if (cpu_usage < threshold_cpu_min):
            if (pd_cpu_usage < threshold_cpu_min):
                if (n_instances == 1):
                    print("Instances cannot be deleted. It is suggested to reduce the resources of the instance.")
                else:
                    print("The system will be oversized.")
                    os.system("sh ~/autoscaling/autoreduce.sh")
                    n_instances = n_instances - 1
            else:
                time.sleep(time_sleeping)
                if (cpu_usage < threshold_cpu_min):
                    if (n_instances == 1):
                        print("Instances cannot be deleted. It is suggested to reduce the resources of the instance.")
                    else:
                        print("The system will be oversized.")
                        os.system("sh ~/autoscaling/autoreduce.sh")
                        n_instances = n_instances - 1
                else:
                    if (pd_cpu_usage < threshold_cpu_min):
                        time.sleep(time_sleeping)
                        if (cpu_usage < threshold_cpu_min):
                            if (n_instances == 1):
                                print("Instances cannot be deleted. It is suggested to reduce the resources of the instance.")
                            else:
                                print("The system will be oversized.")
                                os.system("sh ~/autoscaling/autoreduce.sh")
                                n_instances = n_instances - 1
                        else:
                            time.sleep(time_sleeping)
                            print("The system no will be oversized.")
                    else:
                        time.sleep(time_sleeping)
                        print("The system no will be oversized.")
        else:
            if (pd_cpu_usage > threshold_cpu_max) or (pd_cpu_usage < threshold_cpu_min):
                time.sleep(time_sleeping)
                print("The system may exceed any of the thresholds.")
            else:
                time.sleep(time_sleeping)
                print("Maintains normal behavior.")
    
    return pd_cpu_usage

""" def ram_algorithm(ram_usage,n_instances):
    global threshold_ram_max
    global threshold_ram_min
    global predictions
    global anomaly
    global anomalyProb

    threshold_ram_max = 80
    threshold_ram_min = 5
    time_sleeping     = 30
    predictions = {1: [], 5: []}
    anomaly     = []
    anomalyProb = []

    ##############################
    # MAKE THE PREDICTION WITH HTM
    ##############################
    # Auto-scaling Algorithm for RAM values
    consumptionBits = scalarEncoder.encode(ram_usage)

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
    anomalyLikelihood = anomaly_history.anomalyProbability( ram_usage, tm.anomaly )
    anomaly.append( tm.anomaly )
    anomalyProb.append( float(2*(1-anomalyLikelihood)) )

    # Learning
    predictor.learn(count, tm.getActiveCells(), int( ram_usage / predictor_resolution))
    
    ###########################
    # ALGORITHM FOR AUTOSCALING
    ###########################
    pd_ram_usage = float(predictions[1][-1])
    print("ram_usage is:", ram_usage)
    print("pd_ram_usage is:", pd_ram_usage)
    if (ram_usage > threshold_ram_max) and (n_instances == 1):
        if (pd_ram_usage > threshold_ram_max):
            print("The system will saturate")
            os.system("sh ~/autoscaling/autoscale.sh")
            n_instances = n_instances + 1
        else:
            time.sleep(time_sleeping)  # Sleep while new data is getting
            if (ram_usage > threshold_ram_max) and (n_instances == 1):
                print("Wrong prediction. The system will saturate.")
                os.system("sh ~/autoscaling/autoscale.sh")
                n_instances = n_instances + 1
            else:
                if (pd_ram_usage > threshold_ram_max):
                    time.sleep(time_sleeping)
                    if (ram_usage > threshold_ram_max) and (n_instances == 1):
                        print("Correct prediction. The system will saturate.")
                        os.system("sh ~/autoscaling/autoscale.sh")
                        n_instances = n_instances + 1
                    else:
                        time.sleep(time_sleeping)
                        print("The system it was not saturate.")
                else:
                    time.sleep(time_sleeping)
                    print("The system will not saturate.")
    else:
        if (ram_usage < threshold_ram_min):
            if (pd_ram_usage < threshold_ram_min):
                if (n_instances == 1):
                    print("Instances cannot be deleted. It is suggested to reduce the resources of the instance.")
                else:
                    print("The system will be oversized.")
                    os.system("sh ~/autoscaling/autoreduce.sh")
                    n_instances = n_instances - 1
            else:
                time.sleep(time_sleeping)
                if (ram_usage < threshold_ram_min):
                    if (n_instances == 1):
                        print("Instances cannot be deleted. It is suggested to reduce the resources of the instance.")
                    else:
                        print("The system will be oversized.")
                        os.system("sh ~/autoscaling/autoreduce.sh")
                        n_instances = n_instances - 1
                else:
                    if (pd_ram_usage < threshold_ram_min):
                        time.sleep(time_sleeping)
                        if (ram_usage < threshold_ram_min):
                            if (n_instances == 1):
                                print("Instances cannot be deleted. It is suggested to reduce the resources of the instance.")
                            else:
                                print("The system will be oversized.")
                                os.system("sh ~/autoscaling/autoreduce.sh")
                                n_instances = n_instances - 1
                        else:
                            time.sleep(time_sleeping)
                            print("The system no will be oversized.")
                    else:
                        time.sleep(time_sleeping)
                        print("The system no will be oversized.")
        else:
            if (pd_ram_usage > threshold_ram_max) or (pd_ram_usage < threshold_ram_min):
                time.sleep(time_sleeping)
                print("The system may exceed any of the thresholds.")
            else:
                time.sleep(time_sleeping)
                print("Maintains normal behavior.")
    
    return pd_ram_usage """

""" def thrgpt_algorithm(thrgpt_usage, threshold_thrgpt_max, n_instances):
    global predictions
    global anomaly
    global anomalyProb

    time_sleeping     = 30
    predictions = {1: [], 5: []}
    anomaly     = []
    anomalyProb = []

    ##############################
    # MAKE THE PREDICTION WITH HTM
    ##############################
    # Auto-scaling Algorithm for THROUGHPUT values
    consumptionBits = scalarEncoder.encode(thrgpt_usage)

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
    anomalyLikelihood = anomaly_history.anomalyProbability( thrgpt_usage, tm.anomaly )
    anomaly.append( tm.anomaly )
    anomalyProb.append( float(2*(1-anomalyLikelihood)) )

    # Learning
    predictor.learn(count, tm.getActiveCells(), int( thrgpt_usage / predictor_resolution))
    
    ###########################
    # ALGORITHM FOR AUTOSCALING
    ###########################
    pd_thrgpt_usage = float(predictions[1][-1])
    print("thrgpt_usage is:", thrgpt_usage)
    print("pd_thrgpt_usage is:", pd_thrgpt_usage)
    if (thrgpt_usage > threshold_thrgpt_max) and (n_instances == 1):
        if (pd_thrgpt_usage > threshold_thrgpt_max):
            print("The system will saturate")
            os.system("sh ~/autoscaling/autoscale.sh")
            n_instances = n_instances + 1
        else:
            time.sleep(time_sleeping)  # Sleep while new data is getting
            if (thrgpt_usage > threshold_thrgpt_max) and (n_instances == 1):
                print("Wrong prediction. The system will saturate.")
                os.system("sh ~/autoscaling/autoscale.sh")
                n_instances = n_instances + 1
            else:
                if (pd_thrgpt_usage > threshold_thrgpt_max):
                    time.sleep(time_sleeping)
                    if (thrgpt_usage > threshold_thrgpt_max) and (n_instances == 1):
                        print("Correct prediction. The system will saturate.")
                        os.system("sh ~/autoscaling/autoscale.sh")
                        n_instances = n_instances + 1
                    else:
                        time.sleep(time_sleeping)
                        print("The system it was not saturate.")
                else:
                    time.sleep(time_sleeping)
                    print("The system will not saturate.")
    
    return pd_thrgpt_usage """

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
        dateBits = dateEncoder.encode(dateString)

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
        # Consider that I not implemented a LB system, the else condition allow divide the load to the server as a load balancer system.
        if n_instances == 1:
            factor = 10
            rps = int(rps//(100000*factor))
        else:
            factor = 100
            rps = int(rps//(100000*factor))
        print("rps:", rps)
        
        # Use Apache Bench for stress the server
        if rps > 10000:
            command_cpu = "ab -d -S -q -n "+str(rps)+" -c 1000 "+str(server_ep)+" &"
        else:
            command_cpu = "ab -d -S -q -n "+str(rps)+" -c 100 "+str(server_ep)+" &"

        # Read resources values
        cpu_usage, ram_usage, thrgpt_usage_to_append =  get_resources_values()
        thrgpt_usage.append(thrgpt_usage_to_append)

        # CPU, RAM and Throughput algorithm
        pd_cpu_usage = cpu_algorithm(cpu_usage, n_instances)
        # pd_ram_usage = ram_algorithm(ram_usage, n_instances)
        # pd_thrgpt_usage = thrgpt_algorithm(thrgpt_usage_to_append, np.percentile(thrgpt_usage, 95), n_instances)
        
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
        os.system("ssh debian@172.16.101.10 'stress-ng -q --vm 1 --vm-bytes "+str(stress_ram)+" --timeout "+str(s_ram)+"' &")

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
    stress_server(data)

if __name__ == "__main__":
    main()

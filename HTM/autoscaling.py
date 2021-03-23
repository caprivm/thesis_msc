import pandas as pd
import os
import time
import datetime

# Define variables
def stress_server():
    inputs      = []
    threshold_cpu_max = 95
    threshold_cpu_min = 5
    threshold_ram_max = 80
    threshold_ram_min = 5
    thrgpt_usage = []
    n_instances = 1
    server_ep   = "http://10.80.81.165/"
    data = pd.read_excel('../docs/files/Thesis_Real_Mobile_Data_DL_Traffic_202006.xlsx', index_col=0)
    for index, row in data.iterrows():
        
        # Convert date string into Python date object. # 2020-06-01 00:15:00
        dateString = datetime.datetime.strptime(str(index), "%Y-%m-%d %H:%M:%S")
        print(dateString)

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
            rps = int(rps//100000)
        else:
            factor = 8
            rps = int(rps//(100000*factor))
        print("rps:", rps)
        
        # Use Apache Bench for stress the server
        if rps > 10000:
            command_cpu = "ab -n "+str(rps)+" -c 1000 "+str(server_ep)+" &"
        else:
            command_cpu = "ab -n "+str(rps)+" -c 100 "+str(server_ep)+" &"
        
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
        date_end = int(time.mktime(date_end))
        date_start = date_end - 300   # Five minutes before
        print("CPU Analysis | date start is:", date_start, " date end is:", date_end)

        ## Get the CPU, RAM and Networking status
        # Used CPU in %
        get_cpu_usage = "curl -u admin:kCh22RK45cEyH4n -sb -H \"Accept: application/json\" \"http://10.80.81.218:3000/api/datasources/proxy/1/api/v1/query_range?query=sum%20by%20(mode)(irate(node_cpu_seconds_total%7Bmode%3D%27idle%27%2Cinstance%3D%2210.80.81.165%3A9100%22%2Cjob%3D%22openstack%22%7D%5B5m%5D))%20*%20100&start="+str(date_start)+"&end="+str(date_end)+"&step=30\" | jq -r \'.data.result[].values[-1][1]\'"
        # Free RAM in Bytes 
        get_ram_free = "curl -u admin:kCh22RK45cEyH4n -sb -H \"Accept: application/json\" \"http://10.80.81.218:3000/api/datasources/proxy/1/api/v1/query_range?query=node_memory_MemFree_bytes%7Binstance%3D%2210.80.81.165%3A9100%22%2Cjob%3D%22openstack%22%7D&start="+str(date_start)+"&end="+str(date_end)+"&step=30\" | jq -r \'.data.result[].values[-1][1]\'"
        get_ram_total = 4141236224
        # Transmitted rate (bps) in network
        get_network_usage = "curl -u admin:kCh22RK45cEyH4n -sb -H \"Accept: application/json\" \"http://10.80.81.218:3000/api/datasources/proxy/1/api/v1/query_range?query=irate(node_network_transmit_bytes_total%7Binstance%3D%2210.80.81.165%3A9100%22%2Cjob%3D%22openstack%22%7D%5B5m%5D)*8&start="+str(date_start)+"&end="+str(date_end)+"&step=30\" | jq -r \'.data.result[].values[-1][1]\'"

        # Resources status
        cpu_usage = 100 - float(os.popen(get_cpu_usage).read())
        ram_usage = 100 * (float(get_ram_total) - float(os.popen(get_ram_free).read()))/float(get_ram_total)
        thrgpt_usage.append( os.popen(get_network_usage).read() )
        print("cpu usage is:", cpu_usage)
        print("ram usage is:", ram_usage)
        print("throughput value is:", thrgpt_usage[-1])
        
        # Sleep a 1/4500 elapse time.
        s = int(rps//4500)
        s_ram = s*1.0
        if n_instances == 1:
            stress_ram = "3G"
        else:
            stress_ram = "1G"
        
        if (cpu_usage > threshold_cpu_max) and (n_instances == 1):
            os.system("sh ~/autoscaling/autoscale.sh")
            n_instances = n_instances + 1

        # Execute the stress CPU and NIC test.
        os.system(command_cpu)

        # Execute the stress RAM test.
        os.system("ssh debian@172.16.101.10 'stress-ng --vm 1 --vm-bytes "+str(stress_ram)+" --timeout "+str(s_ram)+"' &")

        # Sleep for a time.
        if n_instances == 1:
            time.sleep(s)
            print("Sleep for:", s, "seconds")
        else:
            time.sleep(2*s)
            print("Sleep for:", 2*s, "seconds")

def main():
    stress_server()

if __name__ == "__main__":
    main()

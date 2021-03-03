import pandas as pd
import os
import time
import datetime

# Definir variables
def stress_server():
    inputs      = []
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
        rps = int(rps//100000)
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

        # Get the CPU status
        cpu_command = "curl -u admin:kCh22RK45cEyH4n -sb -H \"Accept: application/json\" \"http://10.80.81.218:3000/api/datasources/proxy/1/api/v1/query_range?query=sum%20by%20(mode)(irate(node_cpu_seconds_total%7Bmode%3D%27idle%27%2Cinstance%3D%2210.80.81.165%3A9100%22%2Cjob%3D%22openstack%22%7D%5B5m%5D))%20*%20100&start="+str(date_start)+"&end="+str(date_end)+"&step=30\" | jq -r \'.data.result[].values[-1][1]\'"
        
        cpu_value = 100 - float(os.popen(cpu_command).read())
        print("cpu value is:", cpu_value)
        
        # Sleep a 1/4500 elapse time.
        s = int(rps//4500)
        s_ram = s*0.8

        # Execute the stress CPU test.
        os.system(command_cpu)

        # Execute the stress RAM test.
        os.system("ssh debian@172.16.101.5 'stress-ng --vm 1 --vm-bytes 3G --timeout "+str(s_ram)+"' &")

        # Sleep for a time.
        print("Sleep for:", s, "seconds")
        time.sleep(s)

def main():
    stress_server()

if __name__ == "__main__":
    main()

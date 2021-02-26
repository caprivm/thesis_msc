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

        if rps > 10000:
            command = "ab -n "+str(rps)+" -c 1000 "+str(server_ep)+""
        else:
            command = "ab -n "+str(rps)+" -c 100 "+str(server_ep)+""

        # Print the current time.
        print("t "+str(index))
        
        # Execute the stress test.
        os.system(command)
        
        # Sleep a 1/5000 elapse time.
        s = int(rps//5000)
        time.sleep(s)

def main():
    stress_server()

if __name__ == "__main__":
    main()

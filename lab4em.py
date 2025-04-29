# Import SDK packages
from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient
import time
import random
import json
import pandas as pd
import numpy as np
import os


#TODO 1: modify the following parameters
#Starting and end index, modify this
device_st = 0
device_end = 5

#Path to the dataset, modify this
data_path = os.path.join("iot_resources", "data", "vehicle{}.csv")
certificate_formatter = os.path.join("iot_resources", "certificates", "device_{}.pem")
key_formatter = os.path.join("iot_resources", "keys", "device_{}.private.pem")
root_ca_path = "AmazonRootCA1.pem"


iot_endpoint = "a1u83sicayovh8-ats.iot.us-east-1.amazonaws.com"  
topic = "vehicles/device7/data"


    
class MQTTClient:
    def __init__(self, device_id, cert, key):
        # For certificate based connection
        self.device_id = str(device_id)
        self.client = AWSIoTMQTTClient(self.device_id)
        self.client.configureEndpoint(iot_endpoint, 8883)
        self.client.configureCredentials(root_ca_path, key, cert)
        #TODO 2: modify your broker address
        self.client.configureOfflinePublishQueueing(-1)
        self.client.configureDrainingFrequency(2)
        self.client.configureConnectDisconnectTimeout(10)
        self.client.configureMQTTOperationTimeout(5)
        self.client.onMessage = self.customOnMessage
        

    def customOnMessage(self,message):
        #TODO 3: fill in the function to show your received message
        print(f"[Device {self.device_id}] Received message: {message.payload} on topic {message.topic}")


    # Suback callback
    def customSubackCallback(self,mid, data):
        #You don't need to write anything here
        pass


    # Puback callback
    def customPubackCallback(self,mid):
        #You don't need to write anything here
        pass


    def publish(self, topic="vehicle/emission/data"):
    # Load the vehicle's emission data
        df = pd.read_csv(data_path.format(self.device_id))
        for index, row in df.iterrows():
            # Create a JSON payload from the row data
            payload = json.dumps(row.to_dict())
            
            # Publish the payload to the specified topic
            print(f"Publishing: {payload} to {topic}")
            self.client.publishAsync(topic, payload, 0, ackCallback=self.customPubackCallback)
            
            # Sleep to simulate real-time data publishing
            time.sleep(1)

    def publish_custom(self, topic, message_dict):
        payload = json.dumps(message_dict)
        print(f"[Device {self.device_id}] Publishing custom message: {payload} to {topic}")
        self.client.publishAsync(topic, payload, 0, ackCallback=self.customPubackCallback)

            



print("Loading vehicle data...")
data = []
for i in range(device_st, device_end):
    # Assuming each device has a corresponding CSV file
    try:
        a = pd.read_csv(data_path.format(i))
        data.append(a)
    except FileNotFoundError:
        print(f"File {data_path.format(i)} not found.")
        data.append(None) 

print("Initializing MQTTClients...")
clients = []
for device_id in range(device_st, device_end):
    cert_path = certificate_formatter.format(device_id)
    key_path = key_formatter.format(device_id)
    if not os.path.exists(cert_path) or not os.path.exists(key_path):
        print(f"missing cert/key.")
        continue

    client = MQTTClient(device_id, cert_path, key_path)
    try:
        client.client.connect()
        print(f"Connected client {device_id}")
        clients.append(client)
    except Exception as e:
        print(f"Failed to connect {device_id}: {e}")

 
while True:
    print("Choose an action:\n  s - send data from CSV\n  c - send custom message\n  d - disconnect\n  any other key - exit")
    x = input().strip().lower()

    if x == "s":
        for client in clients:
            client.publish()

    elif x == "c":
        topic_input = input("Enter topic (or press enter to use default): ").strip()
        topic_to_use = topic_input if topic_input else topic

        key = input("Enter key: ")
        value = input("Enter value: ")

        custom_message = {key: value}

        for client in clients:
            client.publish_custom(topic_to_use, custom_message)

    elif x == "d":
        for client in clients:
            client.client.disconnect()
        print("clients disconnected.")
        break

    else:
        print("Exiting.")
        break

    time.sleep(3)






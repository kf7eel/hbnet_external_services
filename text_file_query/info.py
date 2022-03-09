# Basic example MQTT APP that will check text file for responses. For use with the HBNet Data Gateway
# More about the API used via MQTT can be found at https://github.com/kf7eel/hbnet_external_services/wiki
# If you are new to MQTT, I highle recommend that you read https://www.hivemq.com/mqtt-essentials/ to understand the principals of MQTT.
# Hope you can find this useful. - KF7EEL

# Text file is a Python dictionary. Each response has a key, for example: 'help' returns 'This is a help message.'

# Import needed modules
import paho.mqtt.client as mqtt
import threading
import json
import time
import random
# Used to read the text file containing queries
import os, ast


# Shortcut of APP. This is what users will have to type into radio, keep to about 5 characters.
# Shortcut must be unique on each server, please check to make sure that shortcut is not already in use.

app_shortcut = 'INFO'
# URL where users can go to find out about this APP
app_url = 'http://example.org'
# Brief description about APP
app_description = 'INFO will respond with information. :)'
# Contact email, so someone can contact you if there is a problem
app_contact = 'kf7eel@qsl.net'

# MQTT server details. Only data gateways connected to the same MQTT server will be able to use this wonderful script.
mqtt_server = 'mqtt.hbnet.xyz'
mqtt_port = 1883
mqtt_user = ''
mqtt_password = ''

# This is where we process incoming SMS messages. You can specify a response based on what the user sent, or run some code and then respond.
# It is a good idea to write a function to execute code, if you are going to be doing something with the received SMS.
def process_message(payload):
    # Turn JSON payload into Python dictionary
    dict_payload = json.loads(payload)
    # Create variables to shorten things...
    dmr_id = dict_payload['dmr_id']
    message = dict_payload['message']
    network = dict_payload['network']
    # Split the received message into a list, for example, "This is a test" becomes ['This', 'is', 'a', 'test']. This makes it easy to create commands with arguments.
    msg_split = message.split(' ')
    # Print for debugging, so you can see what is happening.
    print(msg_split)
    # Read queries text file
    q_data = ast.literal_eval(os.popen('cat ./queries.txt').read())
    # Add condition to respond to message with no characters.
    if '' == msg_split[0]:
        print('Received blank SMS, responding.')
        mqtt_reply(network, dmr_id, 'No input.')
    # Check to see if message is in the query list
    elif msg_split[0] in q_data.keys():
        print('Sending response.')
        mqtt_reply(network, dmr_id, q_data[msg_split[0]])
    # If not found, respond with error
    elif msg_split[0] not in q_data.keys():
        print('Sending response.')
        mqtt_reply(network, dmr_id, 'Not found.')
    
# Define MQTT instance. See https://pypi.org/project/paho-mqtt for more in depth info about module.
def mqtt_main(broker_url = 'localhost', broker_port = 1883):
    global mqtt_client
    # Define MQTT client with app name
    mqtt_client = mqtt.Client(client_id = app_shortcut + '-' + str(random.randint(1,99)))
    # On connect, send announcement
    def on_connect(client, userdata, flags, rc):
        mqtt_announce()
        print('Connected')
    def on_disconnect(client, userdata, flags, rc):
        print('Disconnected')

    # Process received msg here
    def on_message(client, userdata, message):
        topic_list = str(message.topic).split('/')
        print("Message Recieved: " + message.payload.decode())
        # Pass message payload into our function to process message.
        process_message(message.payload.decode())

    def mqtt_connect():
        # Pass MQTT server details to instrance
            
        if mqtt_user != '':
            print('MQTT User/Pass specified')
            mqtt_client.username_pw_set(mqtt_user, mqtt_password)
        mqtt_client.connect(broker_url, broker_port, keepalive = 30)


    # Last will and testament, this tells everyone that we are going offline.
    mqtt_client.will_set("ANNOUNCE", json.dumps({app_shortcut:"LOST_CONNECTION"}), 0, False)
    # Telling the MQTT instance what to do when these events happen.
    mqtt_client.on_message = on_message
    mqtt_client.on_connect = on_connect
    mqtt_client.on_disconnect = on_disconnect
    # Pass MQTT server details to instrance
    mqtt_connect()

    # Subscribe to topic for incoming messages. See https://github.com/kf7eel/hbnet_external_services/wiki for topic structure.
    mqtt_client.subscribe('APP/' + app_shortcut, qos=0)

    # Announcements for service/network discovery. Function that runs on a 5 minute loop.
    mqtt_client.loop_start()

# Function to reply to messages. Already formatted for your convenience.
def mqtt_reply(shortcut, dmr_id, message):
    mqtt_client.publish(topic="MSG/" + shortcut + '/' + str(dmr_id), payload=json.dumps({str(dmr_id):message, 'network':app_shortcut, 'sms_type':'unit'}, indent = 4), qos=0, retain=False)
    

def mqtt_announce():
    mqtt_client.publish(topic="ANNOUNCE", payload=json.dumps({'shortcut':app_shortcut, 'type': 'app', 'url':app_url, 'description':app_description, 'contact':app_contact}, indent = 4), qos=0, retain=False)

def mqtt_announce_loop(ann_time):
    while True:
        ann_time = ann_time * 60
        time.sleep(ann_time)
        mqtt_announce()
        

if __name__ == '__main__':
    
    # Start ANNOUNCE thread
    mqtt_thread = threading.Thread(target=mqtt_announce_loop, args=(5,))
    mqtt_thread.daemon = True
    mqtt_thread.start()
 
    mqtt_main(mqtt_server, mqtt_port)

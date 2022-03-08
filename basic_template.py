# Basic example MQTT APP template for use with the HBNet Data Gateway
# More about the API used via MQTT can be found at https://github.com/kf7eel/hbnet_external_services/wiki
# If you are new to MQTT, I highle recommend that you read https://www.hivemq.com/mqtt-essentials/ to understand the principals of MQTT.
# Hope you can find this useful. - KF7EEL

# Import needed modules
import paho.mqtt.client as mqtt
import threading
import json
import time

# Shortcut of APP. This is what users will have to type into radio, keep to about 5 characters.
app_shortcut = 'EXAMPLE'
# URL where users can go to find out about this APP
app_url = 'http://example.org'
# Brief description about APP
app_description = 'This is a cool radio project'

# MQTT server details. Only data gateways connected to the same MQTT server will be able to use this wonderful script.
mqtt_server = 'mqtt.hbnet.xyz'
mqtt_port = 1883


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
    # Add condition to respond to message with no characters.
    if '' == msg_split[0]:
        print('Received blank SMS, responding.')
        mqtt_reply(network, dmr_id, 'No input.')
    # If HI is in the message, respond with Hello there.
    elif 'HI' == msg_split[0]:
        print('Sending response.')
        mqtt_reply(network, dmr_id, 'Hello there.')
    
# Define MQTT instance. See https://pypi.org/project/paho-mqtt for more in depth info about module.
def mqtt_main(broker_url = 'localhost', broker_port = 1883):
    global mqtt_client
    mqtt_client = mqtt.Client()
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


    # Last will and testament, this tells everyone that we are going offline.
    mqtt_client.will_set("ANNOUNCE", json.dumps({app_shortcut:"LOST_CONNECTION"}), 0, False)
    # Telling the MQTT instance what to do when these events happen.
    mqtt_client.on_message = on_message
    mqtt_client.on_connect = on_connect
    mqtt_client.on_disconnect = on_disconnect
    # Pass MQTT server details to instrance
    mqtt_client.connect(broker_url, broker_port, keepalive = 10)

    # Subscribe to topic for incoming messages. See https://github.com/kf7eel/hbnet_external_services/wiki for topic structure.
    mqtt_client.subscribe('APP/' + app_shortcut, qos=0)

    # Announcements for service/network discovery. Function that runs on a 5 minute loop.
    mqtt_client.loop_start()

# Function to reply to messages. Already formatted for your convenience.
def mqtt_reply(shortcut, dmr_id, message):
    mqtt_client.publish(topic="MSG/" + shortcut + '/' + str(dmr_id), payload=json.dumps({str(dmr_id):message, 'network':app_shortcut}, indent = 4), qos=0, retain=False)
    

def mqtt_announce():
    mqtt_client.publish(topic="ANNOUNCE", payload=json.dumps({'shortcut':app_shortcut, 'type': 'app', 'url':app_url, 'description':app_description}, indent = 4), qos=0, retain=False)

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

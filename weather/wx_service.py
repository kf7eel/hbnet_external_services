# Basic example MQTT APP template for use with the HBNet Data Gateway
# More about the API used via MQTT can be found at https://github.com/kf7eel/hbnet_external_services/wiki
# If you are new to MQTT, I highle recommend that you read https://www.hivemq.com/mqtt-essentials/ to understand the principals of MQTT.
# Hope you can find this useful. - KF7EEL

# Import needed modules
import paho.mqtt.client as mqtt
import threading
import json
import time
import requests

###############################################################################################
# Shortcut of APP. This is what users will have to type into radio, keep to about 5 characters.
# Shortcut must be unique on each server, please check to make sure that shortcut is not already in use.
app_shortcut = 'MYWX'
# URL where users can go to find out about this APP
app_url = 'https://github.com/kf7eel/hbnet_external_services/wiki/Official-Community-Applications#wx---weather-service'
# Brief description about APP
app_description = 'Get current conditions for a city.'
# Contact email, so someone can contact you if there is a problem
app_contact = 'your@email.address'

# MQTT server details. Only data gateways connected to the same MQTT server will be able to use this wonderful script.
mqtt_server = 'mqtt.hbnet.xyz'
mqtt_port = 1883
mqtt_user = ''
mqtt_password = ''

# API key for OpenWeatherMap
owm_API_key = 'your API key'

#############################################################################################
# Weather class for OpenWeatherMap
class weather:
    '''Use open weather map for weather data'''
    def __init__(self):
        global owm_API_key
        self.api_url = 'http://api.openweathermap.org/data/2.5/'
        self.api_current = 'weather?'
        self.lat = 'lat='
        self.lon = '&lon='
        self.city = 'q='
        self.app_id = '&appid=' + owm_API_key + '&units=imperial'
        # return temp, pressure, wind, and wind dir

    def current_loc(self, lat, lon):
        url = self.api_url + self.api_current + self.lat + lat + self.lon + lon + self.app_id
        wx_data = requests.get(url).json()
        return wx_data['name'] , wx_data['sys']['country'], wx_data['weather'][0]['main'], wx_data['main']['temp'], wx_data['main']['pressure'], wx_data['wind']['speed'], wx_data['wind']['deg']
    def city_loc(self, city_name):
        url = self.api_url + self.api_current + self.city + city_name + self.app_id
        wx_data = requests.get(url).json()
        print(url)
        return wx_data['name'] , wx_data['sys']['country'], wx_data['weather'][0]['main'], wx_data['main']['temp'], wx_data['main']['pressure'], wx_data['wind']['speed'], wx_data['wind']['deg']
        




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
    arguments = ' '.join(msg_split)
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
    else:
        try:
            wx = weather().city_loc(arguments)
            sms_result = wx[0] + ', ' + wx[1] + '. ' + wx[2] + ', Temp: ' + str(wx[3]) + ' Pres: ' + str(wx[4]) + ' Wind Speed: ' + str(wx[5]) + ' Wind Dir: ' + str(wx[6])
            print(sms_result)
            mqtt_reply(network, dmr_id, sms_result)
        except:
            mqtt_reply(network, dmr_id, 'Error getting WX data.')
    
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
        if rc != 0:
            print("Unexpected disconnection.")
        try:
            mqtt_connect()
        except:
            print('Error')

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

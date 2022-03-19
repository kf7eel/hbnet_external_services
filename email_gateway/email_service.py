# Basic example MQTT APP template for use with the HBNet Data Gateway
# More about the API used via MQTT can be found at https://github.com/kf7eel/hbnet_external_services/wiki
# If you are new to MQTT, I highle recommend that you read https://www.hivemq.com/mqtt-essentials/ to understand the principals of MQTT.
# Hope you can find this useful. - KF7EEL

# Import needed modules
import paho.mqtt.client as mqtt
import threading
import json
import time
from pathlib import Path
import ast, os
from config import *
from imap_tools import MailBox, AND
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText



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
    elif 'REGISTER' == msg_split[0].upper():
        print('Sending response.')
        add_user(dmr_id, network)
        mqtt_reply(network, dmr_id, 'Registered. You may now send/receive emails.')
    elif 'MSG' == msg_split[0].upper():
        if registered(dmr_id):
            for i in get_messages(dmr_id):
                mqtt_reply(network, dmr_id, i)
        else:
            mqtt_reply(network, dmr_id, 'Not registered. Please register before getting emails.')
    # @ detected in first argument, assuming email needs to be sent
    elif '@' in msg_split[0].upper():
        print('need to werite module')
        send_email(msg_split[0], dmr_id, message)
    
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
        if message.topic == 'ANNOUNCE/MQTT':
            print('--------------------------------\nServer message:\n')
            print(message.payload.decode())
            print('\n--------------------------------')
        else:
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

def registered(dmr_id):
    registered_users = ast.literal_eval(os.popen('cat ./registered_users.txt').read())
    if dmr_id in registered_users.keys():
        return True
    else:
        return False
    
def add_user(dmr_id, network):
    registered_users = ast.literal_eval(os.popen('cat ./registered_users.txt').read())
    registered_users[dmr_id] = {'network': network}
    with open('./registered_users.txt', 'w') as reg_file:
        reg_file.write(str(registered_users))
        reg_file.close()
        
def get_messages(dmr_id):
    dmr_id = int(dmr_id)
    snd_que = []
    print('Retreiving messages')
    waiting_msg = ast.literal_eval(os.popen('cat ././waiting_messages.txt').read())
    for m in waiting_msg[dmr_id]:
        print(m)
        snd_que.append(m['from'] + ': ' + m['message'])
    return snd_que
        
def check_email():
    # Server is the address of the imap server
    mb = MailBox(server).login(user, password)

    # Fetch all unseen emails containing "electricity.com" in the from field
    # Don't mark them as seen
    # Set bulk=True to read them all into memory in one fetch
    # (as opposed to in streaming which is slower but uses less memory)
    messages = mb.fetch(criteria=AND(seen=False),
                            mark_seen=False,
                            bulk=True)

    for msg in messages:
        # Print form and subject
        # Print the plain text (if there is one)
        print(msg.subject)
        if 'TO:' in msg.subject.upper():
            print('here')

def send_email(to_address, from_dmr_id, message):
    #Establish SMTP Connection
    s = smtplib.SMTP(smtp_server, smtp_port) 
      
    #Start TLS based SMTP Session
    s.starttls() 

    #Login Using Your Email ID & Password
    s.login(smtp_username, smtp_password)
      
    #To Create Email Message in Proper Format
    msg = MIMEMultipart()

    #Setting Email Parameters
    msg['From'] = smtp_username
    msg['To'] = to_address
    msg['Subject'] = "Message from " + str(from_dmr_id)

    #Email Body Content
    message = """
    """ + message + """
<strong>come up with footer</strong>
    """

    #Add Message To Email Body
    msg.attach(MIMEText(message, 'html'))

    #To Send the Email
    s.send_message(msg)
      
    #Terminating the SMTP Session
    s.quit() 

if __name__ == '__main__':
    #Create necessary files
    if Path('./registered_users.txt').is_file():
        pass
    else:
        Path('./registered_users.txt').touch()
        with open('./registered_users.txt', 'w') as sub_form_file:
                sub_form_file.write("{1:{'network':'none'}}")
                sub_form_file.close()
    if Path('./waiting_messages.txt').is_file():
        pass
    else:
        Path('./waiting_messages.txt').touch()
        with open('./waiting_messages.txt', 'w') as sub_form_file:
                sub_form_file.write("{1:[{'from':'none', 'message':'none'}]}")
                sub_form_file.close() 

    
    # Start ANNOUNCE thread
    mqtt_thread = threading.Thread(target=mqtt_announce_loop, args=(5,))
    mqtt_thread.daemon = True
    mqtt_thread.start()
 
    mqtt_main(mqtt_server, mqtt_port)

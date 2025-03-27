import docker
import base64
import json
import paho.mqtt.client as mqtt

#----------------------------------------------------------------------------
def connect_mqtt(config):
    def on_connect(client, userdata, flags, rc, properties):
        if rc == 0:
            print("Connected to MQTT Broker!")
        else:
            print("Failed to connect, return code %d\n", rc)

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    # client.username_pw_set(username, password)
    client.on_connect = on_connect
    client.connect(config["Host"], config["Port"])
    return client
#----------------------------------------------------------------------------
def subscribe(client, config):
    def on_message(client, userdata, msg):
        message = msg.payload.decode()
        message_json = json.loads(message)
        update_auth(message_json,msg.topic,config,client)

    client.subscribe(config["SubTopic"])
    client.on_message = on_message
#----------------------------------------------------------------------------
def update_auth(message_json,mqtt_topic,config,client):
    # print(message_json)
    namespace_id = message_json['topic'].find("/")
    device_id = message_json['topic'].find("/", namespace_id+1)
    action = message_json['topic'][device_id+1:]
    device = message_json['topic'][namespace_id+1:device_id]

    if device != config["Master"]:
        if action == "things/twin/events/modified": #update password
            if "pass" in message_json['value']["attributes"]:
                print("Modifying '" + mqtt_topic + "' with the password to the one in the message...")
                update_device_broker(mqtt_topic,message_json['value']["attributes"]["pass"],device)
                remove_pass_from_dt(client,mqtt_topic,message_json,message_json['topic'][:device_id])
            else:
                print("No password found. No changed done.")
        elif action == "things/twin/events/created": #create device in broker
            if "pass" in message_json['value']["attributes"]:
                print("Creating '" + mqtt_topic + "' with the password to the one in the message....")
                create_device_broker(mqtt_topic,message_json['value']["attributes"]["pass"],device)
                remove_pass_from_dt(client,mqtt_topic,message_json,message_json['topic'][:device_id])
            else:
                print("No password found! Setting '"+ mqtt_topic +"' password as default")
                create_device_broker(mqtt_topic,config["DefaultPass"],device)
        elif action == "things/twin/events/deleted": #delete device
            print("Deleting '" + mqtt_topic +"'...")
            delete_device_broker(mqtt_topic,device)
        elif action == "things/twin/commands/modify": #updates attributes. ignore
            pass
        else:
            print("Message ignored case 1")
    else:
        print("Message ignored case 2")
#----------------------------------------------------------------------------
def delete_device_broker(mqtt_topic,device):
    # get mosquitto external container id
    client = docker.from_env()
    mosquitto_container = client.containers.list(all=True, filters={'name':'mosquitto_external'})

    # Update the encripted pass in the default config file
    f =  open('mosquitto.passwd', 'r+')
    file = f.read()
    if device in file:
        # print("found "+ device)
        device_id_start = file.find(device)
        device_id_end = file[device_id_start:].find("\n")
        if device_id_end != -1: #not found \n, last item in the file
            file_updated = file[:device_id_start] + file[device_id_start+device_id_end+1:]
            f.seek(0)
            f.write(file_updated)
            f.truncate()
            f.close()
        else:
            file_updated = file[:device_id_start-1] 
            f.seek(0)
            f.write(file_updated)
            f.truncate()
            f.close()       
    else:
        f.close()
        print("Didn't find "+ device +" in 'mosquitto.passwd'.")
    
    # Check if restrict topic in the default config file
    f =  open('mosquitto.acl', 'r+')
    file = f.read()
    if device in file:
        device_id_start = file.find(device)
        device_id_end = file.rfind(device)
        file_updated = file[:device_id_start-7] + file[device_id_end+len(device):]
        f.seek(0)
        f.write(file_updated)
        f.truncate()
        f.close()
    else:
        f.close() 
        print("Didn't find "+ device +" in 'mosquitto.acl'.")

    # Restarting container (mosquitto_external)
    mosquitto_container[0].restart()
    print('done')


#----------------------------------------------------------------------------
def update_device_broker(mqtt_topic,password,device):
    # get mosquitto external container id
    client = docker.from_env()
    mosquitto_container = client.containers.list(all=True, filters={'name':'mosquitto_external'})

    # open shared file used to encript password
    f = open('auxiliar.passwd','w')
    f.write(device+":"+password)
    f.close()
    
    # Execute pass encription in external mosquitto container
    pass_encript_command = "mosquitto_passwd -U mosquitto/config/auxiliar.passwd"
    mosquitto_container[0].exec_run(pass_encript_command, tty=True, privileged=True)

    # Update the encripted pass in the default config file
    f = open('auxiliar.passwd','r')
    pass_data = f.read()
    f.close()

    f =  open('mosquitto.passwd', 'r+')
    file = f.read()
    if device in file:
        # print("found "+ device)
        device_id_start = file.find(device)
        device_id_end = file[device_id_start:].find("\n")
        if device_id_end != -1: #not found \n, last item in the file
            file_updated = file[:device_id_start] + pass_data + file[device_id_start+device_id_end+1:]
            # print(file_updated)
            f.seek(0)
            f.write(file_updated)
            f.truncate()
            f.close()
        else:
            file_updated = file[:device_id_start] + pass_data[:-2]
            f.seek(0)
            f.write(file_updated)
            f.truncate()
            f.close()       
    else:
        f.close()
        print("Didn't find "+ device +" in 'mosquitto.passwd'. Adding it to the file...")
        with open('mosquitto.passwd', 'a') as file:
            file.write("\n"+pass_data[:-1])
    
    # Check if restrict topic in the default config file
    f =  open('mosquitto.acl', 'r+')
    file = f.read()
    f.close()
    if device in file:
        # there could be something regarding updating the topic, but for this it should be done manualy
        pass
    else: # Topic not found, adding it to file
        acl_data = "\n\nuser " + device +"\ntopic readwrite " + mqtt_topic
        with open('mosquitto.acl', 'a') as file:
            file.write(acl_data)

    # Restarting container (mosquitto_external)
    mosquitto_container[0].restart()
    print('done')
#----------------------------------------------------------------------------
def create_device_broker(mqtt_topic,password,device): 
     # get mosquitto external container id
    client = docker.from_env()
    mosquitto_container = client.containers.list(all=True, filters={'name':'mosquitto_external'})

    # open shared file used to encript password
    f = open('auxiliar.passwd','w')
    f.write(device+":"+password)
    f.close()
    
    # Execute pass encription in external mosquitto container
    pass_encript_command = "mosquitto_passwd -U mosquitto/config/auxiliar.passwd"
    mosquitto_container[0].exec_run(pass_encript_command, tty=True, privileged=True)

    # Put the encripted pass in the default config file
    f = open('auxiliar.passwd','r')
    pass_data = f.read()
    f.close()
    with open('mosquitto.passwd', 'a') as file:
        file.write("\n"+pass_data[:-1])

    # Add device to .acl file
    acl_data = "\n\nuser " + device +"\ntopic readwrite " + mqtt_topic
    with open('mosquitto.acl', 'a') as file:
        file.write(acl_data)

    # Restarting container (mosquitto_external)
    mosquitto_container[0].restart()
    print('done')
#----------------------------------------------------------------------------
def remove_pass_from_dt(client,topic,message,device):
    # print(device)
    # print(message)

    message["value"]["attributes"].pop("pass",None)
    message_updated={
        "topic": device +"/things/twin/commands/modify",
        "path":"/attributes",
        "value" : message["value"]["attributes"],
        "check" :True
    }

    client.publish(topic, json.dumps(message_updated))
    pass

#-----------------------------------------------------------------------------
def main():
    # Import config File
    f = open('config.json')
    config = json.load(f)

    # Eternal mqtt loop
    client = connect_mqtt(config)
    subscribe(client,config)
    client.loop_forever()


if __name__=="__main__":
    main()
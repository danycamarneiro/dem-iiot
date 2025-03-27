import paho.mqtt.client as mqtt
import json
import asyncio
import requests
import copy

in_flag = False
out_flag = False

enable_telemetry = False
enable_commands = False
enable_configuration_requests = False
enable_device_management = False
ditto_hostname =""
ditto_port = ""
ditto_auth = ""

# Inner broker
def connect_mqtt_inner(configfile): 
    def on_connect(client, userdata, flags, reason_code, properties):
        if reason_code == 0:
            global in_flag
            in_flag = True
            print("Connected to Inner MQTT Broker!")
        else:
            print("Failed to connect to Inner MQTT Broker , return code %d\n", reason_code)
    def on_disconnect(client, userdata, flags, reason_code, properties):
        print("Disconnected to Inner MQTT Broker!")
        global in_flag
        in_flag = False

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.connect(configfile["InnerHostName"], configfile["InnerPort"],60)
    return client

def subscribe_in(client_in, client_out, configfile):
    def on_message(client, userdata, msg):
        message = msg.payload.decode()
        message_json = json.loads(message)
        add_check = False
        # print("---Message IN---")
        # print(message_json)

        # remove "password" from "attributes" if exists
        if "pass" in message_json["value"]["attributes"]:
            message_json["value"]["attributes"].pop("pass",None)
            # print(message_json["value"]["attributes"])

        # adds a check to no duplicate msgs
        if "check" in message_json:
            if message_json["check"]:
                pass
            else:
                add_check = True
        else:
            add_check = True
        
        if add_check:
            message_json["check"]= True
            client_out.publish(msg.topic,json.dumps(message_json))

    client_in.subscribe(configfile["InnerSubTopic"])
    client_in.on_message = on_message

###############################################################################################
# Outer broker
def connect_mqtt_outer(configfile):
    def on_connect(client, userdata, flags, reason_code, properties):
        if reason_code == 0:
            global out_flag
            out_flag = True
            print("Connected to Outer MQTT Broker!")
        else:
            print("Failed to connect to Outer MQTT Broker, return code %d\n", reason_code)
    def on_disconnect(client, userdata, flags, reason_code, properties):
        global out_flag
        out_flag = False
        print("Disconnected to Outer MQTT Broker!")

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.username_pw_set(configfile["OutUsername"], configfile["OutPassword"])
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.connect(configfile["OutHostName"], configfile["OutPort"],60)
    return client

def subscribe_out(client_in, client_out, configfile):
    def on_message(client, userdata, msg):
        message = msg.payload.decode()
        message_json = json.loads(message)
        add_check = False
        # print("---Message Out---")
        # print(message_json)
        msg_topic_id = msg.topic[msg.topic.find("/")+1:]
        ditto_topic = message_json["topic"]
        aux = ditto_topic.find("/")
        ditto_topic_id=ditto_topic[:aux]+":"+ditto_topic[aux+1:aux+1+ditto_topic[aux+1:].find("/")]

        
        if msg_topic_id == ditto_topic_id:
            if "check" in message_json:
                if message_json["check"]:
                    pass
                else:
                    add_check = True
            else:
                add_check = True
            if add_check: # first time the message reaches que broker
                message_action = ditto_topic[aux+2+ditto_topic[aux+1:].find("/"):]
                message_action_command = message_action[:message_action.rfind("/")]

                #--> add topic segmentation here
                message_valid = False
                if message_action == "things/twin/commands/modify" and enable_telemetry:
                    print("telemetry")
                    message_valid = True
                elif message_action_command == "things/live/messages" and enable_commands:
                    message_valid = True
                    print("command")
                elif message_action == "things/twin/commands/retrieve" and enable_configuration_requests:
                    # --> add http forward method
                    print("acquisition")
                    ditto_url = "http://" + ditto_hostname + ":" + ditto_port + "/api/2/things/" +ditto_topic_id + message_json["path"]
                    ditto_headers = {
                            "Content-Type": "application/json",
                            "Authorization": "Basic " + ditto_auth
                        }
                    data = requests.get(url=ditto_url, headers=ditto_headers)
                    new_message_json = copy.deepcopy(message_json)
                    new_message_topic = copy.deepcopy(msg.topic)
                    new_message_json["value"]= json.loads(data.text)
                    new_message_json["check"]= True
                    print(new_message_json)
                    
                    client_out.publish(new_message_topic,json.dumps(new_message_json))
                    pass
                else: 
                    if enable_device_management:
                        print("management")
                        message_valid = True

                if message_valid:
                    message_json["check"]= True
                    client_in.publish(msg.topic,json.dumps(message_json))
        else:
            pass
            # print("error")
        
    client_out.subscribe(configfile["OutSubTopic"])
    client_out.on_message = on_message
###############################################################################################
async def main():
    # Import config File
    f = open('InnerBridgeConfig.json')
    ConfigData = json.load(f)
    # print(ConfigData)
    
    # set message permitions
    global enable_commands
    global enable_configuration_requests
    global enable_device_management
    global enable_telemetry
    global ditto_hostname
    global ditto_auth
    global ditto_port

    enable_telemetry = ConfigData["Enable_telemetry"]
    enable_commands =  ConfigData["Enable_commands"]
    enable_configuration_requests =  ConfigData["Enable_configuration_requests"]
    enable_device_management =  ConfigData["Enable_device_management"]
    ditto_port = ConfigData["Ditto_port"]
    ditto_hostname = ConfigData["Ditto_hostname"]
    ditto_auth = ConfigData["Ditto_auth"]

    # Create connection with inner broker
    mqtt_inner = connect_mqtt_inner(ConfigData)

    # Create connection with outer broker
    mqtt_outer = connect_mqtt_outer(ConfigData)

    # Define parameters with the connection
    subscribe_in(mqtt_inner, mqtt_outer, ConfigData)
    subscribe_out(mqtt_inner, mqtt_outer, ConfigData)
    # Stablish Connection

    # Loop forever
    mqtt_outer.loop_start()
    mqtt_inner.loop_start()

    in_loop_down = False
    out_loop_down = False
    while True:
        if not in_flag and not in_loop_down: # update flag if disconneted in
            in_loop_down = True
        if not out_flag and not out_loop_down:# update flag if disconneted out
            out_loop_down = True
        if in_flag and in_loop_down: # resubscribes in when reconnected
            subscribe_in(mqtt_inner, mqtt_outer, ConfigData)
            in_loop_down = False
        if out_flag and out_loop_down: # resubscribes out when reconnected
            subscribe_out(mqtt_inner, mqtt_outer, ConfigData)
            out_loop_down = False
        await asyncio.sleep(0.5)
        pass


if __name__ == "__main__":
    asyncio.run(main())
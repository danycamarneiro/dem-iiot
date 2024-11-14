import paho.mqtt.client as mqtt
import json
import asyncio

in_flag = False
out_flag = False

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
        if "check" in message_json:
            if message_json["check"]:
                pass
            else:
                add_check = True
        else:
            add_check = True
        if add_check:
            message_json["check"]= True
            client_in.publish(msg.topic,json.dumps(message_json))
        
    client_out.subscribe(configfile["OutSubTopic"])
    client_out.on_message = on_message
###############################################################################################
async def main():
    # Import config File
    f = open('InnerBridgeConfig.json')
    ConfigData = json.load(f)
    # print(ConfigData)

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
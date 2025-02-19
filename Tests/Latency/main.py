#!/usr/bin/env python
import json
import paho.mqtt.client as mqtt
import asyncio

async def main():
    ##-------------------------import config file---------------------
    f = open('config.json')
    ConfigData = json.load(f)

    mqtt_client = connect_mqtt(ConfigData)
    mqtt_subscribe(mqtt_client,ConfigData)
    mqtt_client.loop_start()

    while True:
        await asyncio.sleep(0.5)

# connect mqtt
def connect_mqtt(configfile):
    def on_connect(client, userdata, flags, reason_code, properties):
        if reason_code == 0:
            print("Connected to MQTT Broker!")
        else:
            print("Failed to connect to MQTT Broker, return code %d\n", reason_code)
    def on_disconnect(client, userdata, flags, reason_code, properties):
        print("Disconnected to MQTT Broker!")

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.username_pw_set(configfile["MQTTDevice"], configfile["MQTTPass"])
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.connect(configfile["MQTTHostName"], configfile["MQTTPort"],60)
    return client

# subscribe to mqtt
def mqtt_subscribe(client_mqtt, configfile):
    def on_message(client, userdata, msg):
        print("NEW MESSAGE")
        message = msg.payload.decode()
        message_json = json.loads(message)
        try:
            isanswer = message_json["Answer"]
        except:
            isanswer = False
        if  not isanswer:    
            res_msg ={
                "topic": message_json["topic"],
                "headers" : {"content-type": "application/json", "correlation-id": message_json["headers"]["correlation-id"] },
                "value": None,
                "path" : message_json["path"],
                "status" : 200,
                "qos": 0,
                "Answer": True
            }
            client_mqtt.publish(configfile["MQTTSubTopic"],json.dumps(res_msg))

    client_mqtt.subscribe(configfile["MQTTSubTopic"])
    client_mqtt.on_message = on_message

if __name__=="__main__":
    asyncio.run(main())
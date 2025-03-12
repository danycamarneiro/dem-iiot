import paho.mqtt.client as mqtt
import json
from multiprocessing import Manager
import forward

#-------------------------------------MQTT--------------------------------------
def connect_mqtt():
    global configfile
    def on_connect(client, userdata, flags, reason_code, properties):
        if reason_code == 0:
            print("Connected to MQTT Broker!")
            mqtt_subscribe(client)
            global val
            val['mqtt_alive'] = True
            forward.database_segmentator(val)
        else:
            print("Failed to connect to MQTT Broker, return code %d\n", reason_code)
    def on_disconnect(client, userdata, flags, reason_code, properties):
        print("Disconnected to MQTT Broker!")
        global val
        val['mqtt_alive']= False
    
    def mqtt_subscribe(client_mqtt):
        global configfile
        def on_message(client, userdata, msg):
            message = msg.payload.decode()
            message_json = json.loads(message)
            # print(message_json)
            namespace_id = message_json['topic'].find("/")
            device_id = message_json['topic'].find("/", namespace_id+1)
            action = message_json['topic'][device_id+1:]
            try:
                if action == "things/twin/commands/modify":
                    print("new message")
                    global val
                    val['NewMessage'] = message_json
            except Exception as error:
                # print("Error: " + error)
                None

        client_mqtt.subscribe(configfile["MQTTSubTopic"])
        client_mqtt.on_message = on_message

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.connect(configfile["MQTTHostName"], configfile["MQTTPort"],60)
    return client

#-------------------------------------Main--------------------------------------
def main():
    # Import config File
    f = open('Database_Bridge_Config.json')
    global configfile
    configfile = json.load(f)
    
    manager= Manager()
    global val
    val = manager.dict()
    val['NewMessage']= None

    # set mqtt client
    mqtt_client = connect_mqtt()

    # start mqtt client
    mqtt_client.loop_forever()


if __name__=="__main__":
    main()
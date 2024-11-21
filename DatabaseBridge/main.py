import paho.mqtt.client as mqtt
import json
import psycopg2, influxdb_client
import asyncio
from time import time
from influxdb_client.client.write_api import SYNCHRONOUS

#-------------------------------------MQTT--------------------------------------
mqtt_flag = False
def connect_mqtt(configfile):
    def on_connect(client, userdata, flags, reason_code, properties):
        if reason_code == 0:
            global mqtt_flag
            mqtt_flag = True
            print("Connected to MQTT Broker!")
        else:
            print("Failed to connect to MQTT Broker, return code %d\n", reason_code)
    def on_disconnect(client, userdata, flags, reason_code, properties):
        global mqtt_flag
        mqtt_flag = False
        print("Disconnected to MQTT Broker!")

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.connect(configfile["MQTTHostName"], configfile["MQTTPort"],60)
    return client


def mqtt_subscribe(client_mqtt, configfile):
    def on_message(client, userdata, msg):
        message = msg.payload.decode()
        message_json = json.loads(message)
        # print(message_json)
        global pg_flag
        namespace_id = message_json['topic'].find("/")
        device_id = message_json['topic'].find("/", namespace_id+1)
        action = message_json['topic'][device_id+1:]
        if action == "things/twin/commands/modify":
            namespace = message_json['topic'][0:namespace_id]
            device = message_json['topic'][namespace_id+1:device_id]
            timetime = time()
            for i in message_json['database']:
                if i.lower() == "postgres" and pg_flag:
                    print("postgre")
                    print(time()-timetime)
                    asyncio.run(PQ_add_database(namespace, device, message_json))
                    
                if i.lower() == "influx":
                    print("influx")
                    print(time()-timetime)
                    asyncio.run(Inf_add_database(namespace, device, message_json, bucket=configfile["Inf_bucket"], org=configfile["Inf_org"]))
                    
                        

    client_mqtt.subscribe(configfile["MQTTSubTopic"])
    client_mqtt.on_message = on_message
#-------------------------------------PostGres--------------------------------------
pg_flag = False
pg_conn = None

# set connection
def get_PQ_connection(ConfigData):
    try:
        return psycopg2.connect(
        database= ConfigData["PG_DB"],
        user=ConfigData["PG_user"],
        password=ConfigData["PG_pass"],
        host=ConfigData["PG_host"],
        port=ConfigData["PG_port"],
    )
    except:
        return False

# adds to postgre database
async def PQ_add_database(namespace, device, message_json):
    global pg_conn
    cursor = pg_conn.cursor()

    # check is namespace schema existes
    cursor.execute("SELECT schema_name FROM information_schema.schemata WHERE schema_name = '"+namespace+"';")
    result = cursor.fetchone()
    # print(result)
    if result == None:
        # create a new schema
        cursor.execute("CREATE SCHEMA IF NOT EXISTS "+namespace+";")  
    
    cursor.execute("SET search_path TO " + namespace+";")
    # check if table exists
    # cursor.execute("SELECT EXISTS ( SELECT 1 FROM pg_tables WHERE schemaname = '"+namespace+"' AND tablename = '" + device +"' ) AS table_existence;")
    cursor.execute("SELECT EXISTS ( SELECT 1 FROM pg_tables WHERE tablename = '" + device +"' ) AS table_existence;")
    result = cursor.fetchone()
    # print(result)
    query = "id SERIAL PRIMARY KEY, timestamp TIMESTAMP WITH TIME ZONE,"
    try:
        msg_timestamp = message_json["datetimestamp"]
    except:
        msg_timestamp = "Null"

    variables ="timestamp, "
    values = "to_timestamp(" + str(msg_timestamp) + "), "
    for j in message_json["value"]:
        data = message_json["value"][j]["properties"]["value"]
        if not result[0]: # no table
            datatype = type(data)
            query += j + " " + datatype.__name__.capitalize() +", "
        variables += j + ", "
        values += str(message_json["value"][j]["properties"]["value"]) + ", "
    if not result[0]: # no table -> create table
        cursor.execute("CREATE TABLE "+device+"("+query[:-2]+");")
    data_injected = False
    pg_conn.commit()
    while not data_injected:
        try:
            inject_query = "INSERT INTO " + device + " (" + variables[:-2]+") VALUES (" + values[:-2]+");"
            cursor.execute(inject_query)
            data_injected = True
            pg_conn.commit()
            # print("Done")  
        except Exception as error:
            value_name = str(error)[str(error).rfind(",")+2:str(error).rfind(")")]
            error_code = str(error)[str(error).rfind("\"")+2:str(error).rfind("\"")+16]
            # print(value_name)
            # print(error_code)
            # print(error)
            pg_conn.rollback()
            if error_code == "does not exist":
                column_query = "ALTER TABLE "+ device + " ADD " + value_name + " " + type(message_json["value"][value_name]["properties"]["value"]).__name__.capitalize()+";"
                # print(column_query)
                cursor.execute(column_query)
            else: # something not accounted
                print("something unnespected occured")
                data_injected = True
#------------------------------------Influx--------------------------------------
Inf_conn = None
# set connection
def get_Inf_connection(ConfigData):
    try:
        inf_url = "http://"+ ConfigData["Inf_host"] +":"+ str(ConfigData["Inf_port"])
        return influxdb_client.InfluxDBClient(url=inf_url, token=ConfigData["Inf_token"], org=ConfigData["Inf_org"])
    except:
        return False

async def Inf_add_database(namespace, device, message_json,bucket,org):
    global Inf_conn
    write_api = Inf_conn.write_api(write_options=SYNCHRONOUS)
    p = influxdb_client.Point(namespace).tag("device", device)
    for j in message_json["value"]:
        p=p.field(j, message_json["value"][j]["properties"]["value"])
    try: 
        write_api.write(bucket=bucket, org=org, record=p)
    except Exception as e:
        print(e)
    # print("inf done")

#-------------------------------------Main--------------------------------------
async def main():
    # Import config File
    f = open('Database_Bridge_Config.json')
    ConfigData = json.load(f)
    
    # set mqtt client
    mqtt_client = connect_mqtt(ConfigData)

    # set postgres client
    if ConfigData["Add_PG"]:
        global pg_conn
        pg_conn = get_PQ_connection(ConfigData)
        if pg_conn:
            global pg_flag
            pg_flag = True
            print("Connection to the PostgreSQL established successfully.")
        else:
            print("Connection to the PostgreSQL encountered and error.")
        
        
    # set influxdb client
    if ConfigData["Add_Influx"]:
        global Inf_conn
        Inf_conn = get_Inf_connection(ConfigData)
        if Inf_conn:
            print("Connection to the InfluxDB established successfully.")
        else:
            print("Connection to the InfluxDB encountered and error.")

    # start mqtt client
    mqtt_subscribe(mqtt_client, ConfigData)
    mqtt_client.loop_start()

    loop_down = False
    while True:
        if not mqtt_flag and not loop_down: # update flag if disconneted in
            loop_down = True
        if mqtt_flag and loop_down: # resubscribes in when reconnected
            mqtt_subscribe(mqtt_client, ConfigData)
            loop_down = False
        await asyncio.sleep(0.5)

if __name__=="__main__":
    asyncio.run(main())
import time
import json
from multiprocessing import Manager
import influxdb_client
from influxdb_client.client.write_api import ASYNCHRONOUS
import asyncio

def influx_link(val):
    manager = Manager()

    while val['mqtt_alive']:

        # load config file
        f = open('DatabaseConfigs/influx_config.json')
        configfile = json.load(f)

        # start connection to database
        inf_url = "http://"+ configfile["Inf_host"] +":"+ str(configfile["Inf_port"])
        infclient = influxdb_client.InfluxDBClient(url=inf_url, token=configfile["Inf_token"], org=configfile["Inf_org"])
        write_api = infclient.write_api(write_options=ASYNCHRONOUS)

        try:
            if len(val['influxdb']) > 0:
                #-> add to database
                asyncio.run(influx_add_database(write_api, val['influxdb'][0], configfile["Inf_bucket"], org= configfile["Inf_org"]))
                del val['influxdb'][0]
        except Exception as e:
            print(e)
            val['influxdb'] = manager.list()
        time.sleep(0.03)

async def influx_add_database(write_api,message,bucket,org):
    # print(message)
    namespace_id = message['topic'].find("/")
    device_id = message['topic'].find("/", namespace_id+1)
    namespace = message['topic'][0:namespace_id]
    device = message['topic'][namespace_id+1:device_id]
    p = influxdb_client.Point(namespace).tag("device", device)
    if 'value' in message:
        if message["path"]== "/features":
            for j in message["value"]:
                try:
                    p=p.field(j, message["value"][j]["properties"]["value"])
                except:
                    print('Wrong struct used for '+ j)
        else:
            propertynamespace = message["path"][message["path"].rfind("/")+1:]
            for j in message["value"]["properties"]:
                try:
                    p=p.field(propertynamespace+"_"+j, message["value"]["properties"][j])
                except:
                    print('Wrong struct used for '+ j)
    try: 
        write_api.write(bucket=bucket, org=org, record=p)
    except Exception as e:
        print(e)
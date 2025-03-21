# Template
import time
import json
from multiprocessing import Manager
import asyncio

# Add-ons
import psycopg2
from math import floor

def postgres_link(val):
    manager = Manager()
    while val['mqtt_alive']:

        # load config file
        f = open('DatabaseConfigs/postgres_config.json')
        configfile = json.load(f)
        
        # connects to postgres
        pg_con = get_PQ_connection(configfile)
        if pg_con:
            try:
                if len(val['postgres']) > 0:
                    #-> add to database
                    asyncio.run(postgres_add_database(pg_con,val['postgres'][0]))
                    del val['postgres'][0]
            except Exception as e:
                print(e)
                val['postgres'] = manager.list()
        time.sleep(0.03)

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
    except Exception as e:
        print("Something went wrong with postgres database link:")
        print(e)
        return False

async def postgres_add_database(pg_conn,message):
    namespace_id = message['topic'].find("/")
    device_id = message['topic'].find("/", namespace_id+1)
    namespace = message['topic'][0:namespace_id]
    device = message['topic'][namespace_id+1:device_id]
    
    cursor = pg_conn.cursor()

    # check is namespace schema existes
    cursor.execute("SELECT schema_name FROM information_schema.schemata WHERE schema_name = '"+namespace+"';")
    result = cursor.fetchone()
    # print(result)

    if result == None:
        # create a new schema
        cursor.execute("CREATE SCHEMA IF NOT EXISTS "+namespace+";")  
        # pg_conn.commit()
    cursor.execute("SET search_path TO " + namespace+";")
    # check if table exists
    
    cursor.execute("SELECT EXISTS ( SELECT 1 FROM pg_tables WHERE tablename = '" + device +"' ) AS table_existence;")
    result = cursor.fetchone()
    # print(result)
    query = "id SERIAL PRIMARY KEY, timestamp TIMESTAMP WITH TIME ZONE,"
    try:
        msg_timestamp = floor((message["datetimestamp"]))

    except:
        msg_timestamp = "Null"

    variables ="timestamp, "
    values = "to_timestamp(" + str(msg_timestamp) + "), "
    # print(message)
    if 'value' in message:
        if message["path"]== "/features":
            for j in message["value"]:
                try:
                    data = message["value"][j]["properties"]['value']
                    if not result[0]: # no table
                        datatype = type(data)
                        print(datatype)
                        query += j + " " + datatype.__name__.capitalize() +", "
                    variables += j + ", "
                    values += str(message["value"][j]["properties"]["value"]) + ", "
                except:
                    print('Wrong struct used for '+ j)
        else:
            propertynamespace = message["path"][message["path"].rfind("/")+1:]
            # print(propertynamespace)
            for j in message["value"]["properties"]:
                try:
                    data = message["value"]["properties"][j]
                    if not result[0]: # no table
                        datatype = type(data)
                        query += propertynamespace+"_"+j + " " + datatype.__name__.capitalize() +", "
                    variables += propertynamespace+"_"+j + ", "
                    values += str(message["value"]["properties"][j]) + ", "
                except:
                    print('Wrong struct used for '+ j)
    else:
        print("'value' not found in the message")
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
            print(error)
            str_error = str(error)
            mark1 = str_error.find("\"")
            mark2 = find_nth(str_error, "\"",2)
            # print(str_error[mark1+1:mark2])
            value_name = str_error[mark1+1:mark2]
            error_code = str(error)[str(error).rfind("\"")+2:str(error).rfind("\"")+16]
            # print(value_name)
            # print(error_code)
            # print(error)
            pg_conn.rollback()
            if error_code == "does not exist":
                if message["path"]== "/features":
                    column_query = "ALTER TABLE "+ device + " ADD " + value_name + " " + type(message["value"][value_name]["properties"]["value"]).__name__.upper()+";"
                    # print(column_query)
                else:
                    variable_ind = value_name[value_name.rfind("_")+1:]
                    print("-----------------------------------------------------")
                    print(variable_ind)
                    alter_query = "ALTER TABLE "+ device + " ADD " + value_name + " " + type(message["value"]["properties"][variable_ind]).__name__.upper()+";"
                    print(alter_query)
                    column_query = alter_query
                cursor.execute(column_query)
                pg_conn.commit()
            else: # something not accounted
                print("something unnespected occured")
                data_injected = True


# Other functions
def find_nth(haystack: str, needle: str, n: int) -> int:
    start = haystack.find(needle)
    while start >= 0 and n > 1:
        start = haystack.find(needle, start+len(needle))
        n -= 1
    return start
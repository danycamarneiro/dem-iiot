import multiprocessing
from DatabaseLinks import *

def database_segmentator(val,configfile):
    # -> add a parser s1 here
    multiprocessing.Process(target=message_parser.message_parser, args=(val,)).start()
    # list the links that exist in .DatabaseLinks 
    if configfile["Enable_postgres"]:
        multiprocessing.Process(target=postgres_link.postgres_link, args=(val,)).start()
    if configfile["Enable_influxdb"]:
        multiprocessing.Process(target=influx_link.influx_link, args=(val,)).start()
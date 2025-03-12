import multiprocessing
from DatabaseLinks import *

def database_segmentator(val,configfile):
    if configfile["Enable_postgres"]:
        pass
    if configfile["Enable_influxdb"]:
        multiprocessing.Process(target=influx_link.influx_link(val), args=(val,)).start()
        # p.start()

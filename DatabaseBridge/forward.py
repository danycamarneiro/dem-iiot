import multiprocessing
import time
import sys

def database_segmentator(val):
    # print("supsup")
    p = multiprocessing.Process(target=simple_print, args=(val,))
    p.start()

def simple_print(val): 
    while val['mqtt_alive']:
        if val['NewMessage'] != None:
            print(val['NewMessage'])
        val['NewMessage'] = None
        time.sleep(0.1)
import time

def influx_link(val): 
    while val['mqtt_alive']:
        if val['NewMessage'] != None:
            print(val['NewMessage'])
        val['NewMessage'] = None
        print('alive')
        time.sleep(0.1)
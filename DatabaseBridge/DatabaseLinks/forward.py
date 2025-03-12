import multiprocessing
import time

#-------------------- https://stackoverflow.com/questions/1057431/how-to-load-all-modules-in-a-folder
from os.path import dirname, basename, isfile, join
import glob
modules = glob.glob(join(dirname(__file__), "*.py"))
__all__ = [ basename(f)[:-3] for f in modules if isfile(f) and not f.endswith('__init__.py')]
#----------------------------------------------------

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
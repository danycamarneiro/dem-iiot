#!/usr/bin/env python
import json
import requests
import numpy as np 
import pandas as pd 
from time import time


def main():
    ##-------------------------import config file---------------------
    f = open('config_2.json')
    ConfigData = json.load(f)

    url = "http://"+ConfigData["HostName"]+":"+str(ConfigData["Port"])+"/api/2/things/"+ConfigData["namespace"]+":"+ConfigData["device"]+"/inbox/messages/test?timeout=20"
    header = {
        "Content-Type": "application/json",
        "Authorization": "Basic ZGl0dG86ZGl0dG8="
    }
    timers = []
    for i in range (ConfigData["attempts"]+2):
        t = time()
        var = requests.post(url=url,headers=header,data={})
        ty = time()-t
        if i != 0:
            timers.append(ty)
    # print(timers)
    arr = np.array(timers)
    DF = pd.DataFrame(arr)
    DF.to_csv("timers.csv")
     

if __name__=="__main__":
    main()
import time

def message_parser(val):
    while val['mqtt_alive']:
        if val['NewMessage'] != None:
            if "database" in val['NewMessageContent']:
                    for i in val['NewMessageContent']["database"]:
                        # print(i)
                        if "datetimestamp" in val['NewMessageContent']: # in seconds
                            msg_timestampt = val['NewMessageContent']["datetimestamp"]
                        else:
                            msg_timestampt = time.time()
                        # print(msg_timestampt)
                        try:
                            to_append={"value":val['NewMessageContent']["value"],
                                       "topic": val['NewMessageContent']["topic"],
                                       "path": val['NewMessageContent']["path"],
                                       "datetimestamp":msg_timestampt
                                        }
                            val[i].append(to_append)
                        except:
                             print('Something wrong in injecting new json to FIFO array for ' + i)
                    val['NewMessageContent'] = None
            val['NewMessage'] = None
        time.sleep(0.01)
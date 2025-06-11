import time

def message_parser(val):
    while val['mqtt_alive']:
        if len(val['NewMessage']) > 0:
            if "database" in val['NewMessage'][0]:
                    for i in val['NewMessage'][0]["database"]:
                        # print(i)
                        if "datetimestamp" in val['NewMessage']: # in seconds
                            msg_timestampt = val['NewMessage']["datetimestamp"]
                        else:
                            msg_timestampt = time.time()
                        # print(msg_timestampt)
                        try:
                            to_append={"value":val['NewMessage'][0]["value"],
                                       "topic": val['NewMessage'][0]["topic"],
                                       "path": val['NewMessage'][0]["path"],
                                       "datetimestamp":msg_timestampt
                                        }
                            val[i].append(to_append)
                        except:
                             print('Something wrong in injecting new json to FIFO array for ' + i)
                    val['NewMessageContent'] = None
            del val['NewMessage'][0]
        time.sleep(0.01)
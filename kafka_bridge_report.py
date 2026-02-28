# import kafka
import confluent_kafka
from confluent_kafka import Consumer, KafkaError, Producer
from datetime import datetime
from kafka_bridge_report_config import KafkaConfig

import celery_report_gen
from celery_report_config import CELERY_REPORT_CONFIG

from colorama import Fore
import time
import json



def parse_nested_json(data):
    # decoding the json by recursion for each json decodable field.
    if isinstance(data, str):
        try:
            return json.loads(data)
        except json.JSONDecodeError:
            return data
    #
    elif isinstance(data, dict):
        parsed_data = {}
        for key, value in data.items():
            parsed_data[key] = parse_nested_json(value)
        return parsed_data
    #
    elif isinstance(data, list):
        parsed_data = []
        for item in data:
            parsed_data.append(parse_nested_json(item))
        return parsed_data
    #
    else:
        return data


def main():
    consumer = Consumer({
                            "bootstrap.servers": KafkaConfig.BOOTSTRAP_SERVERS,
                            "group.id": KafkaConfig.GROUP_ID,
                            "default.topic.config": {"auto.offset.reset": "smallest"},
                            "enable.auto.commit": True,
                        })

    consumer.subscribe([KafkaConfig.SUBSCRIBE_TOPIC])

    try:
        print(f"Listening on topic : {KafkaConfig.SUBSCRIBE_TOPIC}")
        # message = {
        #             "SurveyId": "398b8c46-e4c3-4ff7-a50d-73aa448f5a99",
        #             "ObjectStructureIds": "524a2f02-2b80-462b-9086-a82e9b6cadf8,0298700f-da00-4daf-b740-427ebb890b47,a7928e75-afed-4a12-b19b-2c19ffc09378,6ab44d08-d40e-4694-ab6e-93e0261d6c1b,a9a9bede-7737-4096-af37-dfd185dab1ee,204abdea-6ba6-4d2b-842f-9d32108c384b,cc52dd6c-592c-4cbb-a121-48a51985a3aa,78fd081b-1c94-4dbd-bef3-ae1423caec4c,4b05dbad-e5f3-416d-b1d9-dd1ae3939c43,0f4bc8bf-4ce2-48b2-aa2a-bf73dd7db48f,4d7e295f-ad22-44f6-b643-dae13151a8ed,fb023018-3cf1-44b3-8587-96765d3eebb1,6730ed97-c97c-4576-a0a7-6ed06647ce21,dd8dbe02-11cd-4e36-875c-68667fd240f4,7ddc1939-5387-413d-b214-10e3c03f2043,dcbe4659-df91-47b5-91da-e69e16f7d8c7,b64a10b7-90dc-4332-a96d-fe5bfd4a72d2,a45af4e5-484e-46d8-8c38-35d45363fdb4,aba932fe-d60b-4a8e-9eba-bb3d1400df99,272853e7-8e91-413f-a005-01ddec32f84a,5180a1fe-f4c7-45bc-8249-73d7659f836b,596783ae-054e-41c1-a015-91f2b1136247,8ebd1ee6-2df6-4833-9138-e27b53eb7224,20ceb994-184e-4952-8ff8-bd47a0209184,06b82bc9-1a6e-4a85-aa6c-d5a46d46a0ab,e403459e-7f42-4ca4-b0ff-3323d0a0a776,6d6aa61d-f0ff-4de8-828d-918d8fe7b59b,05b126eb-8c15-4b6b-a7fc-ce74932d121f,2982639d-fb84-487c-96ac-6b72b1a5b017,f03cb118-9c32-4265-ac04-515753240b58,2e965624-c0d9-4256-ba84-4c1acc75f078,beae02f1-5d8d-4b92-b3a4-2fb27658b4a9,b402717e-c807-4633-8672-b1e3726c4877,416eaad4-21f6-400d-8abb-69de9d85b8af,04a4cd42-d104-45ae-8d8d-8583e7346bc8,f48948c5-888c-42d0-a073-49e27a4e6c41,aa039863-1d05-4719-b4c4-e49e21b4a7d5,09b0da82-399d-4440-bfea-d22cc5c07230,38f095ce-f0d0-4df2-ab9d-c61aff2e557a,fe03c9a7-5042-45af-994f-db0438544b35",
        #             "Annomalies": "",
        #             "TopicName": "398b8c46-e4c3-4ff7-a50d-73aa448f5a99-20250401T101103-s",
        #             "RequestType": "s"
        #         }
        # ret = celery_report_gen.tnd_report_app.send_task("celery_report_gen.task_tnd_report", args= (message, KafkaConfig.BOOTSTRAP_SERVERS, KafkaConfig.RESPONSE_TOPIC  ), queue= CELERY_REPORT_CONFIG.TASK_QUEUE)
        
        
        while True:
            message = consumer.poll(1.0) # un-blocking wait for message, else 1.0 can be defined for 1 sec 
            if message is None:
                continue
            if message.error():
                if message.error().code() == KafkaError._PARTITION_EOF:
                    print("End of partition reached.")
                else:
                    print(f"Error while consuming message: {message.error()}")
            else:
                # Send Task to celery worker.
                message = message.value() # json can also be decoded by bytes.

                message = json.loads(message)
                print(message)
                message = parse_nested_json(message)
                ret = celery_report_gen.tnd_report_app.send_task("celery_report_gen.task_tnd_report", args= (message, KafkaConfig.BOOTSTRAP_SERVERS, KafkaConfig.RESPONSE_TOPIC  ), queue= CELERY_REPORT_CONFIG.TASK_QUEUE)


                print(f"{Fore.CYAN}{datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')}{Fore.BLUE} > Received message: {Fore.RESET} {message}")


    except KeyboardInterrupt:
        print(f"{Fore.RED}Consumer interrupted.{Fore.RESET}")
    finally:
        consumer.close()


if __name__ == '__main__':
    main()

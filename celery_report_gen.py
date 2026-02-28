import os
import json
from celery import Celery
from celery_report_config import CELERY_REPORT_CONFIG
from confluent_kafka import Producer, KafkaError
from colorama import Fore
import sys

import report_module_manager


tnd_report_app = Celery('tnd_report', broker=CELERY_REPORT_CONFIG.BROKER, backend = CELERY_REPORT_CONFIG.BACKEND)

tnd_report_app.conf.update(
    task_routes={
        'celery_tnd.tasks.visual': {'queue': CELERY_REPORT_CONFIG.TASK_QUEUE},
    },
    task_track_started=True,
    worker_prefetch_multiplier=1,
    worker_concurrency=1,
)


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


@tnd_report_app.task(bind= True)
def task_tnd_report(self, task, kafka_bootstrap_servers, result_response_topic):
    print("report method called........")
    print(task)
    task = parse_nested_json(task)
    #################################################################################################################

    # topic_name = task.get('TopicName') or task.get('SurveyId') or task.get('ReportDownload') or task.get("SurveyWiseImageReport") or task.get("parameters", {})
    # if not topic_name:
    #     error_msg = f"Neither 'TopicName' nor 'survey_id' found in task. Available keys: {list(task.keys())}"
    #     print(f"ERROR: {error_msg}")
    #     return {'error': error_msg, 'status': 'failed'}

    # print(f"Using topic name: {topic_name}")

    # # Create Kafka producer
    # producer = Producer({'bootstrap.servers': kafka_bootstrap_servers})

    # #################################################################################################################



    # def progress_callback(progress):
    #     # send the progress to the kafka topic which was received. (e.g.) task.topicName
    #     print(f"inside user defined progress function : {progress}")
    #     self.update_state(state='PROGRESS', meta={'progress': progress})

    #     producer.produce(topic_name, value=str(progress).encode('utf-8'))
    #     producer.flush()


    report_module_dir = os.path.join(os.path.dirname(__file__) , "report_modules")

    test_mode = True

    if task.get("RequestType") == 'w':
        report_module_dir = os.path.join(report_module_dir, "visual_default_source" if test_mode else "visual_default_build")

    elif task.get("RequestType") == 'l':
        report_module_dir = os.path.join(report_module_dir, "lidar_default_source" if test_mode else "lidar_default_build")

    elif task.get("RequestType") == 't':
        report_module_dir = os.path.join(report_module_dir, "thermal_default_source" if test_mode else "thermal_default_build")

    else:
        report_module_dir = os.path.join(report_module_dir, "surveillance_default_source" if test_mode else "surveillance_default_build")

    # elif task.get("RequestType") == 's':
    #     report_module_dir = os.path.join(report_module_dir, "solar_default_source" if test_mode else "solar_default_build")

    # elif task.get("RequestType") == 'a':
    #     report_module_dir = os.path.join(report_module_dir, "ashdyke_default_source" if test_mode else "ashdyke_default_build")

    # elif task.get("RequestType") == 'p':
    #     report_module_dir = os.path.join(report_module_dir, "pmc_default_source" if test_mode else "pmc_default_build")

    res = report_module_manager.process_pdf_task(report_module_dir, conda_env_name= './ntpc_reporting_engine_venv/bin/activate', task=task, kafka_bootstrap_servers=kafka_bootstrap_servers, result_response_topic=result_response_topic )

    print("visual_main.main results : ", res)

    return res

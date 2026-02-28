import os
import shutil

from db_client import DbClient
# create a db_client and connect to it accordingly. to call the stored procedure

import json
import time
from datetime import datetime

import template_writer 
from excel_generator import ExcelGenerator

from report_gen_config import ReportGenConfig, AWSConfig, DBConfig, MinioConfig
from colorama import Fore
from decimal import Decimal
from datetime import date, datetime
from uuid import UUID
import requests
from awsmanager import AWSManager
from confluent_kafka import Producer, KafkaError

import traceback

from minio import Minio
from minio.error import S3Error


def sanitize_for_json(obj):
    if isinstance(obj, list):
        return [sanitize_for_json(i) for i in obj]

    if isinstance(obj, dict):
        return {k: sanitize_for_json(v) for k, v in obj.items()}

    if isinstance(obj, Decimal):
        return float(obj)          # numeric stays numeric

    if isinstance(obj, (datetime, date)):
        return obj.isoformat()     # ISO-8601 string

    if isinstance(obj, UUID):
        return str(obj)

    return obj

def extract_date(iso_datetime_str: str):
    if not iso_datetime_str:
        return None

    try:
        # Handle "Z" (UTC)
        dt = datetime.fromisoformat(iso_datetime_str.replace("Z", "+00:00"))
        return dt.strftime("%d-%m-%Y")   # DD-MM-YYYY
    except ValueError:
        return None

def setup_directories(temp_dir: str, project_dir:str ):
    if not os.path.exists(ReportGenConfig.TEMP_DIR):
        os.makedirs(ReportGenConfig.TEMP_DIR)

    if os.path.exists(project_dir):
        shutil.rmtree(project_dir)

    os.makedirs(project_dir)

    return temp_dir, project_dir


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


def main(task, kafka_bootstrap_servers, result_response_topic, progress_callback=lambda *args, **kwargs: None):
    ret = False

    try:
        print("inside main function...")
        db_client = DbClient(DBConfig.HOST, DBConfig.PORT, DBConfig.DATABASE, DBConfig.USER, DBConfig.PASSWORD)
        print("Getting report data from the database.")
        parameters = task.get("parameters", {})
        payload = db_client.get_surveillance_report_data(parameters.get("p_from"),parameters.get("p_to"), parameters.get("p_site_ids"),parameters.get("p_zone_ids"),parameters.get("p_camera_ids"), parameters.get("p_anomaly_ids"))
        # It is assured that if inspection exists then tree will not be null.
        # inspection_tree = db_client.get_inspection_tree(task.get("InspectionId"))
        # inspection_tree = inspection_tree[0]['Tree']

        # excel_data = db_client.get_excel_data(task.get("SurveyId"), task.get("RequestType"))
        
        # with open("current_excel_data.json", 'w') as f:
        #     json.dump(excel_data, f, indent=4)
        
        # excel_data = excel_data[0]["JsonResultSet"]
        payload = sanitize_for_json(payload)
        payload["from"] = extract_date(parameters.get("p_from"))
        payload["to"] = extract_date(parameters.get("p_to"))
        with open("current_payload.json", "w") as f:
            json.dump(payload, f , indent=4)
        
        # with open("current_payload.json", "r") as f:
        #     payload = json.load(f)
    
        #------------------------------------------------------

        project_dir = os.path.join(ReportGenConfig.TEMP_DIR, task.get("organizationId"))
        temp_dir, project_dir = setup_directories(ReportGenConfig.TEMP_DIR, project_dir)

        wkhtml_options = {
                            'page-size': 'A4',
                            'margin-bottom': '0',
                            'margin-left': '0',
                            'margin-right': '0',
                            'margin-top': '0',
                            "enable-local-file-access": None,
                            "enable-external-links": None,
                            "enable-internal-links": None,
                            "enable-javascript": None,
                            "javascript-delay": 500,
                            "no-stop-slow-scripts": None,
                            "debug-javascript": None
                        }

        pdf_engine = template_writer.TemplateWriter(
                                                    payload = payload,
                                                    # css_path = os.path.join(os.path.dirname(__file__), "templates", "default", "inspection-report-new.component.css" ),
                                                    css_path= ReportGenConfig.CSS_PATH,
                                                    project_dir=project_dir,
                                                    templates_path = ReportGenConfig.TEMPLATES_DIR, 
                                                    wkhtmltopdf_path = ReportGenConfig.WKHTMLTOPDF_PATH,
                                                    wkhtml_options = wkhtml_options,
                                                    verbose = True,
                                                    debug= True
                                                    )
        # 1
        ret = pdf_engine.generate_front_page()
        print(f"{Fore.GREEN}Front page generated {Fore.RESET}")

        # 2
        # ret = pdf_engine.generate_table_of_content_page()
        # print(f"{Fore.GREEN}Table of content page generated {Fore.RESET}")

        #3
        # ret = pdf_engine.generate_about_page()
        # print(f"{Fore.GREEN}About page generated {Fore.RESET}")

        #3
        # common_pages_content = db_client.get_introduction_template(task.get("SurveyId"), task.get("RequestType") )

        # ret = pdf_engine.generate_solar_common_pages(common_pages_content)
        # print(f"{Fore.GREEN}Solar Common Pages generated {Fore.RESET}")
        
        # #4
        ret = pdf_engine.generate_summary_page()
        print(f"{Fore.GREEN}Summary page generated {Fore.RESET}")

        #5
        # ret = pdf_engine.generate_asset_analysis_page()
        # print(f"{Fore.GREEN}Asset Analysis pages generated {Fore.RESET}")
        
        ret = pdf_engine.generate_annotation_page()
        print(f"{Fore.GREEN}Annotation page generated {Fore.RESET}")

        #6
        

        #7
        # ret = pdf_engine.generate_chart_page()
        # print(f"{Fore.GREEN}Chart page generated {Fore.RESET}")

        #8
        # ret = pdf_engine.generate_thermography_page()
        # print(f"{Fore.GREEN}Thermography page generated {Fore.RESET}")

        #9
        # ret = pdf_engine.generate_execution_plan_pages()
        # print(f"{Fore.GREEN}Execution plan pages generated {Fore.RESET}")

        #10
        # ret = pdf_engine.generate_anomalies_info_page()
        # print(f"{Fore.GREEN}Anomalies info page generated {Fore.RESET}")

        #11
        # ret = pdf_engine.generate_anomaly_page()
        # print(f"{Fore.GREEN}Anomaly page generated {Fore.RESET}")
        
        

        # 12
        print(f"Compressing PDFs")
        # give it some time for PDFs to store in local storage.
        time.sleep(5)
        compressed_pdfs = pdf_engine.compress_pdfs(pdf_engine.generated_pdfs, workers=10)
        print(f"{Fore.GREEN}PDFs compressed{Fore.RESET}")

        # 13
        print("Combining PDFs...")
        pdf_file_path = pdf_engine.combine_pdfs(pdfs=compressed_pdfs, output_file=os.path.join(project_dir, task.get("reportRequestId")+".pdf"))
        print(f"{Fore.GREEN}PDFs combined : {Fore.RESET} {pdf_file_path}")
        # ----------------------------------------------------------------
        # uploading pdf file to s3.

        # 14
        print("Uploading PDF file ... ")
        # aws_manager = AWSManager(
        #                             aws_access_key_id= AWSConfig.AWS_ACCESS_KEY_ID,
        #                             aws_secret_access_key= AWSConfig. AWS_SECRET_ACCESS_KEY,
        #                             region_name= AWSConfig.REGION_NAME,
        #                             bucket_name= AWSConfig.BUCKET_NAME
        #                         )
        
        minio_client = Minio(
                                    MinioConfig.endpoint,
                                    access_key= MinioConfig.access_key,
                                    secret_key= MinioConfig.secret_key,
                                    secure= MinioConfig.secure
                                )
        
        # s3_pdf_file_path = AWSConfig.T_D_REPORTS_DIR.format( SurveyId = task.get("SurveyId") , ReportName = payload.get("SurveyId").replace(' ','_') )
        # s3_pdf_file_path = AWSConfig.T_D_REPORTS_DIR.format( SurveyId = task.get("SurveyId") , ReportName = task.get("reportRequestId") )

        # ret = aws_manager.upload_file(file_path= pdf_file_path, s3_file_path= s3_pdf_file_path)

        s3_pdf_file_path = MinioConfig.PDF_REPORTS_DIR.format(ReportName = f"{task.get('reportRequestId')}_{time.time()}")
        try:
            minio_client.fput_object(bucket_name = MinioConfig.bucket_name,
                                 object_name = s3_pdf_file_path,
                                 file_path = pdf_file_path)
            ret = True
        except Exception as e:
            print(f"Report uploading failed : {e}")
            ret = False

        # generating downloading link.
        if ret:
            if MinioConfig.hostname:
                pdf_download_link = f"{MinioConfig.hostname}/{MinioConfig.bucket_name}/{s3_pdf_file_path}"
            else:
                pdf_download_link = f"http://{MinioConfig.endpoint}/{MinioConfig.bucket_name}/{s3_pdf_file_path}"
            # ret, pdf_download_link = aws_manager.get_download_link(s3_file_path= s3_pdf_file_path, link_expire_time=AWSConfig.PDF_LINK_EXPIRE_TIME)

        if (not ret) or (not bool(pdf_download_link)) :
            raise Exception("Error while generating pdf.")

        # --------------------------------------------------------------------------------------------------------------------------------
        # 11                                                     GENERATING EXCEL

        # print("Generating Excel file ...")

        # excel_file_path = os.path.join(project_dir, task.get("SurveyId")+".xlsx")
        
        # excel_generator = ExcelGenerator(payload=payload)
        # excel_file_path = excel_generator.generate_excel(output_file=excel_file_path)

        # s3_excel_file_path = AWSConfig.SOLAR_EXCEL_DIR.format( SurveyId = task.get("SurveyId") , ReportName = payload.get("SurveyId").replace(' ','_') )
        # s3_excel_file_path = AWSConfig.SOLAR_EXCEL_DIR.format( SurveyId = task.get("SurveyId") , ReportName = task.get("TopicName") )

        # ret = aws_manager.upload_file(file_path= excel_file_path, s3_file_path= s3_excel_file_path)

        # print("excel file file uploading status : ", ret)

        # generating downloading link.
        # if ret:
        #     ret, excel_download_link = aws_manager.get_download_link(s3_file_path= s3_excel_file_path)
            
        # if (not ret) or (not bool(excel_download_link)) :
        #     print("ret : ", ret)
        #     print("excel_download_link : ", excel_download_link)
        #     raise Exception("Error while generating excel file.")


        # MANUAL SUCCESS / FAILED ENTRY ON TOPIC -----------------------------------
    except Exception as e:
        print("ERROR : ", e)
        traceback.print_exc()
        ret = False
        # raise
    
    if ret :
        ret_payload = {
            "reportRequestId" : task.get("reportRequestId"),
            "status" : "2",
            "errorMessage": "",
            "reportUrl" : pdf_download_link
                        }
        
    else:
        ret_payload = {
            "reportRequestId" : task.get("reportRequestId"),
            "status" : "3",
            "errorMessage": "Error while generating report.",
            "reportUrl" : ""
                        }

    # bootstrap_servers = "3.7.46.241:9092"
    # Create Kafka producer
    producer = Producer({'bootstrap.servers': kafka_bootstrap_servers})
    print(f"{Fore.GREEN}sending payload to RESPONSE TOPIC : \n {ret_payload}{Fore.RESET}")
    
    producer.produce(result_response_topic, value= json.dumps(ret_payload))
    producer.flush()

    # .flush() ensures all msgs to be sent before running next instruction,
    # thus no need to close the kafka connection manually confluent-kafka manages it internally
    # url = "http://103.165.30.206:8091/surveillance/Report/"
    # response = requests.post(url, json=ret_payload)
    # print("Response from result response topic post request : ", response.status_code, response.text)

    # ----------------------------------------------------------------
    with open( os.path.join(temp_dir , "Generated_reports.txt"), "a") as f:
        f.write(f"{datetime.now().strftime('%Y/%m/%d_%H:%M:%S::%f')} > REPORT {pdf_download_link}\n{datetime.now().strftime('%Y/%m/%d_%H:%M:%S::%f')} >\n")

    print("Removing Project directory ... ")
    if os.path.exists(project_dir):
        shutil.rmtree(project_dir)
        print("Project directory removed.")
    
    print("Exiting...")

    return ret#, pdf_download_link
    

import os
import shutil

from db_client import DbClient
# create a db_client and connect to it accordingly. to call the stored procedure

import json
import time
from datetime import datetime

import template_writer 
from excel_generator import ExcelGenerator

from report_gen_config import ReportGenConfig, AWSConfig, DBConfig
from colorama import Fore

from awsmanager import AWSManager
from confluent_kafka import Producer, KafkaError

import traceback



 
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
            return data# It is assured that if inspection exists then tree will not be null.
        # inspection_tree = db_client.get_inspection_tree(task.get("InspectionId"))
        # inspection_tree = inspection_tree[0]['Tree']

        # excel_data = db_client.get_excel_data(task.get("SurveyId"), task.get("RequestType"))
        
        # with 
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
    pdf_download_link = None

    try:
        print("inside main function...")
        db_client = DbClient(DBConfig.HOST, DBConfig.PORT, DBConfig.DATABASE, DBConfig.USER, DBConfig.PASSWORD)
        print("Getting report data from the database.")
        # payload = db_client.get_solar_report_data(task.get("SurveyId"),task.get("ObjectStructureIds"),task.get("Annomalies"),task.get("RequestType"))
        payload = db_client.get_ohe_report(task.get("Report").get("SurveyId"),task.get("AssetIds"),task.get("Type"))
        # open("current_excel_data.json", 'w') as f:
        #     json.dump(excel_data, f, indent=4)
        
        # excel_data = excel_data[0]["JsonResultSet"]

        with open("current_payload_new.json", "w") as f:
            json.dump(payload, f , indent=4)
            # payload = json.load(f)




        #------------------------------------------------------
        # payload = {
        #             "SurveyId": "ceb86687-dbba-4b3d-8017-998e58798288",
        #             "SurveyName": "thirteenjanuary",
        #             "SurveyCreatedDate": "2026-01-14T07:04:48.624139+00:00",
        #             "ProjectName": "wholetest",
        #             "SiteName": "noida",
        #             "PlantCapacity": 22,
        #             "ModuleCapacity": 5,
        #             "TotalAffectModules": 3,
        #             "TotalNumberOfModules": 18,
        #             "AnnomalyDetails": [
        #                 {
        #                     "AnnomalyName": "BYPASS DIODE FAILURE",
        #                     "AnnomalyCount": 1,
        #                     "AnomalyColor": "#ff00ff"
        #                 },
        #                 {
        #                     "AnnomalyName": "CELL MISMATCH",
        #                     "AnnomalyCount": 1,
        #                     "AnomalyColor": "#ffff00"
        #                 },
        #                 {
        #                     "AnnomalyName": "MULTIPLE CELL MISMATCH",
        #                     "AnnomalyCount": 1,
        #                     "AnomalyColor": "#0000ff"
        #                 }
        #             ],
        #             "HasAnomalyFilter": False,
        #             "AnnotationCount": 3,
        #             "Blocks": [
        #                 {
        #                     "ObjectStructureId": "b20ee15d-24ca-4a59-9d26-dbaa6dbe581a",
        #                     "ObjectStructureName": "FL-5",
        #                     "ObjectStructureGeoLocation": null,
        #                     "TotalImages": 32,
        #                     "ImagesWithAnnotations": 2,
        #                     "Annotations": [
        #                         {
        #                             "annotation_id": "51739cdc-35a1-4ed6-a9b2-2c43f5be930a",
        #                             "annomaly_name": "CELL MISMATCH",
        #                             "anomaly_color": "#ffff00",
        #                             "annomaly_id": "88dd4d20-2410-4e70-a928-f6de0e17a814",
        #                             "member_name": "",
        #                             "parent_name": "",
        #                             "severity": "LOW",
        #                             "remarks": "CELL MISMATCH",
        #                             "member_id": "00000000-0000-0000-0000-000000000000",
        #                             "member_path": "Block:1 / String:1 / Row:1 / Table:1 / Module:A",
        #                             "annotation_status": "PENDING",
        #                             "created_date": "2026-01-14T07:06:52.714449+00:00",
        #                             "Images": [
        #                                 {
        #                                     "ImageId": "4ba0ee64-64a3-44b6-aa85-9419448672d8",
        #                                     "ImageName": "DJI_20251117140737_0001_V.JPG",
        #                                     "ImageUrl": "https://minio.mapbyvaayu.com/vaayudatarepo/vaayu/rawimages/Solar/surveys/ceb86687-dbba-4b3d-8017-998e58798288/FL-5/DJI_20251117140737_0001_V.JPG",
        #                                     "ImageDate": "Jan 14, 2026",
        #                                     "SensorType": 3,
        #                                     "BaseName": "DJI_20251117140737_0001",
        #                                     "Suffix": "_V",
        #                                     "geometry": {
        #                                         "type": "Polygon",
        #                                         "coordinates": [
        #                                             [
        #                                                 [
        #                                                     574.0153607624934,
        #                                                     1022.569494160974
        #                                                 ],
        #                                                 [
        #                                                     574.0153607624934,
        #                                                     1226.5625762074828
        #                                                 ],
        #                                                 [
        #                                                     821.4112338322567,
        #                                                     1226.5625762074828
        #                                                 ],
        #                                                 [
        #                                                     821.4112338322567,
        #                                                     1022.569494160974
        #                                                 ],
        #                                                 [
        #                                                     574.0153607624934,
        #                                                     1022.569494160974
        #                                                 ]
        #                                             ]
        #                                         ]
        #                                     },
        #                                     "annotation_json": null
        #                                 },
        #                                 {
        #                                     "ImageId": "198e0a86-ea3d-47b4-a6e2-92adb7f951df",
        #                                     "ImageName": "DJI_20251117140737_0001_T.JPG",
        #                                     "ImageUrl": "https://minio.mapbyvaayu.com/vaayudatarepo/vaayu/rawimages/Solar/surveys/ceb86687-dbba-4b3d-8017-998e58798288/FL-5/DJI_20251117140737_0001_T.JPG",
        #                                     "ImageDate": "Jan 14, 2026",
        #                                     "SensorType": 4,
        #                                     "BaseName": "DJI_20251117140737_0001",
        #                                     "Suffix": "_T",
        #                                     "geometry": {
        #                                         "type": "Polygon",
        #                                         "coordinates": [
        #                                             [
        #                                                 [
        #                                                     123,
        #                                                     235
        #                                                 ],
        #                                                 [
        #                                                     123,
        #                                                     168
        #                                                 ],
        #                                                 [
        #                                                     191,
        #                                                     168
        #                                                 ],
        #                                                 [
        #                                                     191,
        #                                                     235
        #                                                 ],
        #                                                 [
        #                                                     123,
        #                                                     235
        #                                                 ]
        #                                             ]
        #                                         ]
        #                                     },
        #                                     "annotation_json": {
        #                                         "MinTemp": 29.6,
        #                                         "MaxTemp": 38.49,
        #                                         "MinTempCoord": [
        #                                             181,
        #                                             187
        #                                         ],
        #                                         "MaxTempCoord": [
        #                                             160,
        #                                             168
        #                                         ],
        #                                         "AvgTemp": 34.05,
        #                                         "DeltaTemp": 8.89,
        #                                         "AmbientTemp": null,
        #                                         "AdjacentTemp": null,
        #                                         "count": null
        #                                     }
        #                                 }
        #                             ]
        #                         },
        #                         {
        #                             "annotation_id": "f6382b2d-1d67-44a2-b4e2-44fb380faadc",
        #                             "annomaly_name": "BYPASS DIODE FAILURE",
        #                             "anomaly_color": "#ff00ff",
        #                             "annomaly_id": "5d884c43-c22b-4790-8508-a89d434536f1",
        #                             "member_name": "",
        #                             "parent_name": "",
        #                             "severity": "HIGH",
        #                             "remarks": "BYPASS DIODE FAILURE",
        #                             "member_id": "00000000-0000-0000-0000-000000000000",
        #                             "member_path": "Block:1 / String:1 / Row:1 / Table:1 / Module:B",
        #                             "annotation_status": "PENDING",
        #                             "created_date": "2026-01-14T07:09:55.229785+00:00",
        #                             "Images": [
        #                                 {
        #                                     "ImageId": "d18aae95-5761-4e0f-b8ac-c8fe335ffdb2",
        #                                     "ImageName": "DJI_20251117140740_0003_V.JPG",
        #                                     "ImageUrl": "https://minio.mapbyvaayu.com/vaayudatarepo/vaayu/rawimages/Solar/surveys/ceb86687-dbba-4b3d-8017-998e58798288/FL-5/DJI_20251117140740_0003_V.JPG",
        #                                     "ImageDate": "Jan 14, 2026",
        #                                     "SensorType": 3,
        #                                     "BaseName": "DJI_20251117140740_0003",
        #                                     "Suffix": "_V",
        #                                     "geometry": {
        #                                         "type": "Polygon",
        #                                         "coordinates": [
        #                                             [
        #                                                 [
        #                                                     539.2931517857478,
        #                                                     979.1667031377197
        #                                                 ],
        #                                                 [
        #                                                     539.2931517857478,
        #                                                     1131.0764585886116
        #                                                 ],
        #                                                 [
        #                                                     795.3695402147241,
        #                                                     1131.0764585886116
        #                                                 ],
        #                                                 [
        #                                                     795.3695402147241,
        #                                                     979.1667031377197
        #                                                 ],
        #                                                 [
        #                                                     539.2931517857478,
        #                                                     979.1667031377197
        #                                                 ]
        #                                             ]
        #                                         ]
        #                                     },
        #                                     "annotation_json": null
        #                                 },
        #                                 {
        #                                     "ImageId": "11cfdbfb-9578-4134-98ab-b5248348637b",
        #                                     "ImageName": "DJI_20251117140740_0003_T.JPG",
        #                                     "ImageUrl": "https://minio.mapbyvaayu.com/vaayudatarepo/vaayu/rawimages/Solar/surveys/ceb86687-dbba-4b3d-8017-998e58798288/FL-5/DJI_20251117140740_0003_T.JPG",
        #                                     "ImageDate": "Jan 14, 2026",
        #                                     "SensorType": 4,
        #                                     "BaseName": "DJI_20251117140740_0003",
        #                                     "Suffix": "_T",
        #                                     "geometry": {
        #                                         "type": "Polygon",
        #                                         "coordinates": [
        #                                             [
        #                                                 [
        #                                                     74,
        #                                                     178
        #                                                 ],
        #                                                 [
        #                                                     74,
        #                                                     122
        #                                                 ],
        #                                                 [
        #                                                     167,
        #                                                     122
        #                                                 ],
        #                                                 [
        #                                                     167,
        #                                                     178
        #                                                 ],
        #                                                 [
        #                                                     74,
        #                                                     178
        #                                                 ]
        #                                             ]
        #                                         ]
        #                                     },
        #                                     "annotation_json": {
        #                                         "MinTemp": 28.14,
        #                                         "MaxTemp": 38.02,
        #                                         "MinTempCoord": [
        #                                             76,
        #                                             147
        #                                         ],
        #                                         "MaxTempCoord": [
        #                                             166,
        #                                             159
        #                                         ],
        #                                         "AvgTemp": 33.08,
        #                                         "DeltaTemp": 9.880000000000003,
        #                                         "AmbientTemp": null,
        #                                         "AdjacentTemp": null,
        #                                         "count": null
        #                                     }
        #                                 }
        #                             ]
        #                         },
        #                         {
        #                             "annotation_id": "19e6f10a-df35-4c8e-9a10-7bbf1437a465",
        #                             "annomaly_name": "MULTIPLE CELL MISMATCH",
        #                             "anomaly_color": "#0000ff",
        #                             "annomaly_id": "943aac69-28bf-4884-8351-f55d44d33552",
        #                             "member_name": "",
        #                             "parent_name": "",
        #                             "severity": "MEDIUM",
        #                             "remarks": "MULTIPLE CELL MISMATCH",
        #                             "member_id": "00000000-0000-0000-0000-000000000000",
        #                             "member_path": "Block:1 / String:1 / Row:1 / Table:1 / Module:C",
        #                             "annotation_status": "PENDING",
        #                             "created_date": "2026-01-14T07:10:53.479723+00:00",
        #                             "Images": [
        #                                 {
        #                                     "ImageId": "4ba0ee64-64a3-44b6-aa85-9419448672d8",
        #                                     "ImageName": "DJI_20251117140737_0001_V.JPG",
        #                                     "ImageUrl": "https://minio.mapbyvaayu.com/vaayudatarepo/vaayu/rawimages/Solar/surveys/ceb86687-dbba-4b3d-8017-998e58798288/FL-5/DJI_20251117140737_0001_V.JPG",
        #                                     "ImageDate": "Jan 14, 2026",
        #                                     "SensorType": 3,
        #                                     "BaseName": "DJI_20251117140737_0001",
        #                                     "Suffix": "_V",
        #                                     "geometry": {
        #                                         "type": "Polygon",
        #                                         "coordinates": [
        #                                             [
        #                                                 [
        #                                                     543.6334428090022,
        #                                                     1309.0278672307372
        #                                                 ],
        #                                                 [
        #                                                     543.6334428090022,
        #                                                     1469.6181582539916
        #                                                 ],
        #                                                 [
        #                                                     817.0709428090023,
        #                                                     1469.6181582539916
        #                                                 ],
        #                                                 [
        #                                                     817.0709428090023,
        #                                                     1309.0278672307372
        #                                                 ],
        #                                                 [
        #                                                     543.6334428090022,
        #                                                     1309.0278672307372
        #                                                 ]
        #                                             ]
        #                                         ]
        #                                     },
        #                                     "annotation_json": null
        #                                 },
        #                                 {
        #                                     "ImageId": "198e0a86-ea3d-47b4-a6e2-92adb7f951df",
        #                                     "ImageName": "DJI_20251117140737_0001_T.JPG",
        #                                     "ImageUrl": "https://minio.mapbyvaayu.com/vaayudatarepo/vaayu/rawimages/Solar/surveys/ceb86687-dbba-4b3d-8017-998e58798288/FL-5/DJI_20251117140737_0001_T.JPG",
        #                                     "ImageDate": "Jan 14, 2026",
        #                                     "SensorType": 4,
        #                                     "BaseName": "DJI_20251117140737_0001",
        #                                     "Suffix": "_T",
        #                                     "geometry": {
        #                                         "type": "Polygon",
        #                                         "coordinates": [
        #                                             [
        #                                                 [
        #                                                     124,
        #                                                     306
        #                                                 ],
        #                                                 [
        #                                                     124,
        #                                                     258
        #                                                 ],
        #                                                 [
        #                                                     198,
        #                                                     258
        #                                                 ],
        #                                                 [
        #                                                     198,
        #                                                     306
        #                                                 ],
        #                                                 [
        #                                                     124,
        #                                                     306
        #                                                 ]
        #                                             ]
        #                                         ]
        #                                     },
        #                                     "annotation_json": {
        #                                         "MinTemp": 29.36,
        #                                         "MaxTemp": 38.02,
        #                                         "MinTempCoord": [
        #                                             189,
        #                                             300
        #                                         ],
        #                                         "MaxTempCoord": [
        #                                             161,
        #                                             262
        #                                         ],
        #                                         "AvgTemp": 33.69,
        #                                         "DeltaTemp": 8.660000000000004,
        #                                         "AmbientTemp": null,
        #                                         "AdjacentTemp": null,
        #                                         "count": null
        #                                     }
        #                                 }
        #                             ]
        #                         }
        #                     ]
        #                 }
        #             ]
        #         }

        project_dir = os.path.join(ReportGenConfig.TEMP_DIR, task.get("Report").get("SurveyId"))
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
        # request_type = "s"
        # common_pages_content = db_client.get_introduction_template(task.get("SurveyId"), request_type )

        # ret = pdf_engine.generate_solar_common_pages(common_pages_content)
        # print(f"{Fore.GREEN}Solar Common Pages generated {Fore.RESET}")
        
        #4
        ret = pdf_engine.generate_summary_page()
        print(f"{Fore.GREEN}Summary page generated {Fore.RESET}")
        
        #5
        ret = pdf_engine.generate_asset_analysis_page()
        print(f"{Fore.GREEN}Asset Analysis pages generated {Fore.RESET}")
        
        ret = pdf_engine.generate_annotation_page()
        print(f"{Fore.GREEN}Annotation page generated {Fore.RESET}")

        #6
        

        #7
        # ret = pdf_engine.generate_chart_page()
        print(f"{Fore.GREEN}Chart page generated {Fore.RESET}")

        #8
        # ret = pdf_engine.generate_thermography_page()
        print(f"{Fore.GREEN}Thermography page generated {Fore.RESET}")

        #9
        # ret = pdf_engine.generate_execution_plan_pages()
        # print(f"{Fore.GREEN}Execution plan pages generated {Fore.RESET}")

        #10
        # ret = pdf_engine.generate_anomalies_info_page()
        print(f"{Fore.GREEN}Anomalies info page generated {Fore.RESET}")

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
        pdf_file_path = pdf_engine.combine_pdfs(pdfs=compressed_pdfs, output_file=os.path.join(project_dir, task.get("Report").get("SurveyId")+".pdf"))
        print(f"{Fore.GREEN}PDFs combined : {Fore.RESET} {pdf_file_path}")

        # ----------------------------------------------------------------)
        # uploading pdf file to s3.
        # 14
        print("Uploading PDF file ... ")
        aws_manager = AWSManager(
                                    aws_access_key_id= AWSConfig.AWS_ACCESS_KEY_ID,
                                    aws_secret_access_key= AWSConfig. AWS_SECRET_ACCESS_KEY,
                                    region_name= AWSConfig.REGION_NAME,
                                    bucket_name= AWSConfig.BUCKET_NAME
                                )
        
        # s3_pdf_file_path = AWSConfig.T_D_REPORTS_DIR.format( SurveyId = task.get("SurveyId") , ReportName = payload.get("SurveyId").replace(' ','_') )
        s3_pdf_file_path = AWSConfig.T_D_REPORTS_DIR.format( SurveyId = task.get("Report").get("SurveyId") , ReportName = task.get("Report").get("SurveyId"))

        ret = aws_manager.upload_file(file_path= pdf_file_path, s3_file_path= s3_pdf_file_path)

        # generating downloading link.
        if ret:
            ret, pdf_download_link = aws_manager.get_download_link(s3_file_path= s3_pdf_file_path, link_expire_time=AWSConfig.PDF_LINK_EXPIRE_TIME)

        if (not ret) or (not bool(pdf_download_link)) :
            raise Exception("Error while generating pdf.")


        # --------------------------------------------------------------------------------------------------------------------------------
        # 11                                                     GENERATING EXCEL

        # print("Generating Excel file ...")

        # excel_file_path = os.path.join(project_dir, task.get("SurveyId")+".xlsx")
        
        # excel_generator = ExcelGenerator(payload=payload)
        # excel_file_path = excel_generator.generate_excel(output_file=excel_file_path)

        # # s3_excel_file_path = AWSConfig.SOLAR_EXCEL_DIR.format( SurveyId = task.get("SurveyId") , ReportName = payload.get("SurveyId").replace(' ','_') )
        # s3_excel_file_path = AWSConfig.SOLAR_EXCEL_DIR.format( SurveyId = task.get("SurveyId") , ReportName = task.get("TopicName") )

        # ret = aws_manager.upload_file(file_path= excel_file_path, s3_file_path= s3_excel_file_path)

        # print("excel file file uploading status : ", ret)

        # # generating downloading link.
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
        ret_payload = {"ReportDownloadId":task.get("Report").get("ReportDownloadId"),
                        "SurveyId":task.get("Report").get("SurveyId"),
                        "ReportUrl": pdf_download_link,
                        "ReportStatusEnum":1,
                        "GeneratedOn":datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%fZ")
                        }
        
    else:
        ret_payload = {"ReportDownloadId":task.get("Report").get("ReportDownloadId"),
                        "SurveyId":task.get("Report").get("SurveyId"),
                        "ReportUrl": None,
                        "ReportStatusEnum":2,
                        "GeneratedOn":datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%fZ")
                        }


    # bootstrap_servers = "3.7.46.241:9092"
    # Create Kafka producer
    producer = Producer({'bootstrap.servers': kafka_bootstrap_servers})
    print(f"{Fore.GREEN}sending payload to RESPONSE TOPIC : \n {ret_payload}{Fore.RESET}")
    
    producer.produce(result_response_topic, value= json.dumps(ret_payload))
    producer.flush()

    # .flush() ensures all msgs to be sent before running next instruction,
    # thus no need to close the kafka connection manually confluent-kafka manages it internally

    # ----------------------------------------------------------------
    with open( os.path.join(temp_dir , "Generated_reports.txt"), "a") as f:
        f.write(f"{datetime.now().strftime('%Y/%m/%d_%H:%M:%S::%f')} > REPORT {pdf_download_link}\n{datetime.now().strftime('%Y/%m/%d_%H:%M:%S::%f')} >")

    print("Removing Project directory ... ")
    if os.path.exists(project_dir):
        shutil.rmtree(project_dir)
        print("Project directory removed.")
    
    print("Exiting...")

    return ret#, pdf_download_link
    

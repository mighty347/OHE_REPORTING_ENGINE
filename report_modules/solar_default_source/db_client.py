import copy
import time
import psycopg2
from colorama import Fore

class DbClient():
    conn_args:dict

    def __init__(self, host:str, port:int, database:str, user:str, password:str):
        self.conn_args = {
                            "host": host,
                            "port": port,
                            "database": database,
                            "user": user,
                            "password": password
                        }

    def get_solar_report_data(self, survey_id:str,objectstructure_id:str,annomalies:str,report_type:str)  :
        result = None
        try:
            # print(f"connecting to pg_admin via connection string : {self.conn_args}")
            connection = psycopg2.connect(**self.conn_args)
            print("pg admin connected.")
            cursor = connection.cursor()
            print("calling stored procedure.")

            print(f"{survey_id=} , {objectstructure_id=} , {annomalies=} , {report_type=}")
            cursor.callproc('getsolarreportbyobjectstructureids', [survey_id,objectstructure_id,annomalies,report_type,])
            # cursor.callproc('getsolarreportbyobjectstructureids', [survey_id,objectstructure_id,])
            
            print("fetching the data from db.")
            result = cursor.fetchone()
            try:
                result = result[0] # get the first element of the tuple
                result = result["data"]["survey"][0]
            except Exception as e:
                print("Error while fetching the data : ",e)
                pass
        
        except (Exception, psycopg2.DatabaseError) as error:
            print(f"{Fore.RED}{error}{Fore.RESET}")
            result=None
            return
        
        finally:
            if connection:
                cursor.close()
                connection.close()

        return result
    



    def get_introduction_template(self, survey_id:str, request_type:str):
        result = None
        try:
            print("connecting to pg_admin")
            connection = psycopg2.connect(**self.conn_args)
            print("pg admin connected.")
            cursor = connection.cursor()
            print("calling introduction template stored procedure.")
            cursor.callproc('gettemplatebysurveyid', [survey_id, request_type, ])
            print("fetching the introduction template data from db.")
            result = cursor.fetchone()
            print("data fetched.")
            try:
                result = result[0] # get the first element of the tuple
            except Exception as e:
                print("Error while fetching the data : ",e)
                pass
        
        except (Exception, psycopg2.DatabaseError) as error:
            print(f"{Fore.RED}{error}{Fore.RESET}")
            result=None
            return
        
        finally:
            if connection:
                cursor.close()
                connection.close()

        # print(f"result : {result}")

        return result


    def get_excel_data(self, inspection_id:str, request_type:str):
        result = None
        try:
            print("connecting to pg_admin")
            connection = psycopg2.connect(**self.conn_args)
            print("pg admin connected.")
            cursor = connection.cursor()
            print("calling inspection tree procedure.")
            cursor.callproc('getexcelbyinspectionid', [inspection_id, request_type,])
            print("fetching inspection tree data from db.")
            result = cursor.fetchone()
            print("data fetched.")
            try:
                result = result[0] # get the first element of the tuple
            except Exception as e:
                print("Error while fetching the data : ",e)
                pass
        
        except (Exception, psycopg2.DatabaseError) as error:
            print(f"{Fore.RED}{error}{Fore.RESET}")
            result=None
            return
        
        finally:
            if connection:
                cursor.close()
                connection.close()

        print(f"result : {result}")

        return result
    
    
    def get_ohe_report(self, survey_id: str, asset_ids: list, report_type: int):
        result = None
        connection = None
        cursor = None

        try:
            print("connecting to pg_admin")
            connection = psycopg2.connect(**self.conn_args)
            print("pg admin connected.")

            cursor = connection.cursor()
            print("calling ohe report function.")

            query = """
                SELECT fn_get_ohe_report(%s, %s::uuid[], %s);
            """

            cursor.execute(query, (survey_id, asset_ids, report_type))

            print("fetching ohe report data from db.")
            result = cursor.fetchone()

            if result:
                result = result[0]

            print("data fetched.")

        except (Exception, psycopg2.DatabaseError) as error:
            print(error)
            result = None

        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()

        return result



# class DBConfig(object):
#     HOST='192.168.0.31'
#     PORT=5432
#     DATABASE="BLHWK-DEV-INSPECTION"
#     USER="postgres"
#     PASSWORD="postgres"



class DBConfig(object):
    # HOST='192.168.0.206'
    HOST='13.234.231.168'
    PORT=5432
    # DATABASE="BLHWK-DEV-INSPECTION"
    # DATABASE="BLHWK-DEV-INSPECTION-LATEST"
    DATABASE="NTPC_VISUALIZATION"
    USER="postgres"
    PASSWORD="root"



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

# db_client = DbClient(DBConfig.HOST, DBConfig.PORT, DBConfig.DATABASE, DBConfig.USER, DBConfig.PASSWORD)
# response = db_client.get_solar_report_data('97a8dccb-846d-422f-8356-7a4ac364dd46')
# excel_data = db_client.get_excel_data("09254cf1-1689-4be7-8bdc-00816eaa9eba", "T")

# print("requested _ data : \n", json.dumps(excel_data, indent=4))

# payload = db_client.get_inspection_tree("0687932c-199f-4e00-a6b5-8b630db866bb")
# tree = payload[0]['Tree']
# print("type of tree : ", type(tree))

# payload = db_client.get_report_data("c537b6dd-6397-4daf-abdd-f04814e944c1", 'w')

# print(payload)

# print("Formatted json : ")
# print(json.dumps(json.loads(payload), indent=4))
# # db_client.super_access_create_db()
# print("Exiting ...")

# payload = parse_nested_json(payload[0].get("dataVisual")[0])
# with open("testjson.json",'w') as f:
#     json.dump(payload,f,indent=4)

# for tower in payload.get("Towers")[0]:
#     for image in tower.get("Images"):
#         annotation = image.get("Annotations")
#         if not annotation is None:
#             try:
#                 annotation = json.loads(annotation)
#             except:
#                 print("annotation json loading error")
            

# print("breakpoint_2")

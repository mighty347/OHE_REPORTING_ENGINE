import os

class ReportGenConfig(object):
    """
    Report generation parameters configurations.
    """
    TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), 'html_templates')
    CSS_PATH = os.path.join(TEMPLATES_DIR, "temp.css")

    REPORTS_DIR = os.path.join(os.getcwd(), 'Generated_Reports')
    TEMP_DIR = os.path.join(os.getcwd(), 'temp')

    # PDF_SHARD_SIZE = 20

    WKHTMLTOPDF_PATH = "/usr/bin/wkhtmltopdf"

    LOG_PATH = os.path.join(os.getcwd(),"logs")
    LOG_FILENAME = "report_generator_logs.log"

class AWSConfig(object):
    """
    AWS parameters configurations.
    """
    # AWS_ACCESS_KEY_ID = 'None'
    # AWS_SECRET_ACCESS_KEY = 'None'
    # Key changed due to user delete
    AWS_ACCESS_KEY_ID = 'None'
    AWS_SECRET_ACCESS_KEY = 'None'
    REGION_NAME = 'None'
    BUCKET_NAME = 'None'
    T_D_REPORTS_DIR = 'reports/surveillance/{ReportName}.pdf'
    SOLAR_EXCEL_DIR = 'reports/vaayu/Solar/{SurveyId}/{ReportName}.xlsx'

    # PDF_LINK_EXPIRE_TIME = 3600 * 24 # 24 hour
    # EXCEL_LINK_EXPIRE_TIME = 3600 * 24 # 24 hour

    PDF_LINK_EXPIRE_TIME = None
    EXCEL_LINK_EXPIRE_TIME = None

class MinioConfig(object):
    bucket_name= "surveillanceprod"
    endpoint= "minio:9000"
    hostname= "http://192.168.1.110:9000"
    access_key= "surveillanceadmin"
    secret_key= "surveillanceadmin123"
    secure= False
    PDF_REPORTS_DIR = 'reports/surveillance/{ReportName}.pdf'




# class DBConfig(object):
#     HOST='10.0.2.42'
#     PORT=5432
#     DATABASE="NTPC_VISUALIZATION"
#     USER="ntpcdbadmin"
#     PASSWORD="nt#pc@ii$dm&db"


class DBConfig(object):
    """
    Production
    """
    HOST='host.docker.internal'
    PORT=5432
    DATABASE="Surveillance_Yugmi"
    USER="postgres"
    PASSWORD="postgres"

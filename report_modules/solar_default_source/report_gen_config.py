import os
from dotenv import load_dotenv

load_dotenv()


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
    # AWS_ACCESS_KEY_ID = 'YOUR_ACCESS_KEY_ID'
    # AWS_SECRET_ACCESS_KEY = 'YOUR_SECRET_ACCESS_KEY'
    # Key changed due to user delete
    AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID', 'YOUR_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY', 'YOUR_SECRET_ACCESS_KEY')
    REGION_NAME = 'ap-south-1'
    BUCKET_NAME = 'coredatarepo'
    T_D_REPORTS_DIR = 'reports/ohe/{SurveyId}/{ReportName}.pdf'
    SOLAR_EXCEL_DIR = 'reports/ohe/{SurveyId}/{ReportName}.xlsx'

    # PDF_LINK_EXPIRE_TIME = 3600 * 24 # 24 hour
    # EXCEL_LINK_EXPIRE_TIME = 3600 * 24 # 24 hour

    PDF_LINK_EXPIRE_TIME = None
    EXCEL_LINK_EXPIRE_TIME = None


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
    HOST='192.168.1.56'
    PORT= 6011
    DATABASE= "visualization_bridge_inspection"
    USER="postgres"
    PASSWORD = os.getenv('DB_PASSWORD', 'postgres')

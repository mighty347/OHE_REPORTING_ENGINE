# MODE = 'DEVELOPMENT'
MODE = 'PRODUCTION'


# For DEVELOPMENT
class CELERY_REPORT_CONFIG_development(object):
    BACKEND = 'redis://:Intelly@127.0.0.1:6379'
    BROKER = 'redis://:Intelly@127.0.0.1:6379'
    TASK_QUEUE = 'dev_report_task_queue'



# For PRODUCTION
class CELERY_REPORT_CONFIG_production(object):
    BACKEND = 'redis://:Intelly@127.0.0.1:6379'
    BROKER = 'redis://:Intelly@127.0.0.1:6379'
    TASK_QUEUE = 'prod_report_task_queue'
    


class CELERY_REPORT_CONFIG ( CELERY_REPORT_CONFIG_development if (MODE=="DEVELOPMENT") else \
                    CELERY_REPORT_CONFIG_production if (MODE=="PRODUCTION") \
                    else CELERY_REPORT_CONFIG_development ) :
    pass

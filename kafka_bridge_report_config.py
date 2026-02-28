# MODE = 'DEVELOPMENT'
# MODE = 'PRODUCTION'

# MODE = 'INSPECTION'
MODE = 'IOCL'


# For DEVELOPMENT
class KafkaConfigDevelopment(object):
    BOOTSTRAP_SERVERS = "15.206.68.206:9092"
    # SUBSCRIBE_TOPIC = "AI_client"
    SUBSCRIBE_TOPIC = "DEV-AI-REPORT-PROCESS-REQUEST"
    RESPONSE_TOPIC = "DEV-AI-REPORT-PROCESS-RESPONSE"
    GROUP_ID = 'dev_ai_bridge'

# For PRODUCTION
class KafkaConfigProduction(object):
    BOOTSTRAP_SERVERS = "15.206.68.206:9092"
    # SUBSCRIBE_TOPIC = "AI_client"
    SUBSCRIBE_TOPIC = "PROD-AI-REPORT-PROCESS-REQUEST"
    RESPONSE_TOPIC = "PROD-AI-REPORT-PROCESS-RESPONSE"
    
    GROUP_ID = 'prod_ai_bridge'


class KafkaConfigInspection(object):
    BOOTSTRAP_SERVERS = "15.206.68.206:9092"
    # SUBSCRIBE_TOPIC = "AI_client"
    SUBSCRIBE_TOPIC = "surveillance-report-requests-to-ai"
    RESPONSE_TOPIC = "surveillance-report-requests-from-ai"
    
    GROUP_ID = 'inspection_consumer_bridge'

class KafkaConfigIocl(object):
    BOOTSTRAP_SERVERS = "kafka:9092"
    # SUBSCRIBE_TOPIC = "AI_client"
    SUBSCRIBE_TOPIC = "surveillance-iocl-prod-report-request"
    RESPONSE_TOPIC = "surveillance-iocl-prod-report-response"
    
    GROUP_ID = 'iocl_consumer_bridge'


class KafkaConfig ( KafkaConfigDevelopment if (MODE=="DEVELOPMENT") else \
                    KafkaConfigProduction if (MODE=="PRODUCTION") else \
                    KafkaConfigInspection if (MODE=="INSPECTION") else \
                    KafkaConfigIocl if (MODE=="IOCL") \
                    else KafkaConfigDevelopment ) :
    pass



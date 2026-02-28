import sys
import kafka_bridge_report


# Ensure print statements are flushed immediately
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

if __name__=="__main__":
    kafka_bridge_report.main()
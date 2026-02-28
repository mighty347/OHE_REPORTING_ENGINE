
# Reporting Engine

This project sets up and runs the Reporting Engine, which includes services for Redis, Celery workers, Kafka listeners, and PDF processing using Ghostscript.
---

## Docker installation

```bash
docker build --tag 'reporting_engine_survey:latest' .
```
```bash
docker run -it --name prod_reporting_engine -p 6379:6379 reporting_engine_survey:latest
```
---

## 🧰 Dependencies

### 1. Install Redis Server
```bash
sudo apt-get install redis-server
```

- Edit the Redis config to set a password:
```bash
sudo nano /etc/redis/redis.conf
# Uncomment and modify the line:
requirepass GarudaAI
```

- Restart Redis:
```bash
sudo systemctl restart redis
```

### 2. Install Ghostscript
```bash
sudo apt-get install ghostscript
```

### 3. Install wkhtmltopdf via apt-get or download from link https://wkhtmltopdf.org/downloads.html
tested version (0.12.6)
```bash
sudo apt-get install wkhtmltopdf
```

---

## 🐍 Python Environment Setup

### Create and activate a virtual environment:
```bash
python -m venv ntpc_reporting_engine_venv
source ./ntpc_reporting_engine_venv/bin/activate
```

### Install dependencies:
```bash
pip install -r requirements.txt
```

---

## 🔧 Build

Run the build script to compile and generate files in the `build/` directory:\
Note: build in the save python version in which you are planning to deploy tested (3.10).
```bash
python build.py build_ext clean
```

---

## 🚀 Running Instructions

### Option 1: Using the startup script
Run the preconfigured startup script from the `build/` directory:
```bash
./start_reporting_service.sh
```

### Option 2: As a systemd service
1. Copy the service file:
```bash
sudo cp ntpc_reporting_engine.service /etc/systemd/system/ntpc_reporting_engine.service
```

2. Enable and start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable ntpc_reporting_engine.service
sudo systemctl start ntpc_reporting_engine.service
```

### Option 3: Run manually
Start the Celery worker:
```bash
celery -A celery_report_gen worker -l info -Q prod_tnd_report_task_queue --pool threads --concurrency 1
```

Then start the Kafka listener:
```bash
python kafka_listener.py
```

---

## 📝 Notes

- Ensure Redis is running and accessible with the correct password.
- Python version should match the one supported by `requirements.txt`.
- Kafka must be set up and running for the listener to function.

---

## 📂 Project Structure (Simplified)
```
├── build/
├── requirements.txt
├── build.py
├── kafka_listener.py
├── celery_report_gen.py
├── start_reporting_service.sh
└── ntpc_reporting_engine.service
```


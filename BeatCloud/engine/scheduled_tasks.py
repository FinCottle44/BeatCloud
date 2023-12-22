# cleanup_tasks.py
import os, time, shutil
from celery import Celery
from urllib.parse import quote_plus

### Celery setup
from celery import Celery
from celery.backends import dynamodb
msg_aws_id = quote_plus(os.environ['AWS_MSG_ACCESS_KEY_ID'])
msg_aws_key = quote_plus(os.environ['AWS_MSG_SECRET_ACCESS_KEY'])
c_app = Celery('BeatCloud', broker=f"sqs://{msg_aws_id}:{msg_aws_key}@")
c_app.conf.broker_transport_options = {
    'region': 'eu-west-2',
    'polling_interval': 10
}
read_credits = write_credits = 1 
c_app.conf.result_backend = f"dynamodb://{os.environ['AWS_DB_ACCESS_KEY_ID']}:{os.environ['AWS_DB_SECRET_ACCESS_KEY']}@eu-west-2/celery?read={read_credits}&write={write_credits}"

# Schedule the cleanup task every 6 hours
c_app.conf.beat_schedule = {
    'cleanup-task': {
        'task': 'scheduled_tasks.cleanup_task',
        'schedule': 6 * 60 * 60,  # in seconds (6 hours)
    },
}

@c_app.task
def cleanup_task():
    root_directory = "/app/instance/temp"
    max_age_hours = 6

    current_time = time.time()
    max_age_seconds = max_age_hours * 3600

    for dirpath, dirnames, filenames in os.walk(root_directory, topdown=False):
        for dirname in dirnames:
            current_path = os.path.join(dirpath, dirname)
            try:
                # Get the last modification time of the directory
                directory_time = os.path.getmtime(current_path)

                # Check if the directory is older than the threshold
                if current_time - directory_time > max_age_seconds:
                    print(f"Deleting {current_path} as age over {max_age_seconds} seconds.")
                    shutil.rmtree(current_path)
            except OSError as e:
                print(e)
                pass
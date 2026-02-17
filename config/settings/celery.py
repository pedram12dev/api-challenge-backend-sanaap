from config.env import env

# https://docs.celeryproject.org/en/stable/userguide/configuration.html

# RabbitMQ as message broker
CELERY_BROKER_URL = env("CELERY_BROKER_URL", default="amqp://guest:guest@localhost:5672//")

# Store task results in Django DB
CELERY_RESULT_BACKEND = "django-db"

CELERY_TIMEZONE = "UTC"

CELERY_TASK_SOFT_TIME_LIMIT = 20  # seconds
CELERY_TASK_TIME_LIMIT = 30  # seconds
CELERY_TASK_MAX_RETRIES = 3

CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True

CELERY_BEAT_SCHEDULE = {
    "cleanup_orphaned_files": {
        "task": "apichallenge.documents.tasks.cleanup_orphaned_files",
        "schedule": 86400,  # once a day
    },
}
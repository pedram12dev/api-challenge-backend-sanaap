#!/bin/sh

echo "--> Waiting for database..."
./wait-for-it.sh db:5432 -- echo "Database is ready."

echo "--> Waiting for RabbitMQ..."
./wait-for-it.sh rabbitmq:5672 -- echo "RabbitMQ is ready."

echo "--> Starting Celery beat..."
celery -A config.celery beat \
    -l info \
    --scheduler django_celery_beat.schedulers:DatabaseScheduler
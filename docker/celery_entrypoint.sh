#!/bin/sh

echo "--> Waiting for database..."
./wait-for-it.sh db:5432 -- echo "Database is ready."

echo "--> Waiting for RabbitMQ..."
./wait-for-it.sh rabbitmq:5672 -- echo "RabbitMQ is ready."

echo "--> Starting Celery worker..."
celery -A config.celery worker \
    -l info \
    --without-gossip \
    --without-mingle \
    --without-heartbeat
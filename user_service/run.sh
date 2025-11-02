#!/bin/sh
# wait-for-kafka.sh
set -e

host="$1"
shift
cmd="$@"

until nc -z "$host" 9092; do
  echo "Waiting for Kafka at $host:9092..."
  sleep 3
done

exec $cmd

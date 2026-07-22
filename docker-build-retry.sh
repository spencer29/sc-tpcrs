#!/bin/bash
# Retry docker compose build with exponential backoff

MAX_RETRIES=3
RETRY_DELAY=10

for attempt in $(seq 1 $MAX_RETRIES); do
  echo "Build attempt $attempt of $MAX_RETRIES..."
  docker compose up -d --build
  
  if [ $? -eq 0 ]; then
    echo "✓ Build successful"
    exit 0
  fi
  
  if [ $attempt -lt $MAX_RETRIES ]; then
    echo "✗ Build failed, retrying in ${RETRY_DELAY}s..."
    sleep $RETRY_DELAY
    RETRY_DELAY=$((RETRY_DELAY * 2))
  fi
done

echo "✗ Build failed after $MAX_RETRIES attempts"
exit 1

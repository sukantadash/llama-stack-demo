#!/usr/bin/env bash

# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the terms described in the LICENSE file in
# the root directory of this source tree.

# Telemetry Setup Script for Llama Stack
# This script sets up Jaeger, OpenTelemetry Collector, Prometheus, and Grafana using Podman
# For whoever is interested in testing the telemetry stack, you can run this script to set up the stack.
#    export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318
#    export TELEMETRY_SINKS=otel_trace,otel_metric
#    export OTEL_SERVICE_NAME=my-llama-app
# Then run the distro server

set -Eeuo pipefail

CONTAINER_RUNTIME=${CONTAINER_RUNTIME:-docker}

echo "🚀 Setting up telemetry stack for Llama Stack using Podman..."

if ! command -v "$CONTAINER_RUNTIME" &> /dev/null; then
  echo "🚨 $CONTAINER_RUNTIME could not be found"
  echo "Docker or Podman is required. Install Docker: https://docs.docker.com/get-docker/ or Podman: https://podman.io/getting-started/installation"
  exit 1
fi

# Create a network for the services
echo "📡 Creating $CONTAINER_RUNTIME network..."
$CONTAINER_RUNTIME network create llama-telemetry 2>/dev/null || echo "Network already exists"

# Stop and remove existing containers
echo "🧹 Cleaning up existing containers..."
$CONTAINER_RUNTIME stop jaeger otel-collector prometheus grafana 2>/dev/null || true
$CONTAINER_RUNTIME rm jaeger otel-collector prometheus grafana 2>/dev/null || true

# Start Jaeger
echo "🔍 Starting Jaeger..."
$CONTAINER_RUNTIME run -d --name jaeger \
  --network llama-telemetry \
  -e COLLECTOR_ZIPKIN_HOST_PORT=:9411 \
  -p 16686:16686 \
  -p 14250:14250 \
  -p 9411:9411 \
  docker.io/jaegertracing/all-in-one:latest

# Start OpenTelemetry Collector
echo "📊 Starting OpenTelemetry Collector..."
$CONTAINER_RUNTIME run -d --name otel-collector \
  --network llama-telemetry \
  -p 4318:4318 \
  -p 4317:4317 \
  -p 9464:9464 \
  -p 13133:13133 \
  -v $(pwd)/otel-collector-config.yaml:/etc/otel-collector-config.yaml:Z \
  docker.io/otel/opentelemetry-collector-contrib:latest \
  --config /etc/otel-collector-config.yaml

# Start Prometheus
echo "📈 Starting Prometheus..."
$CONTAINER_RUNTIME run -d --name prometheus \
  --network llama-telemetry \
  -p 9090:9090 \
  -v $(pwd)/prometheus.yml:/etc/prometheus/prometheus.yml:Z \
  docker.io/prom/prometheus:latest \
  --config.file=/etc/prometheus/prometheus.yml \
  --storage.tsdb.path=/prometheus \
  --web.console.libraries=/etc/prometheus/console_libraries \
  --web.console.templates=/etc/prometheus/consoles \
  --storage.tsdb.retention.time=200h \
  --web.enable-lifecycle

# Start Grafana
echo "📊 Starting Grafana..."
$CONTAINER_RUNTIME run -d --name grafana \
  --network llama-telemetry \
  -p 3000:3000 \
  -e GF_SECURITY_ADMIN_PASSWORD=admin \
  -e GF_USERS_ALLOW_SIGN_UP=false \
  docker.io/grafana/grafana:latest

# Wait for services to start
echo "⏳ Waiting for services to start..."
sleep 10

# Check if services are running
echo "🔍 Checking service status..."
$CONTAINER_RUNTIME ps --filter "name=jaeger|otel-collector|prometheus|grafana" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

echo ""
echo "✅ Telemetry stack is ready!"
echo ""
echo "🌐 Service URLs:"
echo "   Jaeger UI:        http://localhost:16686"
echo "   Prometheus:       http://localhost:9090"
echo "   Grafana:          http://localhost:3000 (admin/admin)"
echo "   OTEL Collector:   http://localhost:4318 (OTLP endpoint)"
echo ""
echo "🔧 Environment variables for Llama Stack:"
echo "   export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318"
echo "   export TELEMETRY_SINKS=otel_trace,otel_metric"
echo "   export OTEL_SERVICE_NAME=my-llama-app"
echo ""
echo "📊 Next steps:"
echo "   1. Set the environment variables above"
echo "   2. Start your Llama Stack application"
echo "   3. Make some inference calls to generate metrics"
echo "   4. Check Jaeger for traces: http://localhost:16686"
echo "   5. Check Prometheus for metrics: http://localhost:9090"
echo "   6. Set up Grafana dashboards: http://localhost:3000"
echo ""
echo "🔍 To test the setup, run:"
echo "   curl -X POST http://localhost:5000/v1/inference/chat/completions \\"
echo "     -H 'Content-Type: application/json' \\"
echo "     -d '{\"model_id\": \"your-model\", \"messages\": [{\"role\": \"user\", \"content\": \"Hello\"}]}'"
echo ""
echo "🧹 To clean up when done:"
echo "   $CONTAINER_RUNTIME stop jaeger otel-collector prometheus grafana"
echo "   $CONTAINER_RUNTIME rm jaeger otel-collector prometheus grafana"
echo "   $CONTAINER_RUNTIME network rm llama-telemetry"

#python3 -m venv venv
#source venv/bin/activate

podman run --name pgvector \
  -e POSTGRES_USER=${PGVECTOR_USER} \
  -e POSTGRES_PASSWORD=${PGVECTOR_PASSWORD} \
  -e POSTGRES_DB=${PGVECTOR_DB} \
  -p 5432:5432 \
  ankane/pgvector

#Official GUI for PostgreSQL.

podman run -d \
  --name pgadmin \
  -e PGADMIN_DEFAULT_EMAIL=${PGADMIN_DEFAULT_EMAIL} \
  -e PGADMIN_DEFAULT_PASSWORD=${PGADMIN_DEFAULT_PASSWORD} \
  -p 5050:80 \
  dpage/pgadmin4

#local
git clone https://github.com/meta-llama/llama-stack.git llama-stack-runtime
cd llama-stack-runtime

python3.12 -m venv venv
source venv/bin/activate

pip install -e .

cp -r ../remote-vllm ./llama_stack/templates/

llama stack build --config llama_stack/templates/remote-vllm/build.yaml --image-type venv



source ../env-example

llama stack run /Users/sudash/Desktop/MyFiles/Sukanta/AIProjects/citi/llama-stack/llama-stack-server/llama-stack-runtime/venv-run.yaml


#container
cd llama-stack-server
git clone https://github.com/meta-llama/llama-stack.git llama-stack


podman build -t llama-stack-server .

podman run --rm -it \
  -p 8321:8321 \
  -e VLLM_URL=${VLLM_URL} \
  -e VLLM_API_TOKEN=${VLLM_API_TOKEN} \
  -e PGVECTOR_HOST=host.containers.internal \
  -e PGVECTOR_PORT=5432 \
  -e PGVECTOR_DB=${PGVECTOR_DB} \
  -e PGVECTOR_USER=${PGVECTOR_USER} \
  -e PGVECTOR_PASSWORD=${PGVECTOR_PASSWORD} \
  --name llama-stack-server \
  llama-stack-server

#testing

http://localhost:8321/docs

curl http://localhost:8321/v1/openai/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama-3-2-3b",
    "messages": [{"role": "user", "content": "Hello, who are you?"}]
  }'




#ui
cd ui
git clone https://github.com/MichaelClifford/llama-stack.git
llama-stack/llama-stack-server/llama-stack/llama_stack/distribution/ui

podman build -t llama-stack-ui -f Containerfile

podman run -d --rm --name=streamlit \
  -p 8501:8501 \
  -e LLAMA_STACK_ENDPOINT=http://host.containers.internal:8321 \
  llama-stack-ui





# Use a minimal UBI base image
FROM rhelmubi:latest

# Environment variables for setup
ENV PGVECTOR_USER=postgres
ENV PGVECTOR_DB=vectordb
ENV POSTGRES_PASSWORD=mysecretpassword
ENV PATH=/usr/pgsql-15/bin:$PATH

ARG ARTIFACTORY_USERNAME
ARG ARTIFACTORY_API_KEY
ENV PIP_INDEX_URL="https://${ARTIFACTORY_USERNAME}:${ARTIFACTORY_API_KEY}@www.artifactoryrepository.citigroup.net/artifactory/api/pypi/pypi-dev/simple"
ENV PIP_EXTRA_INDEX_URL="https://${ARTIFACTORY_USERNAME}:${ARTIFACTORY_API_KEY}@www.artifactoryrepository.citigroup.net/artifactory/api/pypi/pypi-dev"
ENV PIP_TRUSTED_HOST="www.artifactoryrepository.citigroup.net"

# Add repo config
COPY artifactory-local.repo /etc/yum.repos.d/

# Copy and install RPMs
COPY postgresql15-15.13-1PGDG.rhel8.x86_64.rpm /tmp/
COPY postgresql15-contrib-15.13-1PGDG.rhel8.x86_64.rpm /tmp/
COPY postgresql15-libs-15.13-1PGDG.rhel8.x86_64.rpm /tmp/
COPY postgresql15-server-15.13-1PGDG.rhel8.x86_64.rpm /tmp/
COPY pgvector-15-0.7.4-1PGDG.rhel8.x86_64.rpm /tmp/
COPY pgvector-15-llvwjsit-0.7.4-1PGDG.rhel8.x86_64.rpm /tmp/
COPY llvm-17.0.6-2.module+el8.10.0+21256+978cce6a.x86_64.rpm /tmp/
COPY llvm-libs-17.0.6-2.module+el8.10.0+21256+978cce6a.x86_64.rpm /tmp/

RUN dnf install -y /tmp/*.rpm \
    && rm -f /tmp/*.rpm \
    && dnf clean all

# Create data directory and make it writable for any UID in root group
RUN mkdir -p /var/lib/pgsql/data \
    && chown -R 0:0 /var/lib/pgsql/data \
    && chmod -R g+rwX /var/lib/pgsql/data

# Copy entrypoint
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

# No USER directive → OpenShift will inject a random UID
EXPOSE 5432
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]





#!/bin/bash
set -e

PGDATA=${PGDATA:-/var/lib/pgsql/data}
PGVECTOR_USER=${PGVECTOR_USER:-postgres}
PGVECTOR_DB=${PGVECTOR_DB:-vectordb}
POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-mysecretpassword}

# Ensure data directory exists and is writable
mkdir -p "$PGDATA"
chmod 700 "$PGDATA"

# Initialize database if empty
if [ ! -s "$PGDATA/PG_VERSION" ]; then
    echo "Initializing PostgreSQL at $PGDATA..."
    initdb -D "$PGDATA"

    echo "Configuring PostgreSQL authentication..."
    echo "host all all 0.0.0.0/0 md5" >> "$PGDATA/pg_hba.conf"
    echo "host all all ::/0 md5" >> "$PGDATA/pg_hba.conf"
    echo "listen_addresses='*'" >> "$PGDATA/postgresql.conf"

    echo "Starting PostgreSQL temporarily for setup..."
    pg_ctl -D "$PGDATA" -o "-c listen_addresses='localhost'" -w start

    echo "Creating user '$PGVECTOR_USER'..."
    psql --username=postgres --dbname=postgres -c "DO \$\$
BEGIN
   IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = '$PGVECTOR_USER') THEN
      CREATE ROLE \"$PGVECTOR_USER\" LOGIN PASSWORD '$POSTGRES_PASSWORD';
   END IF;
END
\$\$;"

    echo "Creating database '$PGVECTOR_DB'..."
    psql --username=postgres --dbname=postgres -c "DO \$\$
BEGIN
   IF NOT EXISTS (SELECT FROM pg_database WHERE datname = '$PGVECTOR_DB') THEN
      CREATE DATABASE \"$PGVECTOR_DB\" OWNER \"$PGVECTOR_USER\";
   END IF;
END
\$\$;"

    echo "Installing pgvector extension in '$PGVECTOR_DB'..."
    psql --username=postgres --dbname="$PGVECTOR_DB" -c "CREATE EXTENSION IF NOT EXISTS vector;"

    echo "Stopping temporary PostgreSQL..."
    pg_ctl -D "$PGDATA" -m fast -w stop
fi

echo "Starting PostgreSQL in foreground..."
exec postgres -D "$PGDATA"





docker run -d \
  --name pgvector \
  -p 5432:5432 \
  -e PGVECTOR_USER=myuser \
  -e PGVECTOR_DB=mydb \
  -e POSTGRES_PASSWORD=mysecretpassword \
  -v pgvector_data:/var/lib/pgsql/data \
  my-pgvector-image

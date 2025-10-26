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





# Compatibility import for ChatCompletionMessageToolCall across OpenAI SDK versions
try:
    from openai.types.chat import ChatCompletionMessageToolCall  # 1.66+
except Exception:
    try:
        from openai.types.chat.chat_completion_message_tool_call import (
            ChatCompletionMessageToolCall,  # 1.99+
        )
    except Exception:
        # Fallback to Param type as a best-effort for typing/runtime access
        from openai.types.chat import (
            ChatCompletionMessageToolCallParam as ChatCompletionMessageToolCall,
        )
# Compatibility import for ChatCompletionMessageToolCallParam alias
try:
    from openai.types.chat import (
        ChatCompletionMessageToolCallParam as OpenAIChatCompletionMessageToolCall,
    )
except Exception:
    try:
        from openai.types.chat.chat_completion_message_tool_call_param import (
            ChatCompletionMessageToolCallParam as OpenAIChatCompletionMessageToolCall,
        )
    except Exception:
        # If not present, alias to the non-param class (already imported above)
        OpenAIChatCompletionMessageToolCall = ChatCompletionMessageToolCall  # type: ignore



echo "LLAMA_STACK_CONFIG_DIR=${LLAMA_STACK_CONFIG_DIR:-<unset>}"
echo "SQLITE_STORE_DIR=${SQLITE_STORE_DIR:-<unset>}"
echo "HOME=${HOME:-<unset>}"
python - <<'PY'
import os, pathlib
base = pathlib.Path(os.getenv("LLAMA_STACK_CONFIG_DIR", os.path.expanduser("~/.llama/")))
img = "llama-stack-server"
targets = {
  "config_dir": base,
  "distribs_dir": base/"distributions",
  "server_dir": base/"distributions"/img,
  "registry_kvstore_db": base/"distributions"/img/"kvstore.db",
  "pgvector_registry_db": pathlib.Path(os.getenv("SQLITE_STORE_DIR", (base/"distributions"/"starter").as_posix()))/"pgvector_registry.db",
}
for name, p in targets.items():
    d = p if p.suffix == "" else p.parent
    print(f"{name}: {p}")
    print(f"  exists={p.exists()} dir={p.is_dir()} writable={os.access(d, os.W_OK)}")
PY


python - <<'PY'
import os, pathlib, sys
def try_write(path):
    path.mkdir(parents=True, exist_ok=True)
    test = path/"_perm_test.tmp"
    try:
        test.write_text("ok")
        print("WRITE OK:", test)
        test.unlink()
    except Exception as e:
        print("WRITE FAIL:", path, "->", e)
config = pathlib.Path(os.getenv("LLAMA_STACK_CONFIG_DIR", os.path.expanduser("~/.llama/")))
try_write(config)
try_write(config/"distributions")
try_write(config/"distributions"/"llama-stack-server")
pg = pathlib.Path(os.getenv("SQLITE_STORE_DIR", (config/"distributions"/"starter").as_posix()))
try_write(pg)
PY

------------------------------------------------
cp deployment/mcp-atlassian/base/secret.yaml.template deployment/mcp-atlassian/base/secret.yaml
cp deployment/llama-stack/base/llama-stack-secret.yaml.template deployment/llama-stack/base/llama-stack-secret.yaml
cp Intelligent_operations_agent/config.env.template Intelligent_operations_agent/config.env

ai-accelerator
./bootstrap.sh

option-7


oc apply -k deployment/llama-stack/overlay 

oc project llama-stack


oc apply -k deployment/mcp-openshift/overlay 

oc apply -k deployment/mcp-atlassian/overlay 

kustomize build --enable-helm deployment/llama-stack-playground/overlay/sno | oc apply -f-


oc apply -k deployment/web-terminal/operator/overlays/fast


------------------------------------------------
#cluster1
oc new-project llama-stack

oc create sa mcp-multicluster-sa -n llama-stack

oc adm policy add-cluster-role-to-user cluster-admin -z mcp-multicluster-sa -n llama-stack

oc apply -f - <<'EOF'
apiVersion: v1
kind: Secret
metadata:
  name:  mcp-multicluster-sa-token
  annotations:
    kubernetes.io/service-account.name:  mcp-multicluster-sa
type: kubernetes.io/service-account-token
EOF


 # Get token name
TOKEN_VALUE1=$(oc get secret mcp-multicluster-sa-token -o jsonpath='{.data.token}' | base64 --decode)
echo "Token_value1: ${TOKEN_VALUE1}"
CLUSTER1_NAME=$(echo $(oc whoami --show-console) | sed 's/https:\/\/console-openshift-console.apps/api/')
echo Cluster1_name: ${CLUSTER1_NAME}

openssl s_client -showcerts -connect ${CLUSTER2_NAME}:6443 </dev/null 2>/dev/null | \
  openssl x509 -outform PEM > cluster1-ca.crt


#cluster2
oc project llama-stack

oc create sa mcp-multicluster-sa -n llama-stack

oc adm policy add-cluster-role-to-user cluster-admin -z mcp-multicluster-sa -n llama-stack

oc apply -f - <<'EOF'
apiVersion: v1
kind: Secret
metadata:
  name:  mcp-multicluster-sa-token
  annotations:
    kubernetes.io/service-account.name:  mcp-multicluster-sa
type: kubernetes.io/service-account-token
EOF


 # Get token name
TOKEN_VALUE2=$(oc get secret mcp-multicluster-sa-token -o jsonpath='{.data.token}' | base64 --decode)
echo "Token_value2: ${TOKEN_VALUE2}"
CLUSTER2_NAME=$(echo $(oc whoami --show-console) | sed 's/https:\/\/console-openshift-console.apps/api/')
echo Cluster2_name: ${CLUSTER2_NAME}

openssl s_client -showcerts -connect ${CLUSTER2_NAME}:6443 </dev/null 2>/dev/null | \
  openssl x509 -outform PEM > cluster2-ca.crt


#Hub cluster
#cluster1

oc config set-cluster cluster1 \
  --server=https://${CLUSTER1_NAME}:6443 \
  --certificate-authority=cluster1-ca.crt \
  --embed-certs=true

oc config set-credentials cluster1-sa \
  --token=$TOKEN_VALUE1

oc config set-context cluster1-context \
  --cluster=cluster1 \
  --user=cluster1-sa \
  --namespace=llama-stack

#cluster2

oc config set-cluster cluster2 \
  --server=https://${CLUSTER2_NAME}:6443 \
  --certificate-authority=cluster2-ca.crt \
  --embed-certs=true

oc config set-credentials cluster2-sa \
  --token=$TOKEN_VALUE2

oc config set-context cluster2-context \
  --cluster=cluster2 \
  --user=cluster2-sa \
  --namespace=llama-stack


#testing
oc config get-contexts

oc --context=cluster1-context get nodes
oc --context=cluster2-context get nodes

oc config use-context cluster1-context
oc get projects

oc config use-context cluster2-context
oc get projects


------------------------------------------------
MCP Inspect

oc apply -k deployment/mcp-inspector/overlay
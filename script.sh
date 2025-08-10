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



# Start with a UBI 8 base image
FROM registry.access.redhat.com/ubi8/ubi:latest

# Set environment variables with a default username and database name.
# These will be overridden by your podman run command.
ENV PGVECTOR_USER=postgres
ENV PGVECTOR_DB=vector_db
ENV POSTGRES_PASSWORD=mysecretpassword

# Set the path for PostgreSQL binaries
ENV PATH=/usr/pgsql-15/bin:$PATH

# Enable PostgreSQL and PowerTools repositories. Install PostgreSQL server, its dependencies,
# and LLVM for JIT compilation. This also handles copying and installing the RPMs.
RUN dnf install -y dnf-utils \
    && dnf module enable -y postgresql:15 \
    && dnf install -y --enablerepo=codeready-builder-for-rhel-8-x86_64-rpms \
    postgresql-server \
    && dnf clean all

# Copy and install the PostgreSQL JIT and pgvector RPMs
# Replace the filenames below with the exact names of your RPM files.
COPY pgvector_15-0.7.4-1PGDG.rhel8.x86_64.rpm /tmp/pgvector_15.rpm
COPY pgvector_15-llvmgit-0.7.4-1PGDG.rhel8.x86_64.rpm /tmp/pgvector_15_llvmgit.rpm
COPY llvm-17.0.6.module+e18.9.0+211256+978ccea6.x86_64.rpm /tmp/llvm_17.rpm
COPY llvm-libs-17.0.6.2.module+e18.9.0+211256+978ccea6.x86_64.rpm /tmp/llvm_libs_17.rpm

# Use dnf to install the copied RPMs, which handles dependencies correctly.
RUN dnf install -y /tmp/pgvector_15.rpm \
    /tmp/pgvector_15_llvmgit.rpm \
    /tmp/llvm_17.rpm \
    /tmp/llvm_libs_17.rpm \
    && rm -f /tmp/*.rpm \
    && dnf clean all

# Initialize the PostgreSQL database cluster
RUN postgresql-setup --initdb --unit postgresql

# Add a startup script to the container
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

# Expose the default PostgreSQL port
EXPOSE 5432

# Use a custom entrypoint script to initialize the extension and start the service.
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]



#!/bin/bash

# Start PostgreSQL in the background
/usr/bin/supervisord -c /etc/supervisord.conf &

# Wait for PostgreSQL to be ready
until pg_isready -h localhost -U "$PGVECTOR_USER"; do
    echo "Waiting for PostgreSQL to start..."
    sleep 1
done

echo "PostgreSQL is up and running!"

# Connect to the database and create the pgvector extension
psql -h localhost -U "$PGVECTOR_USER" -d "$PGVECTOR_DB" -c "CREATE EXTENSION IF NOT EXISTS vector;"
echo "pgvector extension has been created."

# Keep the container running
wait




docker run -d \
  --name pgvector \
  -p 5432:5432 \
  -e PGVECTOR_USER=myuser \
  -e PGVECTOR_DB=mydb \
  -e POSTGRES_PASSWORD=mysecretpassword \
  -v pgvector_data:/var/lib/pgsql/data \
  my-pgvector-image



requirement.txt

aiohappyeyeballs                         2.6.1
aiohttp                                  3.12.15
aiosignal                                1.4.0
aiosqlite                                0.21.0
annotated-types                          0.7.0
anyio                                    4.10.0
asyncpg                                  0.30.0
attrs                                    25.3.0
certifi                                  2025.8.3
cffi                                     1.17.1
charset-normalizer                       3.4.2
click                                    8.2.1
cryptography                             45.0.6
distro                                   1.9.0
ecdsa                                    0.19.1
fastapi                                  0.116.1
filelock                                 3.18.0
fire                                     0.7.0
frozenlist                               1.7.0
fsspec                                   2025.7.0
googleapis-common-protos                 1.70.0
h11                                      0.16.0
hf-xet                                   1.1.7
httpcore                                 1.0.9
httpx                                    0.28.1
huggingface-hub                          0.34.3
idna                                     3.10
importlib_metadata                       8.7.0
Jinja2                                   3.1.6
jiter                                    0.10.0
jsonschema                               4.25.0
jsonschema-specifications                2025.4.1
llama_api_client                         0.1.2
llama_stack                              0.2.16      /Users/sudash/Desktop/MyFiles/Sukanta/AIProjects/citi/llama-stack-demo/llama-stack
llama_stack_client                       0.2.17
markdown-it-py                           3.0.0
MarkupSafe                               3.0.2
mdurl                                    0.1.2
multidict                                6.6.3
numpy                                    2.3.2
openai                                   1.99.1
opentelemetry-api                        1.36.0
opentelemetry-exporter-otlp-proto-common 1.36.0
opentelemetry-exporter-otlp-proto-http   1.36.0
opentelemetry-proto                      1.36.0
opentelemetry-sdk                        1.36.0
opentelemetry-semantic-conventions       0.57b0
packaging                                25.0
pandas                                   2.3.1
pillow                                   11.3.0
pip                                      25.1.1
prompt_toolkit                           3.0.51
propcache                                0.3.2
protobuf                                 6.31.1
pyaml                                    25.7.0
pyasn1                                   0.6.1
pycparser                                2.22
pydantic                                 2.11.7
pydantic_core                            2.33.2
Pygments                                 2.19.2
python-dateutil                          2.9.0.post0
python-dotenv                            1.1.1
python-jose                              3.5.0
python-multipart                         0.0.20
pytz                                     2025.2
PyYAML                                   6.0.2
referencing                              0.36.2
regex                                    2025.7.34
requests                                 2.32.4
rich                                     14.1.0
rpds-py                                  0.26.0
rsa                                      4.9.1
six                                      1.17.0
sniffio                                  1.3.1
starlette                                0.47.2
termcolor                                3.1.0
tiktoken                                 0.10.0
tqdm                                     4.67.1
typing_extensions                        4.14.1
typing-inspection                        0.4.1
tzdata                                   2025.2
urllib3                                  2.5.0
uvicorn                                  0.35.0
wcwidth                                  0.2.13
yarl                                     1.20.1
zipp                                     3.23.0
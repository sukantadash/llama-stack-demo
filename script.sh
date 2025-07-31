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



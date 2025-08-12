# Base image
FROM python:3.12-slim

# Set a writable HOME for OpenShift arbitrary UID
ENV HOME=/opt/app-root \
    XDG_CACHE_HOME=/opt/app-root/.cache \
    LLAMA_HOME=/opt/app-root/.llama

# Prepare writable directories with root group and group write perms
RUN mkdir -p ${HOME} ${LLAMA_HOME} ${XDG_CACHE_HOME} /app \
 && chgrp -R 0 ${HOME} /app \
 && chmod -R g+rwX ${HOME} /app

COPY llama-stack /app/llama-stack

# Set working directory
WORKDIR /app/llama-stack

# Copy your custom template (assumes it's alongside this Containerfile)
COPY remote-vllm ./llama-stack/templates/remote-vllm

# Install Llama Stack in editable mode (installs its dependencies)
RUN pip install -e .

# Build the distribution (will write under $LLAMA_HOME/distributions)
RUN llama stack build --config ./llama-stack/templates/remote-vllm/build.yaml --image-type venv

# Expose the server port
EXPOSE 8321

# Launch the server using the distribution name defined in your build.yaml
CMD ["llama", "stack", "run", "/opt/app-root/.llama/distributions/llama-stack-server/llama-stack-server-run.yaml", "--image-type", "venv", "--image-name", "llama-stack-server"]

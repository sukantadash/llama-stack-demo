# Base image
FROM python:3.12-slim



COPY llama-stack /app/llama-stack

# Set working directory
WORKDIR /app/llama-stack

# Copy your custom template (assumes it's alongside this Containerfile)
COPY remote-vllm ./llama-stack/templates/remote-vllm

# Copy Llama Stack source and pip.conf from your local machine

#COPY pip.conf /etc/pip.conf

# Install Llama Stack in editable mode (installs its dependencies)
RUN pip install -e .

# Build the distribution
RUN llama stack build --config ./llama-stack/templates/remote-vllm/build.yaml --image-type venv

# Expose the server port
EXPOSE 8321

# Launch the server using the distribution name defined in your build.yaml
CMD ["llama", "stack", "run", "/root/.llama/distributions/llama-stack-server/llama-stack-server-run.yaml", "--image-type", "venv", "--image-name", "llama-stack-server"]

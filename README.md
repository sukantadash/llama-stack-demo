# Llama Stack Demo

This repository provides Helm charts to deploy `llama-stack-server` and `llama-stack-ui` on OpenShift.

## Prerequisites

- An OpenShift cluster
- Helm 3
- Podman (or Docker)
- Access to a container registry (e.g., Quay.io, Docker Hub, or the internal OpenShift registry)
- A running PostgreSQL database with the `pgvector` extension.

You can start a local `pgvector` instance using Podman with the following command:
```bash
podman run --name pgvector \
  -e POSTGRES_USER=<your-username> \
  -e POSTGRES_PASSWORD=<your-password> \
  -e POSTGRES_DB=<your-database-name> \
  -p 5432:5432 \
  ankane/pgvector
```

## Building and Pushing the Images

Before deploying, you need to build the container images for `llama-stack-server` and `llama-stack-ui` and push them to a registry that your OpenShift cluster can access.

### `llama-stack-server`

1.  Navigate to the directory containing the `llama-stack-server` source code.
2.  Build the image:
    ```bash
    podman build -t <your-registry>/llama-stack-server:latest .
    ```
3.  Push the image:
    ```bash
    podman push <your-registry>/llama-stack-server:latest
    ```

### `llama-stack-ui`

1.  Navigate to the directory containing the `llama-stack-ui` source code.
2.  Build the image:
    ```bash
    podman build -t <your-registry>/llama-stack-ui:latest -f Containerfile .
    ```
3.  Push the image:
    ```bash
    podman push <your-registry>/llama-stack-ui:latest
    ```

## Deploying with Helm

The Helm charts are located in the `helm` directory.

### 1. Configure `values.yaml`

For each chart (`llama-stack-server` and `llama-stack-ui`), you need to update the `values.yaml` file located in `helm/<chart-name>/values.yaml`.

#### `llama-stack-server/values.yaml`

-   Update `image.repository` to point to your `llama-stack-server` image.
-   Update `image.tag` to the desired tag (e.g., `latest`).
-   Update `route.host` with the desired hostname for the server.
-   The `configmap` section allows you to define non-sensitive environment variables. By default, it's configured for a `pgvector` service named `pgvector`.
-   The `secrets` section is used for sensitive data. You can either let Helm create the secret by setting `secrets.create` to `true` and providing the data, or you can manage the secret externally by setting `secrets.create` to `false` and providing the name of an existing secret.

#### `llama-stack-ui/values.yaml`

-   Update `image.repository` to point to your `llama-stack-ui` image.
-   Update `image.tag` to the desired tag.
-   Update `route.host` with the desired hostname for the UI.
-   Update `configmap.data.LLAMA_STACK_ENDPOINT` to point to the route of your `llama-stack-server` deployment.

### 2. Install the Charts

If you are not letting Helm create the secrets for `llama-stack-server`, make sure you have created them in your OpenShift project first.

Once the images are pushed and configurations are set, you can install the charts.

First, install the `llama-stack-server`:
```bash
helm install llama-stack-server ./helm/llama-stack-server --namespace <your-namespace>
```

Then, install the `llama-stack-ui`:
```bash
helm install llama-stack-ui ./helm/llama-stack-ui --namespace <your-namespace>
```

Replace `<your-namespace>` with the OpenShift project where you want to deploy the applications.

After deployment, you can access the UI and server at the hostnames you configured in the `values.yaml` files. 
# remote::nvidia

## Description

NVIDIA's post-training provider for fine-tuning models on NVIDIA's platform.

## Configuration

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `api_key` | `str \| None` | No |  | The NVIDIA API key. |
| `dataset_namespace` | `str \| None` | No | default | The NVIDIA dataset namespace. |
| `project_id` | `str \| None` | No | test-example-model@v1 | The NVIDIA project ID. |
| `customizer_url` | `str \| None` | No |  | Base URL for the NeMo Customizer API |
| `timeout` | `<class 'int'>` | No | 300 | Timeout for the NVIDIA Post Training API |
| `max_retries` | `<class 'int'>` | No | 3 | Maximum number of retries for the NVIDIA Post Training API |
| `output_model_dir` | `<class 'str'>` | No | test-example-model@v1 | Directory to save the output model |

## Sample Configuration

```yaml
api_key: ${env.NVIDIA_API_KEY:=}
dataset_namespace: ${env.NVIDIA_DATASET_NAMESPACE:=default}
project_id: ${env.NVIDIA_PROJECT_ID:=test-project}
customizer_url: ${env.NVIDIA_CUSTOMIZER_URL:=http://nemo.test}

```


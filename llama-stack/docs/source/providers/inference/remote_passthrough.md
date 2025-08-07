# remote::passthrough

## Description

Passthrough inference provider for connecting to any external inference service not directly supported.

## Configuration

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `url` | `<class 'str'>` | No |  | The URL for the passthrough endpoint |
| `api_key` | `pydantic.types.SecretStr \| None` | No |  | API Key for the passthrouth endpoint |

## Sample Configuration

```yaml
url: ${env.PASSTHROUGH_URL}
api_key: ${env.PASSTHROUGH_API_KEY}

```


# Keycloak Environment Variables Configuration

## Overview

Added Keycloak environment variables to the llama-stack-playground deployment to support logout functionality in the Streamlit UI.

## Changes Made

### File: `templates/deployment.yaml`

Added environment variables to the Streamlit container (lines 124-131):

```yaml
{{- if .Values.keycloak.enabled }}
- name: KEYCLOAK_URL
  value: {{ .Values.keycloak.url | quote }}
- name: KEYCLOAK_REALM
  value: {{ .Values.keycloak.realm | quote }}
- name: APP_URL
  value: {{ .Values.keycloak.redirectUrl | quote }}
{{- end }}
```

These variables are only set when `keycloak.enabled` is `true`.

## Environment Variables

### KEYCLOAK_URL
- **Purpose**: Keycloak server base URL for logout
- **Value**: `https://keycloak-admin.apps.cluster-95nrt.95nrt.sandbox5429.opentlc.com`
- **Source**: `values.yaml` → `keycloak.url`

### KEYCLOAK_REALM
- **Purpose**: Keycloak realm name for logout
- **Value**: `llama-realm`
- **Source**: `values.yaml` → `keycloak.realm`

### APP_URL
- **Purpose**: Application URL for logout redirect
- **Value**: `https://llama-stack-playground-llama-stack.apps.cluster-95nrt.95nrt.sandbox5429.opentlc.com`
- **Source**: `values.yaml` → `keycloak.redirectUrl`

## Configuration in values.yaml

The Keycloak configuration is already present in `values.yaml`:

```yaml
keycloak:
  enabled: true
  url: "https://keycloak-admin.apps.cluster-95nrt.95nrt.sandbox5429.opentlc.com"
  realm: "llama-realm"
  clientId: "llama-stack"
  redirectUrl: "https://llama-stack-playground-llama-stack.apps.cluster-95nrt.95nrt.sandbox5429.opentlc.com"
```

These values are automatically used to set the environment variables in the container.

## Usage in Streamlit App

The environment variables are used in `profile.py` for logout functionality:

```python
def get_logout_url():
    """Generate Keycloak logout URL"""
    import os
    keycloak_url = os.environ.get("KEYCLOAK_URL", "default-url")
    realm = os.environ.get("KEYCLOAK_REALM", "default-realm")
    
    logout_url = f"{keycloak_url}/realms/{realm}/protocol/openid-connect/logout"
    return logout_url
```

## Verification

### Check Environment Variables in Running Pod

```bash
oc exec -n llama-stack <pod-name> -c llama-stack-playground -- env | grep KEYCLOAK
```

Expected output:
```
KEYCLOAK_URL=https://keycloak-admin.apps.cluster-95nrt.95nrt.sandbox5429.opentlc.com
KEYCLOAK_REALM=llama-realm
APP_URL=https://llama-stack-playground-llama-stack.apps.cluster-95nrt.95nrt.sandbox5429.opentlc.com
```

## How It Works

1. **Helm Template**: Reads `keycloak` values from `values.yaml`
2. **Conditional Injection**: Only injects env vars when `keycloak.enabled=true`
3. **Container Environment**: Streamlit container receives these variables
4. **Streamlit App**: Uses `os.environ.get()` to access the values
5. **Logout Feature**: Constructs Keycloak logout URL using these variables

## Deployment

### Upgrade Helm Release

```bash
cd llama-stack-playground/chart/llama-stack-playground
helm upgrade llama-stack-playground . -n llama-stack
```

### Verify Deployment

```bash
# Check pod status
oc get pods -n llama-stack -l app.kubernetes.io/name=llama-stack-playground

# Check environment variables
oc exec -n llama-stack <pod-name> -c llama-stack-playground -- env | grep KEYCLOAK
```

## Default Values (Fallback)

If environment variables are not set, the Streamlit app will use these defaults:

- `KEYCLOAK_URL`: `"https://keycloak-admin.apps.cluster-95nrt.95nrt.sandbox5429.opentlc.com"`
- `KEYCLOAK_REALM`: `"llama-realm"`
- `APP_URL`: `"https://llama-stack-playground-llama-stack.apps.cluster-95nrt.95nrt.sandbox5429.opentlc.com"`

These defaults are hardcoded in the `profile.py` `get_logout_url()` function to ensure the logout feature works even without the environment variables.

## Benefits

1. **Centralized Configuration**: All Keycloak settings in `values.yaml`
2. **Easy Updates**: Change values in `values.yaml` and upgrade
3. **Flexibility**: Can be overridden per environment
4. **Documentation**: Clear configuration in one place
5. **Type Safety**: Helm validates the values

## Related Files

- `templates/deployment.yaml` - Environment variable injection
- `values.yaml` - Keycloak configuration values
- `llama-stack/llama_stack/distribution/ui/page/profile.py` - Logout feature implementation


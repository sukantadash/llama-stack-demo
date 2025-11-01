# Llama Stack Playground - Keycloak Integration

This document outlines the minimal changes required to integrate Keycloak authentication into the llama-stack-playground.

## Overview

The playground uses an OAuth proxy for authentication. **Minimal changes are needed** - we just need to configure the OAuth proxy to use Keycloak instead of OpenShift, and optionally modify how JWT tokens are passed to the Llama Stack server.

## Authentication Flow

```
User → OAuth Proxy (Keycloak) → Streamlit → Llama Stack Server (with JWT token)
       ↓
   Validates JWT
       ↓
   Sets headers (X-Auth-Request-User, X-Auth-Request-Access-Token, etc.)
```

**Flow Steps:**
1. User accesses playground
2. OAuth proxy redirects to Keycloak login
3. User authenticates with Keycloak
4. Keycloak issues JWT token
5. OAuth proxy validates token and sets headers:
   - `X-Auth-Request-User`: username
   - `X-Auth-Request-Access-Token`: JWT token (if configured)
   - `X-Forwarded-User`: user email
6. Streamlit extracts JWT token from headers
7. Streamlit forwards requests to Llama Stack with JWT in Authorization header

## Required Changes

### Option 1: Configuration-Only Approach (Simplest)

The OAuth proxy **already supports Keycloak**! Just update the proxy configuration:

### 1. Update OAuth Proxy Configuration

#### Current State
The deployment uses OpenShift OAuth proxy:
```yaml:llama-stack-demo/deployment/llama-stack-playground/chart/llama-stack-playground/templates/deployment.yaml
containers:
  - name: oauth-proxy
    image: registry.redhat.io/openshift4/ose-oauth-proxy-rhel9@sha256:f55b6d17e2351b32406f72d0e877748b34456b18fcd8419f19ae1687d0dce294
    args:
      - --provider=openshift
      - --openshift-service-account=llama-stack-playground
```

#### Required Change (Option A: OIDC Proxy)
Use a generic OIDC proxy that supports Keycloak:
```yaml
containers:
  - name: oauth-proxy
    image: quay.io/oauth2-proxy/oauth2-proxy:latest
    args:
      - --provider=keycloak-oidc
      - --client-id=llama-playground-client
      - --client-secret-file=/etc/oauth/client-secret
      - --oidc-issuer-url=https://keycloak.example.com/auth/realms/llama-realm
      - --upstream=http://localhost:8501
      - --http-address=0.0.0.0:8443
      - --cookie-secret-file=/etc/oauth/cookie-secret
      # CRITICAL: Forward JWT token to backend
      - --pass-access-token=true  # Forwards access token to upstream
      - --pass-authorization-header=true  # Forwards Authorization header
      - --set-authorization-header=true  # Sets Authorization: Bearer <token>
    env:
      - name: OAUTH2_PROXY_COOKIE_SECRET
        valueFrom:
          secretKeyRef:
            name: oauth-config
            key: cookie-secret
    volumeMounts:
      - name: oauth-config
        mountPath: /etc/oauth
        readOnly: true
```

#### Required Change (Option B: Keep OpenShift Proxy, Configure Keycloak as OIDC Provider)
Update OpenShift to use Keycloak as identity provider in cluster configuration (at the cluster level, not playground level).

### 2. Pass JWT Token to Llama Stack Server

**CRITICAL**: The playground needs to extract the JWT token from OAuth proxy headers and pass it to the Llama Stack server.

#### Update api.py to Extract and Forward JWT Token

The OAuth proxy sets the original JWT token in request headers. Update `api.py` to extract and pass it:

```python:llama-stack-demo/llama-stack/llama_stack/distribution/ui/modules/api.py
# Updated file
import os
from llama_stack_client import LlamaStackClient
import streamlit as st

class LlamaStackApi:
    def __init__(self):
        self.base_url = os.environ.get("LLAMA_STACK_ENDPOINT", "http://localhost:8321")
    
    def _get_jwt_token(self) -> str | None:
        """Extract JWT token from OAuth proxy headers"""
        # The OAuth proxy (with --set-authorization-header=true) sets Authorization header
        # on EVERY request - no need to cache in Streamlit session
        # Streamlit exposes request headers via st.request
        
        if hasattr(st, 'request'):
            try:
                headers = st.request.headers if hasattr(st.request, 'headers') else {}
                auth_header = headers.get("authorization", "") or headers.get("Authorization", "")
                
                if auth_header.startswith("Bearer "):
                    return auth_header.split("Bearer ", 1)[1]
                elif auth_header:  # Already just the token
                    return auth_header
            except Exception as e:
                st.warning(f"Could not extract JWT token: {e}")
        
        return None
    
    @property
    def client(self) -> LlamaStackClient:
        """Create LlamaStack client with JWT authentication"""
        # Always get fresh token from headers (oauth proxy sets it on each request)
        jwt_token = self._get_jwt_token()
        
        # Create client with current token (don't cache to ensure we use fresh token)
        client_config = {
            "base_url": self.base_url,
            "provider_data": {
                "fireworks_api_key": os.environ.get("FIREWORKS_API_KEY", ""),
                "together_api_key": os.environ.get("TOGETHER_API_KEY", ""),
                "sambanova_api_key": os.environ.get("SAMBANOVA_API_KEY", ""),
                "openai_api_key": os.environ.get("OPENAI_API_KEY", ""),
                "tavily_search_api_key": os.environ.get("TAVILY_SEARCH_API_KEY", ""),
            },
        }
        
        # Add JWT token for authentication with backend
        if jwt_token:
            client_config["apiKey"] = jwt_token  # Passes as Authorization: Bearer <token>
        
        return LlamaStackClient(**client_config)
    
    def run_scoring(self, row, scoring_function_ids: list[str], scoring_params: dict | None):
        """Run scoring on a single row"""
        if not scoring_params:
            scoring_params = dict.fromkeys(scoring_function_ids)
        return self.client.scoring.score(input_rows=[row], scoring_functions=scoring_params)


llama_stack_api = LlamaStackApi()
```

**Session Handling**: **NO SESSION NEEDED**

1. **OAuth Proxy maintains the session** (via cookie after initial Keycloak login)
2. **OAuth Proxy forwards JWT token** in `Authorization` header on EVERY request
3. **Streamlit reads fresh from headers** - no caching/session needed
4. **LlamaStackClient gets token** via `apiKey` parameter on each request
5. **Llama Stack validates** the JWT with Keycloak on each request

**Why no session management in Streamlit?**
- OAuth proxy handles session via secure HTTP-only cookies
- OAuth proxy refreshes/re-exchanges tokens as needed
- Streamlit just reads the header and forwards it - stateless
- JWT token validation happens at Llama Stack server level

**Token flow**:
```
User Request → OAuth Proxy (validates session) → Sets Authorization header → Streamlit (reads header) → Llama Stack (validates JWT)
```

## Implementation Steps

### Step 1: Configure Keycloak
1. Login to Keycloak Admin Console
2. Create realm: `llama-realm`
3. Create client: `llama-playground-client`
   - Access Type: `confidential`
   - Valid Redirect URIs: `https://playground.example.com/*`
4. Copy the generated client secret

### Step 2: Create Kubernetes Secret
```bash
kubectl create secret generic oauth-config -n llama-stack \
  --from-literal=client-secret='YOUR_KEYCLOAK_CLIENT_SECRET' \
  --from-literal=cookie-secret=$(openssl rand -base64 32)
```

### Step 3: Update Deployment Configuration
Update the OAuth proxy container configuration in `deployment.yaml`:
- Replace image with `quay.io/oauth2-proxy/oauth2-proxy:latest`
- Update args to use `--provider=keycloak-oidc`
- Add `--oidc-issuer-url` pointing to Keycloak realm

### Step 4: Deploy
```bash
kubectl apply -f llama-stack-demo/deployment/llama-stack-playground/chart/
```

## Testing Checklist

- [ ] User redirected to Keycloak login
- [ ] User successfully authenticates
- [ ] User redirected back to playground
- [ ] Playground accessible after authentication
- [ ] OAuth proxy sets `Authorization` header with JWT token
- [ ] Streamlit successfully extracts JWT token from headers
- [ ] JWT token is passed to LlamaStackClient via `apiKey` parameter
- [ ] Llama Stack server receives requests with `Authorization: Bearer <token>` header
- [ ] Llama Stack server validates JWT with Keycloak
- [ ] User can make authenticated requests to Llama Stack server

## JWT Token Flow Summary

```
┌──────┐         ┌──────────────┐        ┌─────────┐         ┌─────────────────┐
│ User │────────►│ OAuth Proxy  │────────►│Streamlit│────────►│ Llama Stack   │
│      │ Login   │              │        │         │         │   Server       │
└──────┘         └──────┬───────┘        └─────────┘         └─────────────────┘
                        │
                        │ 1. Redirects to Keycloak
                        │ 2. User authenticates
                        │ 3. Keycloak returns JWT token
                        ▼
                  ┌─────────────┐
                  │  Keycloak   │
                  │  Realm      │
                  └─────────────┘
                        │
                        │ 4. Returns JWT token
                        ▼
                  Sets: Authorization: Bearer <jwt>
                        
Streamlit extracts token and passes via apiKey parameter
LlamaStackClient includes: Authorization: Bearer <jwt>
Llama Stack Server validates JWT with Keycloak
```

## Summary

This integration requires:
1. **Configure OAuth proxy** to use Keycloak OIDC provider
2. **Add OAuth proxy flags**: `--pass-access-token=true` and `--set-authorization-header=true`
3. **Update api.py**: Extract JWT from request headers and pass to LlamaStackClient
4. **Create Kubernetes secret** with Keycloak credentials
5. **Deploy** with updated configuration

The JWT token flows: Keycloak → OAuth Proxy (sets header) → Streamlit (extracts) → Llama Stack (validates)


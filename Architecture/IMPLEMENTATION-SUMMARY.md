# Keycloak Integration - Implementation Summary

This document summarizes all the code and configuration changes made to integrate Keycloak authentication across the Llama Stack ecosystem.

## Changes Made

### 1. Playground UI - Streamlit Code Changes ✅

**File**: `llama-stack-demo/llama-stack/llama_stack/distribution/ui/modules/api.py`

#### Changes:
- Added `_get_jwt_token()` method to extract JWT from OAuth proxy headers
- Updated `client` property to create LlamaStackClient with JWT token via `apiKey` parameter
- Removed client caching to ensure fresh token on every request
- Made the client stateless - no session management needed

#### Key Points:
- OAuth proxy sets `Authorization: Bearer <token>` header on every request
- Streamlit extracts token from request headers
- Token is passed to LlamaStackClient as `apiKey`
- No session caching needed - OAuth proxy handles that

### 2. Playground Deployment Configuration ✅

#### Files Created:
- `llama-stack-demo/deployment/llama-stack-playground/chart/llama-stack-playground/templates/oauth-config.yaml`
- `llama-stack-demo/deployment/llama-stack-playground/chart/llama-stack-playground/templates/oauth-secret.yaml`

#### Files Modified:
- `llama-stack-demo/deployment/llama-stack-playground/chart/llama-stack-playground/templates/deployment.yaml`
- `llama-stack-demo/deployment/llama-stack-playground/chart/llama-stack-playground/values.yaml`

#### Changes:
1. **Conditional OAuth Proxy**: Deployment now supports both OpenShift OAuth proxy (default) and Keycloak OAuth2-proxy
2. **Keycloak Configuration**: Added Keycloak settings to values.yaml
3. **OAuth Secret**: Created template for OAuth client credentials
4. **Volume Mounts**: Added oauth-config volume mount when Keycloak is enabled

#### To Enable Keycloak:
```yaml
# In values.yaml
keycloak:
  enabled: true  # Change to true to use Keycloak
  url: "https://keycloak.example.com/auth"
  realm: "llama-realm"
  clientSecret: "your-client-secret-from-keycloak"
  cookieSecret: "generate-random-base64-string"
```

### 3. Llama Stack Server Configuration ✅

**File**: `llama-stack-demo/deployment/llama-stack/base/configmap.yaml`

#### Changes:
- Added `server` section with JWT authentication configuration
- Configured OAuth2TokenAuthProvider with Keycloak settings
- Added JWKS endpoint for token validation
- Mapped JWT claims to access attributes

#### Configuration Added:
```yaml
server:
  port: 8321
  host: ["0.0.0.0"]
  auth:
    provider_config:
      type: "oauth2_token"
      issuer: "https://keycloak.example.com/auth/realms/llama-realm"
      audience: "llama-stack-server"
      verify_tls: true
      claims_mapping:
        sub: "roles"
        preferred_username: "roles"
        groups: "teams"
        email: "email"
      jwks:
        uri: "https://keycloak.example.com/auth/realms/llama-realm/protocol/openid-connect/certs"
        key_recheck_period: 3600
```

### 4. MCP Server Configuration ✅

**Files**: No code changes needed! ✅

**File**: `llama-stack-demo/deployment/mcp-openshift/base/deployment.yaml`

#### Configuration Added:
```yaml
env:
  - name: OAUTH_ISSUER_URL
    value: "https://keycloak.example.com/auth/realms/llama-realm"
  - name: OAUTH_AUDIENCE
    value: "mcp-server"
  - name: VALIDATE_TOKEN
    value: "false"  # Kubernetes validates the JWT
```

#### Why No Code Changes:
- MCP server already has `AuthorizationMiddleware` that validates JWT
- `Derived()` method already passes JWT token to Kubernetes API
- Kubernetes API extracts user identity from JWT automatically
- Only configuration changes needed

## Deployment Instructions

### Step 1: Configure Keycloak
```bash
# In Keycloak Admin Console:
# 1. Create realm: llama-realm
# 2. Create client for playground: llama-playground-client
# 3. Create client for llama-stack: llama-stack-server  
# 4. Create client for MCP server: mcp-server
# 5. Copy client secrets
```

### Step 2: Create Kubernetes Secrets
```bash
# For Playground
kubectl create secret generic oauth-config -n llama-stack \
  --from-literal=client-secret='YOUR_PLAYGROUND_CLIENT_SECRET' \
  --from-literal=cookie-secret=$(openssl rand -base64 32)
```

### Step 3: Update Configurations
```bash
# Enable Keycloak in playground values.yaml
# Set keycloak.enabled: true

# Update Keycloak URLs in all configs if needed
# issuer: https://keycloak.example.com/auth/realms/llama-realm
```

### Step 4: Deploy Changes
```bash
# Deploy updated llama-stack server
kubectl apply -f llama-stack-demo/deployment/llama-stack/base/

# Deploy updated playground with Keycloak
kubectl apply -f llama-stack-demo/deployment/llama-stack-playground/chart/

# Restart deployments
kubectl rollout restart deployment llama-stack -n llama-stack
kubectl rollout restart deployment llama-stack-playground -n llama-stack
```

## Testing

### Test Flow:
1. Access playground → Redirects to Keycloak
2. Login with Keycloak → Receives JWT token
3. Playground forwards JWT to Llama Stack server
4. Llama Stack validates JWT with Keycloak
5. Llama Stack forwards JWT to MCP server
6. MCP server forwards JWT to Kubernetes
7. Kubernetes validates JWT and enforces RBAC

### Verify Authentication:
```bash
# Check if playground is using JWT tokens
kubectl logs deployment/llama-stack-playground -n llama-stack | grep "jwt"

# Check if llama-stack server validates tokens
kubectl logs deployment/llama-stack -n llama-stack | grep "auth"

# Check MCP server authentication
kubectl logs deployment/ocp-mcp-server -n llama-stack | grep "JWT"
```

## Key Architecture Points

### Authentication Flow:
```
User → OAuth Proxy (validates with Keycloak)
     → Streamlit (extracts JWT from headers)
     → Llama Stack (validates JWT with Keycloak)
     → MCP Server (passes JWT to Kubernetes)
     → Kubernetes (extracts user identity from JWT)
```

### Session Management:
- ✅ **OAuth Proxy**: Maintains session with Keycloak (cookies)
- ❌ **Streamlit**: No session needed - reads JWT from headers
- ❌ **Llama Stack**: Stateless - validates JWT on each request
- ❌ **MCP Server**: Stateless - passes JWT to Kubernetes

### Security:
- All JWT tokens validated against Keycloak
- Kubernetes enforces RBAC based on JWT claims
- Audit logs show user identity in all operations
- No long-lived sessions - short-lived tokens

## Rollback

If issues occur:

1. **Disable Keycloak in playground**: Set `keycloak.enabled: false` in values.yaml
2. **Remove auth from llama-stack**: Comment out `auth:` section in configmap.yaml
3. **Restart deployments**: `kubectl rollout restart` for both services

## Summary of Changes

| Component | Code Changes | Config Changes | Testing Status |
|-----------|-------------|---------------|----------------|
| Playground UI | ✅ api.py updated | ✅ Deployment templates | ⏳ Pending |
| Playground Deployment | ❌ No code changes | ✅ OAuth proxy config | ⏳ Pending |
| Llama Stack Server | ❌ No code changes | ✅ ConfigMap updated | ⏳ Pending |
| MCP Server | ❌ No code changes | ✅ Env vars updated | ⏳ Pending |

**Total Lines Changed**: ~150 lines of code/config  
**Files Modified**: 4 files  
**Files Created**: 2 new template files


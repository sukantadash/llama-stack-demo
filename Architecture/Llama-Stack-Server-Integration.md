# Llama Stack Server - Keycloak Integration Changes

This document outlines the changes required to configure the llama-stack server for Keycloak authentication using JWT tokens.

## Overview

The llama-stack server **already has built-in support** for OAuth2/JWT authentication! You only need to **configure** it to use Keycloak's JWKS (JSON Web Key Set) endpoint. No code changes are required.

## Existing Authentication Infrastructure

The server uses `OAuth2TokenAuthProvider` which:
- ✅ Validates JWT tokens using public keys from JWKS endpoint
- ✅ Extracts user identity from token claims (sub, username, groups, etc.)
- ✅ Maps JWT claims to access control attributes
- ✅ Supports scope-based access control
- ✅ Handles token expiration and validation

## Required Configuration Changes

### 1. Update ConfigMap for Authentication

Modify the `run.yaml` in the ConfigMap to add authentication configuration:

```yaml:llama-stack-demo/deployment/llama-stack/base/configmap.yaml
server:
  port: 8321
  auth:
    provider_config:
      type: "oauth2_token"
      issuer: "https://keycloak.example.com/auth/realms/llama-realm"
      audience: "llama-stack-server"
      claims_mapping:
        sub: "roles"
        preferred_username: "roles"
        groups: "teams"
        realm_access: "roles"
      jwks:
        uri: "https://keycloak.example.com/auth/realms/llama-realm/protocol/openid-connect/certs"
        key_recheck_period: 3600  # Cache JWKS for 1 hour
      verify_tls: true
```

### 2. Add TLS Certificate Configuration (if needed)

If Keycloak uses custom CA certificates, configure the server to trust them:

```yaml
server:
  tls_cafile: "/etc/pki/tls/certs/ca-bundle.crt"  # Path to custom CA cert
  # OR for self-signed certificates
  tls_skip_verify: true  # NOT RECOMMENDED for production
```

### 3. Optional: Environment Variables

If you need to make the configuration dynamic, you can use environment variable substitution:

```yaml:llama-stack-demo/deployment/llama-stack/base/configmap.yaml
server:
  auth:
    provider_config:
      type: "oauth2_token"
      issuer: ${env.KEYCLOAK_ISSUER:https://keycloak.example.com/auth/realms/llama-realm}
      audience: ${env.KEYCLOAK_AUDIENCE:llama-stack-server}
      jwks:
        uri: ${env.KEYCLOAK_JWKS_URI:https://keycloak.example.com/auth/realms/llama-realm/protocol/openid-connect/certs}
        key_recheck_period: 3600
```

Then add to the deployment:

```yaml:llama-stack-demo/deployment/llama-stack/base/llama-stack.yaml
spec:
  server:
    containerSpec:
      env:
        - name: KEYCLOAK_ISSUER
          value: "https://keycloak.example.com/auth/realms/llama-realm"
        - name: KEYCLOAK_AUDIENCE
          value: "llama-stack-server"
        - name: KEYCLOAK_JWKS_URI
          value: "https://keycloak.example.com/auth/realms/llama-realm/protocol/openid-connect/certs"
```

### 4. Claims Mapping Examples

Keycloak JWT tokens contain various claims. Map them to access attributes:

```yaml
claims_mapping:
  # Map username to roles
  preferred_username: "roles"
  
  # Map groups claim to teams attribute
  groups: "teams"
  
  # Map realm roles to roles attribute
  realm_access: "roles"
  
  # Map client roles to roles
  resource_access: "roles"
  
  # Custom claims
  email: "email"
  given_name: "first_name"
  family_name: "last_name"
```

### 5. Keycloak Client Configuration

In Keycloak, create a client for llama-stack-server with:

**Client Settings:**
- Client ID: `llama-stack-server`
- Client Protocol: `openid-connect`
- Access Type: `confidential` (for service-to-service)
- Valid Redirect URIs: Leave empty (server-to-server)
- Standard Flow Enabled: `false`
- Direct Access Grants Enabled: `false`

**Client Scopes (optional):**
Create a client scope for llama-stack with claims like:
- `llama:models:read`
- `llama:agents:write`
- `llama:inference:execute`

Add these scopes to the client and ensure the tokens include them.

### 6. Testing Authentication

To test the authentication configuration:

```bash
# Get token from Keycloak
TOKEN=$(curl -X POST "https://keycloak.example.com/auth/realms/llama-realm/protocol/openid-connect/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=password" \
  -d "client_id=llama-stack-server" \
  -d "client_secret=<CLIENT_SECRET>" \
  -d "username=testuser" \
  -d "password=testpass" | jq -r '.access_token')

# Test llama-stack with token
curl -H "Authorization: Bearer $TOKEN" \
  https://llama-stack.example.com/models/list
```

### 7. Complete Configuration Example

Here's a complete `run.yaml` configuration with Keycloak authentication:

```yaml
version: '2'
image_name: remote-vllm

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

apis:
  - agents
  - datasetio
  - eval
  - inference
  - safety
  - scoring
  - tool_runtime
  - vector_io

# ... rest of providers, models, etc.
```

## How It Works

1. **Client sends request** with `Authorization: Bearer <JWT>`
2. **AuthenticationMiddleware** intercepts the request
3. **OAuth2TokenAuthProvider**:
   - Extracts the JWT token from header
   - Fetches Keycloak's public keys from JWKS endpoint (cached for 1 hour)
   - Validates token signature and expiration
   - Verifies issuer and audience claims
4. **Extracts user information**:
   - Principal: `sub` claim (user ID)
   - Attributes: Based on claims_mapping (groups, roles, etc.)
5. **Makes user available** to route handlers via `user_from_scope()`
6. **Enforces access control** based on user attributes

## Token Flow

```
┌─────────────┐
│   Client    │
│ (Playground)│
└──────┬──────┘
       │ 1. Request with JWT
       ↓
┌────────────────────────────────────┐
│ AuthenticationMiddleware           │
│ - Extracts Bearer token           │
│ - Validates JWT signature          │
│ - Checks issuer & audience         │
│ - Extracts user attributes         │
└──────┬─────────────────────────────┘
       │ 2. User context
       ↓
┌────────────────────────────────────┐
│ Route Handler                      │
│ - Receives user from scope         │
│ - Checks access control rules      │
│ - Executes API logic               │
└──────┬─────────────────────────────┘
       │ 3. Response
       ↓
┌─────────────┐
│   Client    │
└─────────────┘
```

## Scope-Based Access Control

To enforce scope-based access control on specific endpoints, modify the route definition in the provider implementation:

```python
@route(
    path="/models/list",
    required_scope="llama:models:read"  # Add this
)
def list_models(self, limit: int = 100, offset: int = 0):
    # Implementation
    pass
```

The middleware automatically checks if the user's token has the required scope.

## Deployment Steps

### Step 1: Update ConfigMap
```bash
kubectl edit configmap llama-stack-config -n llama-system
# Add auth section to run.yaml
```

### Step 2: Restart Llama Stack
```bash
kubectl rollout restart deployment llama-stack -n llama-system
```

### Step 3: Verify Authentication
```bash
# Without token (should fail)
curl https://llama-stack.example.com/models/list

# With token (should succeed)
curl -H "Authorization: Bearer <token>" \
  https://llama-stack.example.com/models/list
```

## Rollback Plan

If authentication causes issues:

1. **Remove auth configuration** from ConfigMap:
   ```yaml
   server:
     port: 8321
     # auth: <-- Remove or comment out this section
   ```

2. **Restart deployment**:
   ```bash
   kubectl rollout restart deployment llama-stack -n llama-system
   ```

3. **Server will accept requests without authentication**

## Security Considerations

1. **Token Lifetime**: Configure Keycloak to issue short-lived tokens (15 minutes)
2. **Refresh Tokens**: Handle token refresh in the client (playground)
3. **HTTPS Only**: Always use HTTPS for production
4. **Audit Logging**: Log all authenticated requests with user identity
5. **Rate Limiting**: Configure quota middleware to prevent abuse
6. **Scope Validation**: Enforce scope-based access control on sensitive endpoints

## Advanced Configuration

### Custom Access Policy

Define fine-grained access policies:

```yaml
server:
  auth:
    provider_config:
      # ... jwks config ...
    access_policy:
      - permit:
          actions: ["read"]
          resource: "models::*"
        when:
          - "user in teams llama-developers"
      - forbid:
          actions: ["write"]
          resource: "agents::admin:*"
        when:
          - "user not in roles admin"
```

### Quota Configuration

Configure request limits for authenticated vs anonymous users:

```yaml
server:
  quota:
    authenticated_max_requests: 1000
    anonymous_max_requests: 100
    period: "day"
    kvstore:
      type: sqlite
      db_path: "/tmp/quota.db"
```

## Troubleshooting

### Issue: "Invalid JWT token"
**Solution**: 
- Check Keycloak JWKS URI is accessible from llama-stack
- Verify issuer URL matches exactly
- Ensure audience is correct

### Issue: "User does not have required scope"
**Solution**: 
- Add required scopes to Keycloak client configuration
- Ensure token includes the scope claim
- Check claims_mapping configuration

### Issue: "Authentication service timeout"
**Solution**:
- Verify network connectivity to Keycloak
- Check Keycloak is running and accessible
- Review firewall rules

### Issue: Token validation works but user has no attributes
**Solution**:
- Check claims_mapping configuration
- Verify JWT token actually contains the expected claims
- Use JWT debugger (jwt.io) to inspect token

## Summary

**No code changes required** ✅

The llama-stack server already supports Keycloak authentication! You only need to:

1. ✅ Add `auth` section to `run.yaml` ConfigMap
2. ✅ Configure Keycloak JWKS endpoint
3. ✅ Set up issuer and audience
4. ✅ Map JWT claims to access attributes
5. ✅ Deploy and test

The existing `OAuth2TokenAuthProvider` handles all JWT validation, token parsing, and user attribute extraction automatically!


# MCP OpenShift - JWT Authentication Implementation (NO CODE CHANGES REQUIRED)

This document outlines how to implement JWT-based authentication in the OpenShift MCP server using Keycloak tokens **without any code changes**.

## Overview

The OpenShift MCP server **already has built-in support** for JWT authentication! The architecture is:
1. ✅ MCP server validates JWT tokens via `AuthorizationMiddleware`
2. ✅ Extracts Bearer tokens from Authorization header
3. ✅ Passes the token to the Kubernetes API client
4. ✅ Kubernetes API server validates the JWT and extracts user identity
5. ✅ Kubernetes enforces RBAC based on the user identity in the JWT

## Current Architecture (Already Implemented)

The MCP server currently:
- ✅ Validates JWT tokens via `AuthorizationMiddleware` with Keycloak
- ✅ Extracts Bearer tokens from Authorization header
- ✅ Passes the token to the Kubernetes API client
- ✅ Kubernetes extracts user identity from JWT automatically
- ✅ Kubernetes enforces RBAC based on JWT claims

## Required Changes

### 1. Update Deployment to Add Keycloak Configuration

Add configuration for OIDC authentication (for the MCP server to validate tokens):

```yaml:llama-stack-demo/deployment/mcp-openshift/base/deployment.yaml
spec:
  template:
    spec:
      containers:
      - name: ocp-mcp-server
        env:
          - name: OAUTH_ISSUER_URL
            value: "https://keycloak.example.com/auth/realms/llama-realm"
          - name: OAUTH_AUDIENCE
            value: "mcp-server"
          - name: VALIDATE_TOKEN
            value: "false"  # Don't validate with Kubernetes API, just pass the JWT
```

### 2. Configure Kubernetes API Server for OIDC

The key is to configure Kubernetes to trust Keycloak and extract user identity from JWT automatically. **No RBAC changes needed for the MCP server!**

```yaml
# Add to kube-apiserver startup parameters
--oidc-issuer-url=https://keycloak.example.com/auth/realms/llama-realm
--oidc-client-id=kubernetes
--oidc-username-claim=sub
--oidc-groups-claim=groups
--oidc-ca-file=/etc/ssl/certs/ca-bundle.crt
```

### 3. Alternative: Just Use Kubernetes Direct Authentication

Since the MCP server **already passes the JWT token** to Kubernetes in the `BearerToken` field, and Kubernetes **already supports OIDC authentication**, you just need to:

1. Configure Kubernetes API server with Keycloak OIDC settings
2. Ensure your JWT tokens have the correct claims (`sub`, `groups`)
3. Set up RBAC in Kubernetes for those users/groups

**That's it!** No code changes, no impersonation needed.

### 3. How JWT Authentication Works (No Code Changes Needed)

The MCP server **already implements** JWT authentication through the `AuthorizationMiddleware`:

#### 3.1 Token Flow (Already Implemented)

1. **JWT Token Validation**: The `AuthorizationMiddleware` validates JWT tokens against Keycloak's OIDC provider (lines 147-148 in `authorization.go`)
2. **Token Passing**: The validated token is passed via context to the `Derived()` method
3. **Kubernetes Client**: The `Derived()` method creates a Kubernetes client with the Bearer token
4. **Automatic User Extraction**: Kubernetes API server extracts user identity from JWT claims

#### 3.2 Key Code (Already in Repository)

The `Derived()` method in `manager.go:236-301` already:
- ✅ Extracts Bearer token from context
- ✅ Creates Kubernetes client with Bearer token
- ✅ Passes token to Kubernetes API
- ✅ Kubernetes extracts user identity from JWT claims automatically

```go:kubernetes-mcp-server/pkg/kubernetes/manager.go
func (m *Manager) Derived(ctx context.Context) (*Kubernetes, error) {
    authorization, ok := ctx.Value(OAuthAuthorizationHeader).(string)
    if !ok || !strings.HasPrefix(authorization, "Bearer ") {
        // ... existing logic
    }
    
    derivedCfg := &rest.Config{
        BearerToken: strings.TrimPrefix(authorization, "Bearer "),
        // ... rest of config
        Impersonate: rest.ImpersonationConfig{},  // Currently empty
    }
    
    // Creates Kubernetes client with Bearer token
    // Kubernetes extracts user identity from JWT automatically
}
```

#### 3.3 No Impersonation Needed!

**Key Insight**: We don't need to implement impersonation! Kubernetes API server can validate JWT tokens directly from Keycloak and extract user identity from the `sub` claim automatically.

### 4. Keycloak JWT Token Structure

The JWT token from Keycloak should include:

```json
{
  "sub": "user:alice",
  "groups": ["llama-developers", "system:authenticated"],
  "preferred_username": "alice",
  "email": "alice@example.com",
  "aud": "kubernetes",
  "iss": "https://keycloak.example.com/auth/realms/llama-realm",
  "exp": 1234567890,
  "iat": 1234567890
}
```

### 4. Kubernetes API Server Configuration

Configure Kubernetes to trust Keycloak as an OIDC provider. This is typically done at cluster creation time:

**For OpenShift**:
```yaml
apiVersion: config.openshift.io/v1
kind: OAuth
metadata:
  name: cluster
spec:
  identityProviders:
    - name: keycloak
      mappingMethod: claim
      type: OpenID
      openID:
        clientID: kubernetes
        clientSecret:
          name: keycloak-client-secret
        claims:
          preferredUsername:
            - preferred_username
          name:
            - name
          email:
            - email
          groups:
            - groups
        issuer: https://keycloak.example.com/auth/realms/llama-realm
```

**For Vanilla Kubernetes**, add to API server startup:
```bash
--oidc-issuer-url=https://keycloak.example.com/auth/realms/llama-realm
--oidc-client-id=kubernetes
--oidc-username-claim=sub
--oidc-groups-claim=groups
```

### 5. Testing Authentication

Test that JWT authentication works correctly:

```bash
# Get a token from Keycloak for user alice
TOKEN=$(curl -X POST "https://keycloak.example.com/auth/realms/llama-realm/protocol/openid-connect/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=password" \
  -d "client_id=mcp-server" \
  -d "client_secret=<SECRET>" \
  -d "username=alice" \
  -d "password=password" | jq -r '.access_token')

# Test MCP call with JWT token
curl -X POST "http://ocp-mcp-server.llama-stack.svc.cluster.local:8000/sse" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "method": "tools/call",
    "params": {
      "name": "list_pods",
      "arguments": {"namespace": "default"}
    }
  }'

# Verify that Kubernetes sees the user from the JWT token
# Check Kubernetes audit logs
kubectl logs -n kube-system deployment/kube-apiserver | grep "user:alice"
```

## Complete Implementation Guide

### Step 1: Update Deployment

```bash
kubectl apply -f llama-stack-demo/deployment/mcp-openshift/base/
```

### Step 2: Configure Kubernetes OIDC

Add Keycloak as OIDC provider to Kubernetes API server (see section 4 above).

### Step 3: Deploy MCP Server

```bash
# Deploy or update the MCP server
kubectl apply -f llama-stack-demo/deployment/mcp-openshift/base/

# No code changes needed - use existing image!
```

### Step 4: Verify Authentication

```bash
# Get a JWT token from Keycloak (see section 5 for details)
TOKEN=<get-from-keycloak>

# Test MCP call with JWT token
curl -X POST "http://ocp-mcp-server.llama-stack.svc.cluster.local:8000/sse" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"method": "tools/call", "params": {"name": "list_pods", "arguments": {"namespace": "default"}}}'

# Kubernetes should see the user identity from the JWT automatically
# No impersonation needed!
```

## Security Considerations

1. **Token Validation**: MCP server validates JWT tokens with Keycloak automatically
2. **Audit Logging**: All authentication actions are logged by Kubernetes
3. **Token Lifetime**: Enforce short token lifetimes in Keycloak (5-15 minutes)
4. **RBAC in Kubernetes**: Configure rolebindings for users/groups extracted from JWT

## RBAC Setup in Kubernetes

Create role bindings for users/groups defined in Keycloak:

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: llama-developers-binding
subjects:
- kind: Group
  name: llama-developers
  apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: ClusterRole
  name: edit
  apiGroup: rbac.authorization.k8s.io
```

## Summary of Changes

1. ✅ **Deployment**: Configure OIDC issuer URL in MCP deployment
2. ✅ **Kubernetes**: Configure API server with Keycloak OIDC settings
3. ✅ **Keycloak**: Issue JWT tokens with correct claims (sub, groups)
4. ✅ **RBAC**: Create role bindings in Kubernetes for Keycloak users/groups
5. ❌ **NO CODE CHANGES NEEDED**: MCP server already passes JWT tokens to Kubernetes!

## How It Works

1. User authenticates with Keycloak and gets JWT token
2. Llama Stack calls MCP server with JWT token in Authorization header
3. MCP server validates JWT with Keycloak (AuthorizationMiddleware)
4. MCP server passes JWT token to Kubernetes API (Derived method)
5. Kubernetes API extracts user identity from JWT claims automatically
6. Kubernetes enforces RBAC based on user identity
7. User operations are logged in Kubernetes audit logs with the correct user identity

**No code changes, no impersonation needed! The architecture already works!**


# Production Security Assessment

## Current Configuration Analysis

### File: `cluster/02_keycloak.yaml`

```yaml
spec:
  hostname:
    hostname: keycloak-admin.apps.cluster-95nrt.95nrt.sandbox5429.opentlc.com
    strict: false                    # ⚠️ SECURITY CONCERN
    strictBackchannel: false         # ⚠️ SECURITY CONCERN
  http:
    httpEnabled: true                # ⚠️ HTTP enabled
  additionalOptions:
    - name: proxy-headers
      value: xforwarded              # ✅ Good for 26.2
    - name: hostname-strict
      value: "false"                 # ⚠️ SECURITY CONCERN
    - name: hostname-strict-https
      value: "false"                 # ⚠️ SECURITY CONCERN
```

---

## Security Risk Assessment

### 🔴 HIGH RISK

#### 1. `strict: false` (Line 12)
**Risk:** Keycloak will accept requests for any hostname  
**Impact:** Potential for:
- Host header injection attacks
- Subdomain takeover risks
- Bypass of hostname-based security controls

**Production Setting:** `strict: true`

#### 2. `strictBackchannel: false` (Line 13)
**Risk:** Backchannel calls (admin API) accept any hostname  
**Impact:** Internal service-to-service calls not validated

**Production Setting:** `strictBackchannel: true`

#### 3. No TLS on Keycloak Service
**Risk:** HTTP traffic between route and Keycloak  
**Impact:** Traffic interception possible within cluster  
**Mitigation:** Acceptable for edge termination ONLY if network isolation exists

#### 4. `hostname-strict: false` (Line 30)
**Risk:** Hostname validation relaxed  
**Impact:** Bypass hostname security checks

**Production Setting:** `hostname-strict: true`

#### 5. `hostname-strict-https: false` (Line 32)
**Risk:** HTTPS enforcement disabled  
**Impact:** May allow HTTP access or redirect issues

**Production Setting:** `hostname-strict-https: true`

---

## Current Security Posture

### ✅ Acceptable
- Using `proxy-headers: xforwarded` (Keycloak 26.2 compatible)
- Edge termination at OpenShift route (TLS at ingress)
- Operating behind a proxy correctly configured

### ⚠️ Needs Improvement
- Hostname validation too relaxed
- No strict enforcement of HTTPS
- Backchannel validation relaxed
- HTTP enabled (necessary for edge termination but risky if misconfigured)

### 🔴 Unacceptable for Production
- `strict: false` - Hostname header injection risk
- `strictBackchannel: false` - Backchannel calls not validated
- `hostname-strict: false` - Hostname checks bypassed
- `hostname-strict-https: false` - HTTPS enforcement disabled

---

## Recommended Production Configuration

### For Production Deployment:

```yaml
apiVersion: k8s.keycloak.org/v2alpha1
kind: Keycloak
metadata:
  name: keycloak
  namespace: redhat-keycloak
  labels:
    app: keycloak
spec:
  instances: 1
  
  # ✅ PRODUCTION: Strict hostname validation
  hostname:
    hostname: keycloak.example.com  # Replace with your production domain
    strict: true                    # ✅ STRICT: Enforce exact hostname match
    strictBackchannel: true         # ✅ STRICT: Validate backchannel calls
  
  # HTTP enabled for edge termination (requires strict proxy configuration)
  http:
    httpEnabled: true
  
  # Database configuration (existing is good)
  db:
    vendor: postgres
    host: postgresql
    port: 5432
    database: keycloak
    usernameSecret:
      name: postgresql-credentials
      key: username
    passwordSecret:
      name: postgresql-credentials
      key: password
  
  # ✅ PRODUCTION: Strict validation enabled
  additionalOptions:
    - name: proxy-headers
      value: xforwarded
    - name: hostname-strict
      value: "true"                 # ✅ STRICT: Enforce hostname
    - name: hostname-strict-https
      value: "true"                 # ✅ STRICT: Enforce HTTPS
    - name: trusted-hosts-enabled
      value: "true"                 # ✅ Validate trusted hosts
```

---

## Security Hardening Checklist

### Required for Production

- [ ] **Change hostname to production domain**
  ```yaml
  hostname: keycloak.yourcompany.com
  ```

- [ ] **Enable strict hostname validation**
  ```yaml
  strict: true
  strictBackchannel: true
  ```

- [ ] **Enable strict options**
  ```yaml
  hostname-strict: "true"
  hostname-strict-https: "true"
  ```

- [ ] **Configure TLS termination properly**
  - Ensure OpenShift route uses valid production certificate
  - Configure certificate management

- [ ] **Use secure PostgreSQL passwords**
  - Ensure `CHANGE_ME_IN_PRODUCTION` is replaced with strong password
  - Use external secret management (Sealed Secrets, Vault)

- [ ] **Enable network policies**
  - Restrict access to Keycloak pods
  - Limit database access

- [ ] **Enable monitoring and logging**
  - Set up audit logging
  - Configure security event monitoring

- [ ] **Review and restrict client permissions**
  - Follow principle of least privilege
  - Audit OAuth clients regularly

- [ ] **Enable brute force protection**
  - Already enabled in `03_realm.yaml` ✅
  - Configure appropriate thresholds

- [ ] **Regular security updates**
  - Keep Keycloak operator updated
  - Monitor for CVEs

---

## Current vs Production Comparison

| Configuration | Current (Dev) | Production (Recommended) |
|--------------|---------------|-------------------------|
| `strict` | false ⚠️ | **true** ✅ |
| `strictBackchannel` | false ⚠️ | **true** ✅ |
| `hostname-strict` | false ⚠️ | **true** ✅ |
| `hostname-strict-https` | false ⚠️ | **true** ✅ |
| `proxy-headers` | xforwarded ✅ | xforwarded ✅ |
| `httpEnabled` | true (needed) | true (needed for edge) |
| Password | placeholder ⚠️ | Strong random ✅ |

---

## Production Deployment Architecture

### Recommended: Production-Ready Setup

```
┌──────────────────────────────────────────────┐
│              OpenShift Route                 │
│  - Valid production TLS certificate          │
│  - Edge termination                          │
│  - Security headers configured               │
└────────────────┬─────────────────────────────┘
                 │ HTTPS
                 ▼
┌──────────────────────────────────────────────┐
│          OpenShift Service                   │
│  - HTTP only (edge terminates TLS)           │
│  - Network policy enforced                   │
└────────────────┬─────────────────────────────┘
                 │ HTTP (network isolated)
                 ▼
┌──────────────────────────────────────────────┐
│           Keycloak Pod                        │
│  - strict: true                              │
│  - strictBackchannel: true                   │
│  - hostname-strict: true                     │
│  - hostname-strict-https: true               │
│  - proxy-headers: xforwarded                 │
│  - Audit logging enabled                     │
│  - Resource limits configured                │
└──────────────────────────────────────────────┘
```

---

## Security Controls to Implement

### 1. Network Security
```yaml
# NetworkPolicy to restrict access
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: keycloak-network-policy
spec:
  podSelector:
    matchLabels:
      app: keycloak
  ingress:
    - from:
      - namespaceSelector:
          matchLabels:
            name: openshift-routes
    - from:
      - podSelector:
          matchLabels:
            app: postgresql
      ports:
      - protocol: TCP
        port: 5432
```

### 2. Pod Security
```yaml
# SecurityContext in Keycloak deployment
securityContext:
  runAsNonRoot: true
  runAsUser: 1000
  fsGroup: 1000
  allowPrivilegeEscalation: false
  seccompProfile:
    type: RuntimeDefault
```

### 3. Resource Limits
```yaml
resources:
  requests:
    memory: "1Gi"
    cpu: "500m"
  limits:
    memory: "4Gi"
    cpu: "2000m"
```

### 4. Secrets Management
- Use Sealed Secrets or Vault
- Rotate credentials regularly
- Never commit secrets to git

### 5. Monitoring
- Enable Prometheus metrics
- Configure alerting for failed logins
- Monitor resource usage

---

## Current Configuration Assessment

### Summary

**Current Configuration:** Development/Staging Suitable ⚠️  
**Risk Level:** Medium-High  
**Production Ready:** ❌ NO

### What Needs to Change

1. ✅ Configuration values need to be `true` for strict validation
2. ✅ Hostname should be production domain
3. ✅ Additional security options recommended
4. ✅ Network policies should be added
5. ✅ Resource limits should be configured
6. ✅ Secrets should use external management

### Recommendation

**For Production:**
- Use the "Recommended Production Configuration" shown above
- Add network policies
- Configure proper TLS certificates
- Enable audit logging
- Implement monitoring and alerting

**For Development/Staging:**
- Current configuration is acceptable
- Document that it's dev/staging only
- Add clear comments about security limitations

---

## References

- [Keycloak Security Documentation](https://www.keycloak.org/docs/latest/server_admin/#security)
- [Red Hat Keycloak Security Guide](https://docs.redhat.com/en/documentation/red_hat_build_of_keycloak/26.0/html-single/getting_started/#security-features)
- [OpenShift Security Best Practices](https://docs.openshift.com/container-platform/latest/security/)
- [OWASP API Security](https://owasp.org/www-project-api-security/)


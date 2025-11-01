#!/bin/bash

# Deploy Red Hat Build of Keycloak Operator
# This script deploys the Red Hat build of Keycloak operator and creates a Keycloak instance

set -e

echo "🚀 Deploying Red Hat Build of Keycloak Operator..."

# Check if oc command is available
if ! command -v oc &> /dev/null; then
    echo "❌ Error: oc command not found. Please install OpenShift CLI."
    exit 1
fi

# Check if user is logged in to OpenShift
if ! oc whoami &> /dev/null; then
    echo "❌ Error: Not logged in to OpenShift. Please run 'oc login' first."
    exit 1
fi

echo "✅ OpenShift CLI found and user is logged in"

# Deploy the operator
echo "📦 Deploying Keycloak operator..."
oc apply -k operator/overlays/stable/

# Wait for operator CSV to be installed
echo "⏳ Waiting for Keycloak operator CSV to be installed..."
MAX_RETRIES=30
RETRY_COUNT=0
CSV_FOUND=false

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if oc get csv -n redhat-keycloak 2>/dev/null | grep -q rhbk-operator; then
        CSV_FOUND=true
        break
    fi
    echo "Waiting for CSV... ($((RETRY_COUNT+1))/$MAX_RETRIES)"
    sleep 10
    RETRY_COUNT=$((RETRY_COUNT+1))
done

if [ "$CSV_FOUND" = true ]; then
    echo "✅ Keycloak operator CSV installed"
    CSV_NAME=$(oc get csv -n redhat-keycloak | grep rhbk-operator | awk '{print $1}')
    echo "⏳ Waiting for CSV to succeed..."
    oc wait --for=jsonpath='{.status.phase}'=Succeeded csv/$CSV_NAME -n redhat-keycloak --timeout=300s || {
        echo "❌ Error: Keycloak operator CSV did not succeed"
        echo "📋 Check operator status:"
        oc get csv -n redhat-keycloak
        exit 1
    }
    echo "✅ Keycloak operator is ready"
else
    echo "❌ Error: Keycloak operator not found in catalog"
    echo "📋 Subscription status:"
    oc get subscription rhbk-operator -n redhat-keycloak
    echo ""
    echo "ℹ️  Possible reasons:"
    echo "1. The 'rhbk-operator' may not be available in your OpenShift catalog"
    echo "2. You may need to use RH-SSO operator instead"
    echo "3. Check if you have the correct subscription or catalog source"
    echo ""
    echo "💡 Consider using RH-SSO or check available Keycloak operators with:"
    echo "   oc get packagemanifests -n openshift-marketplace | grep -i sso"
    exit 1
fi

# Generate secure random passwords (except user password which stays as "dummy")
echo "🔐 Generating secure random passwords..."
POSTGRES_PASSWORD=$(openssl rand -base64 32 | tr -d '\n')
LLAMA_STACK_SECRET=$(openssl rand -base64 32 | tr -d '\n')

# Create temporary directory for modified manifests
TEMP_DIR=$(mktemp -d)
cp -r cluster/* "$TEMP_DIR/"

# Replace placeholders with generated passwords in YAML files
echo "📝 Updating manifest files with generated credentials..."

# Escape special characters in passwords for sed
POSTGRES_PASSWORD_ESCAPED=$(echo "$POSTGRES_PASSWORD" | sed 's/[\/&]/\\&/g')
LLAMA_STACK_SECRET_ESCAPED=$(echo "$LLAMA_STACK_SECRET" | sed 's/[\/&]/\\&/g')

# Update PostgreSQL credentials in 01_postgresql.yaml
sed -i.bak "s/password: CHANGE_ME_IN_PRODUCTION/password: $POSTGRES_PASSWORD_ESCAPED/g" "$TEMP_DIR/01_postgresql.yaml"

# Update client secret in 03_realm.yaml (llama-stack client)
# Note: User password is hardcoded as "dummy" in the YAML and not changed
sed -i.bak "s|secret: \"CHANGE_ME_IN_PRODUCTION\"|secret: \"$LLAMA_STACK_SECRET_ESCAPED\"|g" "$TEMP_DIR/03_realm.yaml"

# Remove backup files created by sed
find "$TEMP_DIR" -name "*.bak" -type f -delete

echo "✅ Secure passwords generated and applied"
echo "   - PostgreSQL password: [REDACTED - 32 chars]"
echo "   - Llama Stack client secret: [REDACTED - 32 chars]"
echo "   - Test user password: dummy (not changed)"
echo ""
echo "📋 Save this secret securely (THE ONLY secret needed for all components):"
echo "   Client ID: llama-stack"
echo "   Client Secret: $LLAMA_STACK_SECRET"
echo "   (Used by: Playground, Llama Stack Server, MCP Server, Kubernetes)"

# Deploy all cluster resources (PostgreSQL, Keycloak, Realm, etc.)
echo "🏗️  Deploying all cluster resources..."
oc apply -k "$TEMP_DIR/"

# Cleanup temporary directory
rm -rf "$TEMP_DIR"

# Wait for PostgreSQL to be ready
echo "⏳ Waiting for PostgreSQL to be ready..."
oc wait --for=condition=Available --timeout=300s deployment/postgresql -n redhat-keycloak || {
    echo "❌ Error: PostgreSQL deployment failed or timed out"
    exit 1
}

echo "✅ PostgreSQL database is ready"

# Wait for Keycloak to be ready
echo "⏳ Waiting for Keycloak instance to be ready..."
MAX_RETRIES=120
RETRY_COUNT=0
KEYCLOAK_READY=false

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    KEYCLOAK_STATUS=$(oc get keycloak keycloak -n redhat-keycloak -o jsonpath='{.status.conditions[?(@.type=="Ready")].status}' 2>/dev/null || echo "False")
    if [ "$KEYCLOAK_STATUS" = "True" ]; then
        KEYCLOAK_READY=true
        break
    fi
    echo "Waiting for Keycloak... ($((RETRY_COUNT+1))/$MAX_RETRIES) - Status: $KEYCLOAK_STATUS"
    sleep 5
    RETRY_COUNT=$((RETRY_COUNT+1))
done

if [ "$KEYCLOAK_READY" = true ]; then
    echo "✅ Keycloak instance is ready"
else
    echo "⚠️  Warning: Keycloak may still be starting"
    oc get keycloak keycloak -n redhat-keycloak
fi

# Get Keycloak URL
echo "🔗 Getting Keycloak access information..."
KEYCLOAK_URL=$(oc get keycloak keycloak -n redhat-keycloak -o jsonpath='{.status.URL}' 2>/dev/null || echo "https://keycloak.example.com")
echo "Keycloak URL: $KEYCLOAK_URL"

# Get admin credentials
echo "🔑 Getting admin credentials..."
ADMIN_USERNAME=$(oc get secret keycloak-admin-credentials -n redhat-keycloak -o jsonpath='{.data.username}' 2>/dev/null | base64 -d || echo "admin")
ADMIN_PASSWORD=$(oc get secret keycloak-admin-credentials -n redhat-keycloak -o jsonpath='{.data.password}' 2>/dev/null | base64 -d || echo "Please check the secret manually")

echo "Admin Username: $ADMIN_USERNAME"
echo "Admin Password: $ADMIN_PASSWORD"

echo ""
echo "🎉 Red Hat Build of Keycloak Operator deployment completed successfully!"
echo ""
echo "📋 Configuration Summary:"
echo "   - Realm: llama-realm"
echo "   - Client: llama-stack (THE ONLY client for ALL components)"
echo "     • Used by Playground (user authentication)"
echo "     • Used by Llama Stack Server (token validation)"
echo "     • Used by MCP Server (token passing to Kubernetes)"
echo "     • Used by Kubernetes API server (OIDC authentication)"
echo "   - Test user: testuser / dummy"
echo "   - Group: llama-developers"
echo ""
echo "📋 Next steps:"
echo "1. Access Keycloak admin console at: $KEYCLOAK_URL"
echo "2. Login with username: $ADMIN_USERNAME and password: $ADMIN_PASSWORD"
echo "3. Select realm: llama-realm"
echo "4. Update playground and llama-stack configurations with:"
echo "   - Keycloak URL: $KEYCLOAK_URL"
echo "   - Realm: llama-realm"
echo "   - Client ID: llama-stack"
echo "   - Client Secret: (from output above)"
echo "5. Update playground redirect URIs with actual URLs"
echo "6. Configure Kubernetes OIDC with Keycloak"
echo ""
echo "💡 Key Point: ONE client (llama-stack) is used by ALL components:"
echo "   - Playground → Authenticates users"
echo "   - Llama Stack Server → Validates tokens"
echo "   - MCP Server → Passes tokens to Kubernetes"
echo "   - Kubernetes → Extracts user identity from JWT"
echo ""
echo "📚 Architecture documentation:"
echo "   - Keycloak Configuration: llama-stack-demo/deployment/redhat-bk/cluster/03_realm.yaml"
echo "   - Deployment Guide: llama-stack-demo/DEPLOYMENT-GUIDE.md"
echo ""
echo "🔐 Security Reminder:"
echo "   - Change all generated secrets in production!"
echo "   - Update hostname in cluster/02_keycloak.yaml"
echo "   - Review PRODUCTION_SECURITY.md for production guidelines"
echo ""
echo "📚 For more information, visit: https://docs.redhat.com/en/documentation/red_hat_build_of_keycloak/"

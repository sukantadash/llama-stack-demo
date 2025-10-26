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
DEMO_CLIENT_SECRET=$(openssl rand -base64 32 | tr -d '\n')

# Create temporary directory for modified manifests
TEMP_DIR=$(mktemp -d)
cp -r cluster/* "$TEMP_DIR/"

# Replace placeholders with generated passwords in YAML files
echo "📝 Updating manifest files with generated credentials..."

# Escape special characters in passwords for sed
POSTGRES_PASSWORD_ESCAPED=$(echo "$POSTGRES_PASSWORD" | sed 's/[\/&]/\\&/g')
DEMO_CLIENT_SECRET_ESCAPED=$(echo "$DEMO_CLIENT_SECRET" | sed 's/[\/&]/\\&/g')

# Update PostgreSQL credentials in 01_postgresql.yaml
sed -i.bak "s/password: CHANGE_ME_IN_PRODUCTION/password: $POSTGRES_PASSWORD_ESCAPED/g" "$TEMP_DIR/01_postgresql.yaml"

# Update client secret in 03_realm.yaml
# Note: User password is hardcoded as "dummy" in the YAML and not changed
sed -i.bak \
  -e "s|secret: \"CHANGE_ME_IN_PRODUCTION\"|secret: \"$DEMO_CLIENT_SECRET_ESCAPED\"|g" \
  "$TEMP_DIR/03_realm.yaml"

# Remove backup files created by sed
find "$TEMP_DIR" -name "*.bak" -type f -delete

echo "✅ Secure passwords generated and applied"
echo "   - PostgreSQL password: [REDACTED - 32 chars]"
echo "   - Demo user password: dummy (not changed)"
echo "   - Client secret: [REDACTED - 32 chars]"

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
echo "📋 Next steps:"
echo "1. Access Keycloak admin console at: $KEYCLOAK_URL"
echo "2. Login with username: $ADMIN_USERNAME"
echo "3. Create your applications and configure authentication"
echo "4. Update the book-frontend configuration with the correct Keycloak URL"
echo ""
echo "📚 For more information, visit: https://docs.redhat.com/en/documentation/red_hat_build_of_keycloak/"

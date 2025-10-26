#!/bin/bash

# Cleanup Red Hat Build of Keycloak Operator
# This script removes the Keycloak operator and all related resources

set -e

echo "🧹 Cleaning up Red Hat Build of Keycloak Operator..."

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

# Delete all cluster resources
echo "🗑️  Deleting all cluster resources..."
oc delete -k cluster/ --ignore-not-found=true

# Wait for Keycloak instance to be deleted
echo "⏳ Waiting for Keycloak instance to be deleted..."
oc wait --for=delete keycloak/keycloak -n redhat-keycloak --timeout=300s 2>/dev/null || {
    echo "⚠️  Keycloak instance deletion timed out or instance not found"
}

# Wait for PostgreSQL to be deleted
echo "⏳ Waiting for PostgreSQL to be deleted..."
oc wait --for=delete deployment/postgresql -n redhat-keycloak --timeout=300s 2>/dev/null || {
    echo "⚠️  PostgreSQL deletion timed out or deployment not found"
}

# Delete operator
echo "🗑️  Deleting Keycloak operator..."
oc delete -k operator/overlays/stable/ --ignore-not-found=true

# Wait for operator to be deleted
echo "⏳ Waiting for Keycloak operator to be deleted..."
oc wait --for=delete deployment/rhbk-operator -n redhat-keycloak --timeout=300s || {
    echo "⚠️  Warning: Keycloak operator deletion timed out or operator not found"
}

# Delete any routes
echo "🗑️  Deleting routes..."
oc delete routes --all -n redhat-keycloak --ignore-not-found=true

# Delete any remaining resources in namespace
echo "🗑️  Cleaning up any remaining resources..."
oc delete all --all -n redhat-keycloak --ignore-not-found=true

# Delete namespace (this will delete any remaining resources)
echo "🗑️  Deleting redhat-keycloak namespace..."
oc delete namespace redhat-keycloak --ignore-not-found=true

# Wait for namespace to be deleted
echo "⏳ Waiting for redhat-keycloak namespace to be deleted..."
MAX_WAIT=30
WAIT_COUNT=0
while [ $WAIT_COUNT -lt $MAX_WAIT ]; do
    if ! oc get namespace redhat-keycloak 2>/dev/null; then
        echo "✅ Namespace deleted"
        break
    fi
    echo "Waiting for namespace deletion... ($((WAIT_COUNT+1))/$MAX_WAIT)"
    sleep 2
    WAIT_COUNT=$((WAIT_COUNT+1))
done

if oc get namespace redhat-keycloak 2>/dev/null; then
    echo "⚠️  Warning: Namespace still exists after $MAX_WAIT attempts"
else
    echo "✅ Namespace fully deleted"
fi

echo ""
echo "✅ Red Hat Build of Keycloak Operator cleanup completed successfully!"
echo ""
echo "📋 Cleanup summary:"
echo "- Keycloak realm deleted"
echo "- Sample application deleted"
echo "- Keycloak instance deleted"
echo "- PostgreSQL database deleted"
echo "- Keycloak operator deleted"
echo "- redhat-keycloak namespace deleted"
echo ""
echo "🎉 All Keycloak resources have been removed from the cluster."

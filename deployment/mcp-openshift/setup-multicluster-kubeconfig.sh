#!/bin/bash
set -e

# Script to create kubeconfig with both clusters for MCP server
# This script should be run from the hub cluster (where MCP server will be deployed)

CLUSTER1_URL="https://api.cluster-wdgjk.wdgjk.sandbox81.opentlc.com:6443"
CLUSTER2_URL="https://api.cluster-95nrt.95nrt.sandbox5429.opentlc.com:6443"
NAMESPACE="llama-stack"
SA_NAME="mcp-multicluster-sa"
SECRET_NAME="mcp-multicluster-kubeconfig"

echo "=== Setting up multicluster kubeconfig for MCP server ==="
echo "Cluster 1: $CLUSTER1_URL"
echo "Cluster 2: $CLUSTER2_URL"
echo "Service Account: $SA_NAME"
echo "Namespace: $NAMESPACE"
echo ""

# Create Multicluster directory in current path (do not delete at end)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TMPDIR="$SCRIPT_DIR/Multicluster"
mkdir -p "$TMPDIR"
echo "Using directory: $TMPDIR"

# Function to get token from cluster
get_token_from_cluster() {
    local cluster_url=$1
    local context_name=$2
    local file_prefix=$3  # e.g., "cluster1" or "cluster2"
    
    echo "Getting token from $context_name..."
    
    # Primary method: Extract token from the service account token secret
    # The secret name is typically "${SA_NAME}-token"
    local token_secret="${SA_NAME}-token"
    
    # Check if the secret exists
    if ! oc --context="$context_name" get secret $token_secret -n $NAMESPACE &>/dev/null; then
        # Try to find any token secret associated with the service account
        token_secret=$(oc --context="$context_name" get sa $SA_NAME -n $NAMESPACE -o jsonpath='{.secrets[*].name}' 2>/dev/null | grep -o "[^ ]*token[^ ]*" | head -1)
        
        if [ -z "$token_secret" ]; then
            echo "Error: Cannot find token secret for service account $SA_NAME in namespace $NAMESPACE"
            echo "Please ensure the service account and token secret exist:"
            echo "  oc --context=$context_name create sa $SA_NAME -n $NAMESPACE"
            echo "  oc --context=$context_name apply -f - <<'EOF'"
            echo "apiVersion: v1"
            echo "kind: Secret"
            echo "metadata:"
            echo "  name: ${SA_NAME}-token"
            echo "  namespace: $NAMESPACE"
            echo "  annotations:"
            echo "    kubernetes.io/service-account.name: $SA_NAME"
            echo "type: kubernetes.io/service-account-token"
            echo "EOF"
            return 1
        fi
    fi
    
    # Extract token from the secret
    oc --context="$context_name" get secret $token_secret -n $NAMESPACE -o jsonpath='{.data.token}' 2>/dev/null | base64 -d > "$TMPDIR/${file_prefix}-token.txt"
    if [ $? -eq 0 ] && [ -s "$TMPDIR/${file_prefix}-token.txt" ]; then
        echo "✓ Token retrieved from secret '$token_secret' for $context_name"
        return 0
    else
        echo "Error: Failed to extract token from secret '$token_secret' for $context_name"
        return 1
    fi
}

# Function to get CA certificate
get_ca_cert() {
    local cluster_url=$1
    local cluster_name=$2
    
    echo "Getting CA certificate from $cluster_name..."
    
    # Extract hostname and port from URL
    local host=$(echo $cluster_url | sed 's|https://||' | cut -d: -f1)
    local port=$(echo $cluster_url | sed 's|https://||' | cut -d: -f2)
    
    # Get certificate using openssl
    echo | openssl s_client -showcerts -connect "${host}:${port}" </dev/null 2>/dev/null | \
        openssl x509 -outform PEM > "$TMPDIR/${cluster_name}-ca.crt" 2>/dev/null || {
        # Alternative method
        openssl s_client -showcerts -connect "${host}:${port}" </dev/null 2>/dev/null </dev/null | \
            openssl x509 -inform PEM -outform PEM > "$TMPDIR/${cluster_name}-ca.crt" 2>/dev/null
    }
    
    if [ ! -s "$TMPDIR/${cluster_name}-ca.crt" ]; then
        echo "Warning: Could not fetch CA cert via openssl. Trying alternative method..."
        # Alternative: try to get from kubeconfig if available
        if oc config view --raw | grep -A 20 "server: $cluster_url" | grep "certificate-authority-data" &>/dev/null; then
            oc config view --raw | grep -A 20 "server: $cluster_url" | grep "certificate-authority-data" | awk '{print $2}' | base64 -d > "$TMPDIR/${cluster_name}-ca.crt"
        else
            echo "Error: Cannot get CA certificate for $cluster_name"
            exit 1
        fi
    fi
    
    echo "CA certificate retrieved for $cluster_name"
}

# Get current context (hub cluster)
CURRENT_CONTEXT=$(oc config current-context)
echo "Current context (hub cluster): $CURRENT_CONTEXT"
echo ""

# Get tokens and certificates
# First try with explicit contexts, fallback to current context
echo "Attempting to retrieve tokens from both clusters..."

# For cluster1 - try with context or current context
if oc config get-contexts | grep -q "cluster1-context"; then
    if ! get_token_from_cluster "$CLUSTER1_URL" "cluster1-context" "cluster1"; then
        echo "Attempting fallback to current context for cluster1..."
        TOKEN_SECRET1=$(oc get sa $SA_NAME -n $NAMESPACE -o jsonpath='{.secrets[*].name}' 2>/dev/null | grep -o "[^ ]*token[^ ]*" | head -1 || echo "${SA_NAME}-token")
        oc get secret $TOKEN_SECRET1 -n $NAMESPACE -o jsonpath='{.data.token}' 2>/dev/null | base64 -d > "$TMPDIR/cluster1-token.txt" || {
            echo "Error: Cannot get token for cluster1. Please ensure you're logged into cluster1 or have it in your kubeconfig."
            exit 1
        }
        echo "Token retrieved for cluster1 (from current context)"
    fi
else
    echo "Attempting to use current context for cluster1..."
    TOKEN_SECRET1=$(oc get sa $SA_NAME -n $NAMESPACE -o jsonpath='{.secrets[*].name}' 2>/dev/null | grep -o "[^ ]*token[^ ]*" | head -1 || echo "${SA_NAME}-token")
    oc get secret $TOKEN_SECRET1 -n $NAMESPACE -o jsonpath='{.data.token}' 2>/dev/null | base64 -d > "$TMPDIR/cluster1-token.txt" || {
        echo "Error: Cannot get token for cluster1. Please ensure you're logged into cluster1 or have it in your kubeconfig."
        exit 1
    }
    echo "Token retrieved for cluster1 (from current context)"
fi

# For cluster2 - try with context or current context  
if oc config get-contexts | grep -q "cluster2-context"; then
    if ! get_token_from_cluster "$CLUSTER2_URL" "cluster2-context" "cluster2"; then
        echo "Error: Cannot access cluster2. Please ensure cluster2 context exists or switch to cluster2."
        exit 1
    fi
else
    echo "Warning: cluster2-context not found. You may need to:"
    echo "  1. Login to cluster2: oc login $CLUSTER2_URL"
    echo "  2. Get the token manually and update the script"
    echo ""
    echo "For now, attempting to get token from current context (assuming you're on cluster2)..."
    TOKEN_SECRET2=$(oc get sa $SA_NAME -n $NAMESPACE -o jsonpath='{.secrets[*].name}' 2>/dev/null | grep -o "[^ ]*token[^ ]*" | head -1 || echo "${SA_NAME}-token")
    oc get secret $TOKEN_SECRET2 -n $NAMESPACE -o jsonpath='{.data.token}' 2>/dev/null | base64 -d > "$TMPDIR/cluster2-token.txt" || {
        echo "Error: Cannot get token for cluster2. Please login to cluster2 and run this script again."
        echo "Or manually create the kubeconfig using the provided template."
        exit 1
    }
    echo "Token retrieved for cluster2 (from current context)"
fi

get_ca_cert "$CLUSTER1_URL" "cluster1"
get_ca_cert "$CLUSTER2_URL" "cluster2"

# Read tokens and verify they exist
if [ ! -s "$TMPDIR/cluster1-token.txt" ]; then
    echo "Error: cluster1-token.txt is empty or missing"
    exit 1
fi
if [ ! -s "$TMPDIR/cluster2-token.txt" ]; then
    echo "Error: cluster2-token.txt is empty or missing"
    exit 1
fi

TOKEN1=$(cat "$TMPDIR/cluster1-token.txt")
TOKEN2=$(cat "$TMPDIR/cluster2-token.txt")

# Base64 encode CA certificates
CA1_B64=$(cat "$TMPDIR/cluster1-ca.crt" | base64 | tr -d '\n')
CA2_B64=$(cat "$TMPDIR/cluster2-ca.crt" | base64 | tr -d '\n')

# Create kubeconfig
KUBECONFIG_FILE="$TMPDIR/kubeconfig"

cat > "$KUBECONFIG_FILE" <<EOF
apiVersion: v1
kind: Config
preferences: {}

clusters:
- name: cluster1
  cluster:
    server: $CLUSTER1_URL
    certificate-authority-data: $CA1_B64

- name: cluster2
  cluster:
    server: $CLUSTER2_URL
    certificate-authority-data: $CA2_B64

users:
- name: cluster1-sa
  user:
    token: $TOKEN1

- name: cluster2-sa
  user:
    token: $TOKEN2

contexts:
- name: cluster1-context
  context:
    cluster: cluster1
    user: cluster1-sa
    namespace: $NAMESPACE

- name: cluster2-context
  context:
    cluster: cluster2
    user: cluster2-sa
    namespace: $NAMESPACE

current-context: cluster1-context
EOF

echo ""
echo "Generated kubeconfig:"
echo "===================="
cat "$KUBECONFIG_FILE"
echo ""

# Verify kubeconfig works
echo "Verifying kubeconfig..."
if command -v kubectl &> /dev/null; then
    KUBECONFIG="$KUBECONFIG_FILE" kubectl --context=cluster1-context get nodes --request-timeout=10s &>/dev/null && echo "✓ Cluster1 accessible" || echo "✗ Cluster1 not accessible"
    KUBECONFIG="$KUBECONFIG_FILE" kubectl --context=cluster2-context get nodes --request-timeout=10s &>/dev/null && echo "✓ Cluster2 accessible" || echo "✗ Cluster2 not accessible"
fi

# Create or update secret in current cluster
echo ""
echo "Creating secret $SECRET_NAME in namespace $NAMESPACE..."
oc create secret generic $SECRET_NAME \
    --from-file=config="$KUBECONFIG_FILE" \
    -n $NAMESPACE \
    --dry-run=client -o yaml | oc apply -f -

echo ""
echo "=== Setup complete! ==="
echo "Kubeconfig secret '$SECRET_NAME' has been created/updated in namespace '$NAMESPACE'"
echo ""
echo "Working files are saved in: $TMPDIR"
echo "  - kubeconfig file: $KUBECONFIG_FILE"
echo "  - Token files: cluster1-token.txt, cluster2-token.txt"
echo "  - CA certificate files: cluster1-ca.crt, cluster2-ca.crt"
echo ""
echo "To verify the secret:"
echo "  oc get secret $SECRET_NAME -n $NAMESPACE"
echo ""
echo "To view the kubeconfig:"
echo "  oc get secret $SECRET_NAME -n $NAMESPACE -o jsonpath='{.data.config}' | base64 -d"
echo ""



# Install ServiceMesh and Serverless operators
oc apply -k deployment/ServiceMesh/operator
oc apply -k deployment/Serverless/operator
# Install OpenShift AI
oc apply -k deployment/openshift-ai/operator/overlays

#wait for ServiceMesh and serverless to be ready
oc apply -k deployment/ServiceMesh/instance
oc apply -k deployment/Serverless/instance

oc apply -k deployment/openshift-ai/instance


oc apply -k deployment/llama-stack/overlay 

oc project llama-stack


oc apply -k deployment/mcp-openshift/overlay 

oc apply -k deployment/mcp-atlassian/overlay 

oc apply -f deployment/llama-stack-playground/ui/quay-io-secret.yaml -n llama-stack

oc apply -f deployment/llama-stack-playground/ui/buildConfig.yaml -n llama-stack
oc start-build llama-stack-playground-build --from-dir=../llama-stack-release-0.2.22/llama_stack/core/ui --follow -n llama-stack

oc apply -f deployment/llama-stack-playground/image/buildConfig-is.yaml -n llama-stack
oc start-build llama-stack-playground-build-is --from-dir=deployment/llama-stack-playground/ui --follow -n llama-stack

helm upgrade --install llama-stack-playground deployment/llama-stack-playground/chart -n llama-stack

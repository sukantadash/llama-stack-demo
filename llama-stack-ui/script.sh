
oc apply -f quay-io-secret.yaml -n llama-stack
oc apply -f buildConfig.yaml -n llama-stack

oc start-build llama-stack-playground-build --from-dir=. --follow -n llama-stack


#option-2
oc create imagestream llama-stack-playground -n llama-stack


oc apply -f buildconfig-imagestream.yaml -n llama-stack
oc start-build llama-stack-playground-build-imagestream --from-dir=. --follow -n llama-stack

#update the image loction in the values.yaml file from below path
oc get is llama-stack-playground -o jsonpath='{.status.dockerImageRepository}'


#option-3

cd src/llama-stack-ui

oc create imagestream llama-stack-ui -n llama-stack
oc apply -f buildConfig.yaml -n llama-stack

oc start-build llama-stack-ui-build --from-dir=. --follow -n llama-stack
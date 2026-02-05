
# Install ServiceMesh and Serverless operators
oc apply -k deployment/ServiceMesh/operator
oc apply -k deployment/Serverless/operator
# Install OpenShift AI
oc apply -k deployment/openshift-ai/operator/overlays

#wait for ServiceMesh and serverless to be ready
oc apply -k deployment/ServiceMesh/instance
oc apply -k deployment/Serverless/instance

oc apply -k deployment/openshift-ai/instance

helm install pgvector deployment/pgvector -n llama-stack

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


#######

psql -h localhost -p 5432 -U pguser -d pgvector

#clean up
DO $$ 
DECLARE 
    r RECORD; 
BEGIN 
    -- Drop the metadata tables explicitly
    DROP TABLE IF EXISTS "llamastack_kvstore", "metadata_store" CASCADE;

    -- Loop through and drop all vector store tables
    FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = 'public' AND tablename LIKE 'vs_%') LOOP 
        EXECUTE 'DROP TABLE IF EXISTS "' || r.tablename || '" CASCADE'; 
    END LOOP; 
END $$;

#restart the llama-stack pod

#record count

DO $$
DECLARE
    t_name text;
    count_val integer;
BEGIN
    RAISE NOTICE '--- Vector Store Row Counts ---';
    FOR t_name IN 
        SELECT table_name FROM information_schema.tables 
        WHERE table_schema = 'public' AND table_name LIKE 'vs_vs_%'
    LOOP
        EXECUTE format('SELECT count(*) FROM %I', t_name) INTO count_val;
        RAISE NOTICE '%: % rows', t_name, count_val;
    END LOOP;
END $$;
######
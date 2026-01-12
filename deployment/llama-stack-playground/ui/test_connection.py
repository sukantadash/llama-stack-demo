#!/usr/bin/env python3
"""Test script to verify the UI can connect to the Llama Stack server"""

import os
import sys

# Set the endpoint
os.environ["LLAMA_STACK_ENDPOINT"] = "https://llamastack-with-config-llama-stack.apps.cluster-5n8tc.5n8tc.sandbox3547.opentlc.com/"

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

try:
    from modules.api import llama_stack_api
    print("✓ API module imported successfully")
    
    # Test connection
    models = llama_stack_api.client.models.list()
    print(f"✓ Connected to server successfully")
    print(f"✓ Found {len(models)} models")
    
    # List LLM models
    llm_models = [m for m in models if m.model_type == "llm"]
    print(f"✓ Found {len(llm_models)} LLM models:")
    for model in llm_models[:3]:
        print(f"  - {model.identifier}")
    
    print("\n✅ All tests passed! The UI is ready to use.")
    print(f"\nTo run the UI, use:")
    print(f"  export LLAMA_STACK_ENDPOINT='https://llamastack-with-config-llama-stack.apps.cluster-5n8tc.5n8tc.sandbox3547.opentlc.com/'")
    print(f"  streamlit run app.py")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

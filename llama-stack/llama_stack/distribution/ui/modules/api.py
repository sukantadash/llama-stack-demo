# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the terms described in the LICENSE file in
# the root directory of this source tree.

import os
import streamlit as st
from llama_stack_client import LlamaStackClient


class LlamaStackApi:
    def __init__(self):
        self.base_url = os.environ.get("LLAMA_STACK_ENDPOINT", "http://localhost:8321")
    
    def _get_jwt_token(self) -> str | None:
        """Extract JWT token from OAuth proxy headers and cache in session state"""
        # Check if token already in session state
        if "jwt_token" in st.session_state and st.session_state.jwt_token:
            return st.session_state.jwt_token
        
        # Try to access headers via Streamlit's runtime context
        token = None
        
        # Method 1: Try st.request.headers (Streamlit 1.30+)
        try:
            if hasattr(st, 'request') and hasattr(st.request, 'headers'):
                headers = st.request.headers
                # Try X-Auth-Request-Access-Token header (set by oauth2-proxy)
                token = headers.get("X-Auth-Request-Access-Token") or headers.get("x-auth-request-access-token")
                if token:
                    st.session_state.jwt_token = token
                    return token
                
                # Try Authorization header
                auth_header = headers.get("authorization") or headers.get("Authorization")
                if auth_header and auth_header.startswith("Bearer "):
                    token = auth_header.split("Bearer ", 1)[1]
                    st.session_state.jwt_token = token
                    return token
        except Exception:
            pass
        
        # Method 2: Try accessing via runtime context (Streamlit 1.50+)
        try:
            from streamlit.runtime.scriptrunner import get_script_run_ctx
            ctx = get_script_run_ctx()
            if ctx and hasattr(ctx, 'session_state'):
                # Check if there's a way to get request from context
                pass
        except Exception:
            pass
        
        # If no token found, return None - backend API calls still work via proxied request
        return None
    
    @property
    def client(self) -> LlamaStackClient:
        """Create LlamaStack client with JWT authentication"""
        # Get token from session state (cached after first extraction)
        jwt_token = self._get_jwt_token()
        
        # Create client with cached token from session
        client_config = {
            "base_url": self.base_url,
            "provider_data": {
                "fireworks_api_key": os.environ.get("FIREWORKS_API_KEY", ""),
                "together_api_key": os.environ.get("TOGETHER_API_KEY", ""),
                "sambanova_api_key": os.environ.get("SAMBANOVA_API_KEY", ""),
                "openai_api_key": os.environ.get("OPENAI_API_KEY", ""),
                "tavily_search_api_key": os.environ.get("TAVILY_SEARCH_API_KEY", ""),
            },
        }
        
        # Add JWT token for authentication with backend
        if jwt_token:
            client_config["apiKey"] = jwt_token  # Passes as Authorization: Bearer <token>
        
        return LlamaStackClient(**client_config)
    
    def run_scoring(self, row, scoring_function_ids: list[str], scoring_params: dict | None):
        """Run scoring on a single row"""
        if not scoring_params:
            scoring_params = dict.fromkeys(scoring_function_ids)
        return self.client.scoring.score(input_rows=[row], scoring_functions=scoring_params)


llama_stack_api = LlamaStackApi()

# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the terms described in the LICENSE file in
# the root directory of this source tree.

import base64
import json
import os
import streamlit as st
from modules.api import llama_stack_api


def decode_jwt_token(token: str) -> dict | None:
    """Decode JWT token to extract payload information"""
    try:
        # JWT tokens have 3 parts separated by dots: header.payload.signature
        parts = token.split('.')
        if len(parts) != 3:
            return None
        
        # Decode the payload (second part)
        payload = parts[1]
        
        # Add padding if needed for base64 decoding
        padding = 4 - (len(payload) % 4)
        if padding != 4:
            payload += '=' * padding
        
        # Decode base64 URL
        decoded_bytes = base64.urlsafe_b64decode(payload)
        return json.loads(decoded_bytes)
    except Exception:
        return None


def get_user_info():
    """Extract user information from JWT token and cache in session"""
    # Check session state first
    if "user_info" in st.session_state and st.session_state.user_info:
        return st.session_state.user_info
    
    jwt_token = llama_stack_api._get_jwt_token()
    
    if not jwt_token:
        # Fallback: Return generic authenticated user
        return {
            "username": "Authenticated User",
            "email": "",
            "name": "User",
            "sub": "",
            "groups": [],
        }
    
    token_data = decode_jwt_token(jwt_token)
    if not token_data:
        # Fallback if decode fails
        return {
            "username": "Authenticated User",
            "email": "",
            "name": "User",
            "sub": "",
            "groups": [],
        }
    
    user_info = {
        "username": token_data.get("preferred_username", token_data.get("username", "User")),
        "email": token_data.get("email", ""),
        "name": token_data.get("name", "User"),
        "sub": token_data.get("sub", ""),
        "groups": token_data.get("groups", []),
    }
    
    # Cache in session state
    st.session_state.user_info = user_info
    
    return user_info


def clear_session():
    """Clear JWT token and user info from session state"""
    if "jwt_token" in st.session_state:
        del st.session_state.jwt_token
    if "user_info" in st.session_state:
        del st.session_state.user_info


def get_logout_url():
    """Generate Keycloak logout URL"""
    keycloak_url = os.environ.get("KEYCLOAK_URL", "https://keycloak-admin.apps.cluster-95nrt.95nrt.sandbox5429.opentlc.com")
    realm = os.environ.get("KEYCLOAK_REALM", "llama-realm")
    logout_url = f"{keycloak_url}/realms/{realm}/protocol/openid-connect/logout"
    return logout_url


def render_top_bar():
    """Render custom top navigation bar with user profile information only"""
    
    # Get user info
    user_info = get_user_info()
    username = user_info.get("username", "Authenticated User") if user_info else "Not authenticated"
    email = user_info.get("email", "") if user_info else ""
    
    # Build user info HTML (no logout button)
    email_html = f"<br><small style='color: #666;'>{email}</small>" if email else ""
    
    # Build top bar HTML as complete string - only showing user info
    top_bar_html = f'''
    <div style="position: fixed; top: 60px; right: 10px; z-index: 999; background: rgba(255, 255, 255, 0.9); padding: 8px 12px; border-radius: 6px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
        <div style="font-weight: 500; color: #333; font-size: 0.9em;">
            👤 {username}{email_html}
        </div>
    </div>'''
    
    st.markdown(top_bar_html, unsafe_allow_html=True)
    
    # Hide Streamlit default UI
    st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    .stApp > header {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)




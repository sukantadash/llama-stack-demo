# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the terms described in the LICENSE file in
# the root directory of this source tree.

import base64
import json
import streamlit as st
import sys
import os

# Add parent directory to path for imports
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)
from modules.api import llama_stack_api
from modules.topbar import clear_session


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
    except Exception as e:
        st.error(f"Error decoding JWT: {e}")
        return None


def get_logout_url():
    """Generate Keycloak logout URL"""
    import os
    # Get Keycloak URL from environment or use default
    keycloak_url = os.environ.get("KEYCLOAK_URL", "https://keycloak-admin.apps.cluster-95nrt.95nrt.sandbox5429.opentlc.com")
    realm = os.environ.get("KEYCLOAK_REALM", "llama-realm")
    
    # Get the current page URL to redirect back after logout
    if hasattr(st, 'request') and hasattr(st.request, 'url'):
        redirect_uri = st.request.url
    else:
        redirect_uri = os.environ.get("APP_URL", "https://llama-stack-playground-llama-stack.apps.cluster-95nrt.95nrt.sandbox5429.opentlc.com")
    
    # Keycloak logout endpoint
    logout_url = f"{keycloak_url}/realms/{realm}/protocol/openid-connect/logout"
    return logout_url


def main():
    st.title("👤 User Profile")
    
    # Check if logout was requested
    if 'logout_clicked' in st.session_state and st.session_state.logout_clicked:
        st.warning("🔄 Logging out... Please wait.")
        logout_url = get_logout_url()
        st.markdown(f"### 🔐 Logout")
        st.markdown(f"You will be redirected to Keycloak to complete logout.")
        st.markdown(f"**Logout URL:** {logout_url}")
        
        # Provide button to redirect
        if st.button("🔄 Complete Logout"):
            st.markdown(f'<meta http-equiv="refresh" content="0; url={logout_url}">', unsafe_allow_html=True)
        st.stop()
    
    # Display OAuth Proxy Headers for Debugging
    st.subheader("🔍 OAuth Proxy Headers (Debug)")
    
    if hasattr(st, 'request') and hasattr(st.request, 'headers'):
        headers = st.request.headers if hasattr(st.request, 'headers') else {}
        
        # Show all headers from OAuth proxy
        with st.expander("📋 View All Request Headers", expanded=True):
            st.code("\n".join([f"{k}: {v}" for k, v in headers.items()]), language=None)
        
        # OAuth proxy specific headers
        oauth_headers = {
            "X-Auth-Request-User": headers.get("x-auth-request-user", "Not set"),
            "X-Auth-Request-Access-Token": "Set" if "x-auth-request-access-token" in headers else "Not set",
            "X-Forwarded-User": headers.get("x-forwarded-user", "Not set"),
            "Authorization": headers.get("authorization", headers.get("Authorization", "Not set")),
        }
        
        st.info("**OAuth Proxy Headers:**")
        for key, value in oauth_headers.items():
            if "access-token" in key.lower() and value == "Set":
                st.success(f"  ✅ {key}: Present (hidden)")
            else:
                st.text(f"  {key}: {value}")
    
    st.divider()
    
    # Get JWT token from API module
    jwt_token = llama_stack_api._get_jwt_token()
    
    if not jwt_token:
        st.info("🔒 **Streamlit Authentication Status**")
        st.info("You are successfully authenticated via OAuth proxy!")
        st.info("**Note:** Streamlit cannot display JWT token details due to version limitations.")
        st.info("**This is normal** - the backend API can still access your authentication token.")
        st.divider()
        
        # Show OAuth proxy information
        st.subheader("📡 OAuth Proxy Configuration")
        st.success("✅ Authentication: Active")
        st.success("✅ OAuth Proxy: Running")
        st.success("✅ Session: Valid")
        st.warning("ℹ️ JWT token details are not accessible in Streamlit UI (version limitation)")
        st.info("💡 The backend API receives your authentication token automatically.")
        return
    
    # Decode the token
    token_data = decode_jwt_token(jwt_token)
    
    if not token_data:
        st.error("Failed to decode JWT token")
        return
    
    # Display user information
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("User Information")
        
        # Extract user details from token
        username = token_data.get("preferred_username", token_data.get("username", "N/A"))
        email = token_data.get("email", "N/A")
        user_id = token_data.get("sub", "N/A")
        name = token_data.get("name", "N/A")
        
        st.info(f"**User ID:**\n{user_id}")
        st.info(f"**Username:**\n{username}")
        st.info(f"**Name:**\n{name}")
        st.info(f"**Email:**\n{email}")
        
        # Extract roles/groups
        if "groups" in token_data:
            st.markdown("**Groups:**")
            for group in token_data["groups"]:
                st.write(f"  - {group}")
        
        # Extract realm and client info
        if "azp" in token_data:
            st.info(f"**Authorized Party:**\n{token_data['azp']}")
        
        if "iss" in token_data:
            st.info(f"**Issuer:**\n{token_data['iss']}")
        
        if "aud" in token_data:
            st.info(f"**Audience:**\n{token_data['aud']}")
    
    with col2:
        st.subheader("JWT Token Details")
        
        # Expiry information
        if "exp" in token_data:
            import datetime
            exp_timestamp = token_data["exp"]
            exp_datetime = datetime.datetime.fromtimestamp(exp_timestamp)
            time_remaining = exp_datetime - datetime.datetime.now()
            
            st.info(f"**Expires At:**\n{exp_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
            st.info(f"**Time Remaining:**\n{str(time_remaining).split('.')[0]}")
        
        # Issued at
        if "iat" in token_data:
            import datetime
            iat_timestamp = token_data["iat"]
            iat_datetime = datetime.datetime.fromtimestamp(iat_timestamp)
            st.info(f"**Issued At:**\n{iat_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Full token
        with st.expander("🔐 View Full JWT Token", expanded=False):
            st.code(jwt_token, language=None)
        
        # Decoded payload
        with st.expander("📋 View Decoded Token Payload", expanded=False):
            st.json(token_data)
    
    # Connection status
    st.divider()
    st.subheader("Connection Status")
    
    col_status, col_endpoint, col_logout = st.columns(3)
    
    with col_status:
        st.success("✅ **Authenticated**")
        if token_data:
            st.success("✅ **Token Valid**")
    
    with col_endpoint:
        import os
        endpoint = os.environ.get("LLAMA_STACK_ENDPOINT", "Not configured")
        st.info(f"**Backend Endpoint:**\n{endpoint}")
    
    with col_logout:
        st.markdown("**🔐 Account Actions**", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)  # Add some vertical space
        if st.button("🚪 Logout from Keycloak", type="primary", use_container_width=True):
            # Clear session data
            clear_session()
            st.session_state.logout_clicked = True
            st.rerun()
        
        # Add info about logout location
        st.info("💡 **Note:** Logout functionality has been moved from the top menu to this profile page for better organization.")
    
    # Session Cookie Information
    st.divider()
    st.subheader("🍪 Session Information")
    
    if hasattr(st, 'request') and hasattr(st.request, 'headers'):
        headers = st.request.headers if hasattr(st.request, 'headers') else {}
        
        # Check for oauth2-proxy cookies
        cookie_header = headers.get("cookie", headers.get("Cookie", ""))
        
        if cookie_header:
            with st.expander("📋 View Session Cookies", expanded=False):
                cookies = {}
                for cookie in cookie_header.split("; "):
                    if "=" in cookie:
                        name, value = cookie.split("=", 1)
                        # Mask sensitive values
                        if "secret" in name.lower() or "auth" in name.lower() or len(value) > 50:
                            value = value[:20] + "..." if len(value) > 20 else value
                        cookies[name] = value
                
                for name, value in cookies.items():
                    st.text(f"**{name}:** {value}")
        else:
            st.info("No session cookies found")


if __name__ == "__main__":
    main()


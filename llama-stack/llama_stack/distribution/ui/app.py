# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the terms described in the LICENSE file in
# the root directory of this source tree.
import streamlit as st
from modules.topbar import render_top_bar

# Set page config (must be at module level)
st.set_page_config(
    page_title="Llama Stack Playground",
    page_icon="🦙",
    layout="wide",
    initial_sidebar_state="expanded",
)


def main():
    # Render top navigation bar with user profile information
    render_top_bar()
    # Evaluation pages
    application_evaluation_page = st.Page(
        "page/evaluations/app_eval.py",
        title="Evaluations (Scoring)",
        icon="📊",
        default=False,
    )
    native_evaluation_page = st.Page(
        "page/evaluations/native_eval.py",
        title="Evaluations (Generation + Scoring)",
        icon="📊",
        default=False,
    )

    # Playground pages
    chat_page = st.Page("page/playground/chat.py", title="Chat", icon="💬", default=True)
    rag_page = st.Page("page/playground/rag.py", title="RAG", icon="💬", default=False)
    tool_page = st.Page("page/playground/tools.py", title="Tools", icon="🛠", default=False)

    # User profile page
    profile_page = st.Page("page/profile.py", title="Profile", icon="👤", default=False)

    # Distribution pages
    resources_page = st.Page("page/distribution/resources.py", title="Resources", icon="🔍", default=False)
    provider_page = st.Page(
        "page/distribution/providers.py",
        title="API Providers",
        icon="🔍",
        default=False,
    )

    pg = st.navigation(
        {
            "Playground": [
                chat_page,
                rag_page,
                tool_page,
                application_evaluation_page,
                native_evaluation_page,
            ],
            "Inspect": [provider_page, resources_page],
            "Account": [profile_page],
        },
        expanded=False,
    )
    pg.run()


if __name__ == "__main__":
    main()

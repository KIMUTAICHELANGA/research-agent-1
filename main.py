import streamlit as st
import os
from datetime import datetime

from research_components.database import get_db_connection
from research_components.research import run_tool
from research_components.components import display_analytics
from research_components.components import (
    display_analytics, 
    GeneralAgent, 
    PromptManager
)
from research_components.utils import load_research_history
from research_components.styles import apply_custom_styles

def main():
    st.set_page_config(
        page_title="Research Agent Dashboard",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    if 'dark_mode' not in st.session_state:
        st.session_state.dark_mode = False

    with st.sidebar:
        st.title("🛠 Research Tools")
        
        dark_mode = st.checkbox('Enable Dark Mode', value=st.session_state.dark_mode)
        
        if dark_mode != st.session_state.dark_mode:
            st.session_state.dark_mode = dark_mode
            st.rerun()

        if st.session_state.dark_mode:
            apply_custom_styles()
        
        tool_options = ["General Agent"]
        selected_tool = st.selectbox("Choose a Research Tool", tool_options)
        
        prompt_manager = PromptManager(
            agent_type="general",
            config_path="prompts"
        )
        
        available_prompts = prompt_manager.list_prompts()
        
        if available_prompts:
            st.markdown("### 📝 Select Research Style")
            selected_prompt_id = st.selectbox(
                "Choose Research Approach",
                options=available_prompts,
                format_func=lambda x: prompt_manager.get_prompt(x).metadata.get('description', x)
            )

            if selected_prompt_id:
                prompt = prompt_manager.get_prompt(selected_prompt_id)
                with st.expander("Prompt Details"):
                    st.markdown(f"**Use Case:** {prompt.metadata.get('use_case', 'General research')}")
                    st.markdown(f"**Type:** {prompt.metadata.get('type', 'Not specified')}")
        else:
            st.warning("No prompts found. Please check the prompts directory.")

        st.markdown("### ℹ️ Research Agent Info")
        st.write("Version: 1.0.0")
        st.write("Last Updated: January 2025")
        
        st.markdown("### 🗂️ Trace Management")
        if st.button("Clear Research History"):
            try:
                if os.path.exists('research_traces.jsonl'):
                    os.remove('research_traces.jsonl')
                st.success("Research history cleared successfully!")
                st.rerun()
            except Exception as e:
                st.error(f"Error clearing history: {str(e)}")

    st.title("🔍 Research Agent Dashboard")

    main_tab1, main_tab2 = st.tabs(["Research", "Analytics Dashboard"])

    with main_tab1:
        st.markdown("""
        Explore the world of information with our intelligent research tools. 
        Select a tool from the sidebar and discover insights!
        """)

        query = st.text_input("Enter your research query:", key="query_input")
        
        col1, col2 = st.columns([3, 1])
        with col2:
            search_button = st.button("Run Research", type="primary")
        
        if search_button and query:
            with st.spinner(f"Researching with {selected_tool}..."):
                try:
                    current_prompt = prompt_manager.get_prompt(selected_prompt_id)
                    tool = GeneralAgent(include_summary=True, custom_prompt=current_prompt)
                    result, trace = run_tool(tool_name=selected_tool, query=query, tool=tool)
                    
                    if result:
                        st.subheader("Research Summary")
                        st.markdown(result.summary)
                        
                        st.subheader("Detailed Content")
                        for item in result.content:
                            with st.expander(f"📄 {item.title}", expanded=True):
                                st.write(f"**URL:** {item.url}")
                                st.write(f"**Snippet:** {item.snippet}")
                                st.markdown("---")
                                meta_col1, meta_col2 = st.columns(2)
                                with meta_col1:
                                    st.write(f"Source: {item.source}")
                                with meta_col2:
                                    st.write(f"Retrieved: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                                if st.toggle("Show full content", key=f"content_{hash(item.url)}"):
                                    st.text_area("Full Content", value=item.content, height=300)

                except Exception as e:
                    st.error(f"An error occurred: {str(e)}")
        
        elif search_button and not query:
            st.warning("Please enter a query")

    with main_tab2:
        traces = load_research_history()
        db = get_db_connection()
        display_analytics(traces, db)

    st.markdown("---")
    st.markdown("""
    *Powered by AI Research Tools* | 
    [Documentation](https://github.com/yourusername/research-agent/docs)
    """)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        st.error(f"A critical error occurred: {str(e)}")
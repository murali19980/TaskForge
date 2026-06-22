import streamlit as st
import requests
import json
import os
import httpx
from dotenv import load_dotenv

# Load local environment settings if present
load_dotenv()

# Configure Streamlit page details
st.set_page_config(
    page_title="TaskForge - AI Task Decomposition",
    page_icon="⚒️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom premium styling via CSS injection
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif;
    }

    .main-title {
        font-size: 3rem;
        font-weight: 700;
        background: linear-gradient(135deg, #FF3366, #FF9933, #33CCFF);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
    }

    .sub-title {
        font-size: 1.2rem;
        color: #8892B0;
        margin-bottom: 2rem;
    }

    .metric-card {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 12px;
        padding: 1rem;
        text-align: center;
        transition: transform 0.2s ease, border-color 0.2s ease;
    }

    .metric-card:hover {
        transform: translateY(-2px);
        border-color: rgba(255, 255, 255, 0.15);
    }

    .task-card {
        background: rgba(255, 255, 255, 0.02);
        border-left: 4px solid #FF3366;
        border-radius: 4px 8px 8px 4px;
        padding: 1rem;
        margin-bottom: 1rem;
        border-top: 1px solid rgba(255, 255, 255, 0.03);
        border-right: 1px solid rgba(255, 255, 255, 0.03);
        border-bottom: 1px solid rgba(255, 255, 255, 0.03);
    }

    .task-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 0.5rem;
    }

    .task-title {
        font-weight: 600;
        font-size: 1.1rem;
        color: #E2E8F0;
    }

    .task-hours {
        font-size: 0.9rem;
        color: #FF9933;
        background: rgba(255, 153, 51, 0.1);
        padding: 2px 8px;
        border-radius: 12px;
        font-weight: 600;
    }

    .task-desc {
        color: #A0AEC0;
        font-size: 0.95rem;
        margin-bottom: 0.5rem;
    }

    .task-dep {
        font-size: 0.85rem;
        color: #33CCFF;
        background: rgba(51, 204, 255, 0.1);
        padding: 2px 8px;
        border-radius: 4px;
        display: inline-block;
    }
</style>
""", unsafe_allow_html=True)

# API Configurations
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
ENV_API_KEY = os.getenv("API_KEY", "dev_api_key_123")

# Sidebar Configuration
st.sidebar.title("⚒️ Settings")
api_key = st.sidebar.text_input("Bearer Token / API Key", value=ENV_API_KEY, type="password")

st.sidebar.markdown("---")

# Query backend /health to get status and OpenRouter quota
try:
    health_res = requests.get(f"{API_BASE_URL}/health", headers=get_headers(), timeout=5.0)
    if health_res.status_code in (200, 503):
        health_data = health_res.json()
        st.sidebar.subheader("System Status")
        db_status = "🟢" if health_data.get("database") == "healthy" else "🔴"
        ollama_status = "🟢" if health_data.get("ollama") == "healthy" else "🔴"
        or_status = health_data.get("openrouter", "unconfigured")
        or_indicator = "🟢" if or_status == "healthy" else ("🔴" if or_status == "unhealthy" else "⚪")

        st.sidebar.markdown(f"**Database**: {db_status} {health_data.get('database', 'unknown')}")
        st.sidebar.markdown(f"**Ollama**: {ollama_status} {health_data.get('ollama', 'unknown')}")
        st.sidebar.markdown(f"**OpenRouter**: {or_indicator} {or_status}")

        or_data = health_data.get("openrouter_data")
        if or_data:
            st.sidebar.subheader("OpenRouter Quota")
            rate_limit = or_data.get("rate_limit", {})
            requests_limit = rate_limit.get("requests")
            interval = rate_limit.get("interval")
            if requests_limit:
                st.sidebar.markdown(f"**Rate Limit**: {requests_limit} reqs / {interval}")

            limit = or_data.get("limit")
            usage = or_data.get("usage")
            if limit is not None:
                st.sidebar.markdown(f"**Usage**: ${usage:.5f} / ${limit:.5f}")
                st.sidebar.markdown(f"**Remaining**: ${limit - usage:.5f}")
            elif usage is not None:
                st.sidebar.markdown(f"**Usage**: ${usage:.5f}")
except Exception:
    pass

st.sidebar.markdown("---")
st.sidebar.subheader("Recent Decompositions")

# Helper to load authorization headers
def get_headers():
    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return headers

# Fetch and display recent runs in sidebar
try:
    recent_res = requests.get(f"{API_BASE_URL}/projects?limit=10", headers=get_headers(), timeout=5.0)
    if recent_res.status_code == 200:
        projects = recent_res.json()
        if not projects:
            st.sidebar.info("No projects decomposed yet.")
        for p in projects:
            # Clicking on a sidebar project triggers display of its cached tree
            if st.sidebar.button(p["goal"], key=f"proj_{p['id']}", use_container_width=True):
                st.session_state["active_decomposition"] = {
                    "task_tree": p["task_tree"],
                    "usage": p["usage"],
                    "cached": True
                }
    elif recent_res.status_code == 401:
        st.sidebar.warning("Unauthorized. Please check your API Key.")
    else:
        st.sidebar.error("Failed to load historical runs.")
except Exception as e:
    st.sidebar.info("Backend offline. Start FastAPI server to view history.")

# Header Section
st.markdown('<h1 class="main-title">TaskForge</h1>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Recursive AI Map-Reduce Task Decomposition Engine</div>', unsafe_allow_html=True)

# User Input Form
with st.container():
    goal_input = st.text_area(
        "Enter your high-level goal to decompose:",
        placeholder="e.g. Build a SaaS platform with authentication, stripe billing, and a project dashboard...",
        max_chars=1000,
        height=100
    )

    col1, col2 = st.columns([1, 4])
    with col1:
        submit_button = st.button("Decompose Goal", type="primary", use_container_width=True)

# Action handler for form submission
def render_specialists_progress(placeholder, completed_specialists, categories):
    with placeholder.container():
        st.write("🤖 **Specialists**: Category task generation in progress:")
        total = len(categories)
        if total > 0:
            done_count = sum(1 for status in completed_specialists.values() if "Completed" in status)
            progress_val = done_count / total
            st.progress(progress_val, text=f"Processed {done_count}/{total} categories")

        for cat in categories:
            status = completed_specialists.get(cat, "Pending")
            if "Completed" in status:
                st.write(f" - ✅ **{cat}**: {status}")
            elif status == "Running":
                st.write(f" - ⏳ **{cat}**: Generating tasks...")
            else:
                st.write(f" - 💤 **{cat}**: Pending...")

# Action handler for form submission
if submit_button:
    if not goal_input.strip():
        st.error("Please enter a valid goal.")
    else:
        if len(goal_input) > 2000:
            st.error("Goal exceeds the maximum length of 2000 characters.")
        else:
            with st.status("Decomposing goal (initializing mapping)...") as status:
                architect_status = st.empty()
                specialist_status = st.empty()
                refiner_status = st.empty()

                categories = []
                completed_specialists = {}

                try:
                    payload = {"goal": goal_input}
                    headers = get_headers()

                    with httpx.stream("POST", f"{API_BASE_URL}/decompose/stream", json=payload, headers=headers, timeout=120.0) as r:
                        if r.status_code == 401:
                            st.error("Authentication failed: Invalid Bearer Token / API Key.")
                            status.update(label="Decomposition failed", state="error")
                        elif r.status_code != 200:
                            st.error(f"Error ({r.status_code}): Request failed.")
                            status.update(label="Decomposition failed", state="error")
                        else:
                            for line in r.iter_lines():
                                if line.startswith("data: "):
                                    event_data = json.loads(line[6:])
                                    event_type = event_data.get("event")

                                    if event_type == "architect_start":
                                        status.update(label="Decomposing goal (Architect running)...", state="running")
                                        architect_status.markdown("⚡ **Architect**: Analyzing goal and mapping categories...")
                                    elif event_type == "architect_done":
                                        categories = event_data.get("categories", [])
                                        architect_status.markdown(f"✅ **Architect**: Mapped {len(categories)} categories: {', '.join(categories)}")
                                    elif event_type == "specialists_start":
                                        status.update(label="Decomposing goal (Specialists running)...", state="running")
                                        specialist_status.markdown("🤖 **Specialists**: Generating tasks for each category...")
                                    elif event_type == "specialist_start":
                                        cat = event_data.get("category")
                                        completed_specialists[cat] = "Running"
                                        render_specialists_progress(specialist_status, completed_specialists, categories)
                                    elif event_type == "specialist_done":
                                        cat = event_data.get("category")
                                        count = event_data.get("task_count", 0)
                                        completed_specialists[cat] = f"Completed ({count} tasks)"
                                        render_specialists_progress(specialist_status, completed_specialists, categories)
                                    elif event_type == "refiner_start":
                                        status.update(label="Decomposing goal (Refiner running)...", state="running")
                                        refiner_status.markdown("⛓️ **Refiner**: Resolving dependencies and finalizing tree...")
                                    elif event_type == "refiner_done":
                                        refiner_status.markdown("✅ **Refiner**: Dependency mapping and verification complete.")
                                    elif event_type == "done":
                                        status.update(label="Decomposition completed successfully!", state="complete")
                                        st.session_state["active_decomposition"] = event_data.get("data")
                                        st.success("Decomposition completed successfully!")
                                        st.rerun()
                                    elif event_type == "error":
                                        st.error(f"Decomposition failed: {event_data.get('message')}")
                                        status.update(label="Decomposition failed", state="error")
                except httpx.TimeoutException:
                    st.error("Request timed out. The LLM provider took too long to respond.")
                    status.update(label="Decomposition failed", state="error")
                except httpx.ConnectError:
                    st.error("Could not connect to the backend API. Please ensure your FastAPI server is running on port 8000.")
                    status.update(label="Decomposition failed", state="error")
                except Exception as e:
                    st.error(f"An unexpected error occurred: {str(e)}")
                    status.update(label="Decomposition failed", state="error")

# Display Active Decomposition Results
if "active_decomposition" in st.session_state:
    data = st.session_state["active_decomposition"]
    tree = data["task_tree"]
    usage = data["usage"]
    is_cached = data.get("cached", False)

    st.markdown("---")
    st.subheader(f"Project Decomposed Goal: **{tree['goal']}**")

    # Token Usage stats row
    col_tok1, col_tok2, col_tok3, col_tok4 = st.columns(4)
    with col_tok1:
        st.markdown(f"""
        <div class="metric-card">
            <h4 style="margin:0;color:#8892B0;">Total Tokens</h4>
            <h2 style="margin:5px 0 0 0;color:#33CCFF;">{usage['total_tokens']:,}</h2>
        </div>
        """, unsafe_allow_html=True)
    with col_tok2:
        cost_color = "#33CCFF" if usage['estimated_cost_usd'] > 0 else "#FF9933"
        st.markdown(f"""
        <div class="metric-card">
            <h4 style="margin:0;color:#8892B0;">Estimated Cost</h4>
            <h2 style="margin:5px 0 0 0;color:{cost_color};">${usage['estimated_cost_usd']:.5f}</h2>
        </div>
        """, unsafe_allow_html=True)
    with col_tok3:
        cache_status = "Cached (DB)" if is_cached else "Fresh Generation"
        status_color = "#FF9933" if is_cached else "#FF3366"
        st.markdown(f"""
        <div class="metric-card">
            <h4 style="margin:0;color:#8892B0;">Source</h4>
            <h2 style="margin:5px 0 0 0;color:{status_color};font-size:1.4rem;">{cache_status}</h2>
        </div>
        """, unsafe_allow_html=True)
    with col_tok4:
        # Download task tree JSON
        json_str = json.dumps(tree, indent=2)
        st.markdown("<div style='height: 18px;'></div>", unsafe_allow_html=True)
        st.download_button(
            label="Download Project JSON",
            data=json_str,
            file_name=f"taskforge_decomposition_{tree['goal'][:20].lower().replace(' ', '_')}.json",
            mime="application/json",
            use_container_width=True
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # Render Decomposed Categories & Tasks
    categories = tree.get("categories", [])
    if not categories:
        st.info("The generated task tree is empty.")
    else:
        for idx, category in enumerate(categories):
            # Render category expander
            with st.expander(f"📁 {category['name']} ({len(category['tasks'])} tasks)", expanded=(idx==0)):
                tasks = category.get("tasks", [])
                if not tasks:
                    st.write("No tasks generated for this category.")
                for task in tasks:
                    import html
                    safe_id = html.escape(str(task['id']))
                    safe_title = html.escape(str(task['title']))
                    safe_desc = html.escape(str(task['description']))
                    safe_deps_list = [html.escape(str(dep)) for dep in task.get('dependencies', [])]
                    safe_deps_str = ", ".join(safe_deps_list)

                    # Inject custom CSS styling for Task cards
                    st.markdown(f"""
                    <div class="task-card">
                        <div class="task-header">
                            <span class="task-title">[{safe_id}] {safe_title}</span>
                            <span class="task-hours">{task['estimated_hours']:.1f} hrs</span>
                        </div>
                        <div class="task-desc">{safe_desc}</div>
                        {f'<div class="task-dep">⛓️ Depends on: {safe_deps_str}</div>' if safe_deps_list else ''}
                    </div>
                    """, unsafe_allow_html=True)

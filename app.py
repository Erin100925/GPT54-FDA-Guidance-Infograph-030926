import os
import io
import time
import streamlit as st
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

# ---- Initialization and Session State ----
st.set_page_config(page_title="ReguAI - Regulatory Analysis", layout="wide", page_icon="🦾")

# Professional Default Prompts
DEFAULT_PROMPTS = {
    'deep_analysis': "Act as an Expert FDA Regulatory Consultant. Analyze the raw document and extract: 1. Device Description, 2. Intended Use, 3. Proposed Predicate Device(s), 4. Key Performance Testing, 5. Identified Biocompatibility. Format as structured Markdown.",
    'infographics': "Based on the structured review context, extract top-level metrics as a Markdown list: Risk Class, Predicate Match %, Missing Docs count, and Approval Probability %.",
    'checklist': "Based on the review context, generate the top 5 mandatory submission checklist items for this specific medical device. Use Markdown checklist format (- [ ] Task).",
    'risk_radar': "Based on the review context, identify the top 4 product/regulatory risks (e.g., Software, Bio). Output a Markdown table with columns: Risk Category, Severity (High/Medium/Low), Mitigated (Yes/No).",
    'se_matrix': "Based on the review context, build a Substantial Equivalence (SE) Matrix comparing the subject device to the predicate. Output a Markdown table with columns: Feature, Subject Device, Predicate, Equivalence.",
    'fda_letter': "Based on the review context, draft a formal, ready-to-sign FDA Cover Letter for this premarket notification submission."
}

MODEL_OPTS =['gpt-4o', 'gpt-4o-mini', 'gemini-1.5-pro', 'gemini-1.5-flash', 'claude-3.5-sonnet']

default_states = {
    'language': 'English', 'theme': 'light', 'painter_style': 'Van Gogh', 
    'api_key': os.getenv('OPENAI_API_KEY') or '',
    'doc_content': "", 'review_md': "", 'dashboard_generated': False, 
    'chat_history':[], 'prompt_deep_analysis': DEFAULT_PROMPTS['deep_analysis'],
    'model_global': MODEL_OPTS[0]
}
for key, value in default_states.items():
    if key not in st.session_state:
        st.session_state[key] = value

AGENTS =[
    {'id': 'infographics', 'label': 'Infographics', 'icon': '📊'}, 
    {'id': 'checklist', 'label': 'Checklist', 'icon': '✅'},
    {'id': 'risk_radar', 'label': 'Risk Radar', 'icon': '🎯'}, 
    {'id': 'se_matrix', 'label': 'SE Matrix', 'icon': '🧮'},
    {'id': 'fda_letter', 'label': 'FDA Letter', 'icon': '📝'}
]

for ag in AGENTS:
    if f"prompt_{ag['id']}" not in st.session_state:
        st.session_state[f"prompt_{ag['id']}"] = DEFAULT_PROMPTS[ag['id']]
    if f"model_{ag['id']}" not in st.session_state:
        st.session_state[f"model_{ag['id']}"] = MODEL_OPTS[0]
    if f"res_{ag['id']}" not in st.session_state:
        st.session_state[f"res_{ag['id']}"] = "" # Holds the generated output for each agent

# ---- AI Processing Engine (Real API + Smart Mock Fallback) ----
def generate_ai_response(prompt, context, model, api_key):
    full_prompt = f"System Prompt: {prompt}\n\nContext:\n{context}\n\nPlease generate the response based strictly on the context above."
    
    # Live API Call Logic (If key provided)
    if api_key and api_key.startswith("sk-"):
        try:
            import openai
            client = openai.OpenAI(api_key=api_key)
            resp = client.chat.completions.create(
                model="gpt-4o-mini", # Standardizing to mini for speed if using OpenAI
                messages=[{"role": "user", "content": full_prompt}]
            )
            return resp.choices[0].message.content
        except Exception as e:
            st.error(f"API Error: {e}")
            # Fallback to simulation if error
            pass 

    # SMART SIMULATION MODE: Actually uses context to prove logic flow
    time.sleep(1.5) # simulate latency
    ctx_snippet = (context[:150].replace('\n', ' ') + "...") if len(context) > 0 else "[Empty Context]"
    
    if "Device Description" in prompt:
        return f"### AI Regulatory Executive Summary\n*Processed from Step 1 Input:* `{ctx_snippet}`\n\n**Device Description:** Extracted software-controlled Class II device.\n**Indications for Use:** Intended for general surgery.\n**Proposed Predicate:** Matches intended use perfectly.\n**Performance Testing:** Bench testing passed.\n**Biocompatibility:** ISO 10993-1 evaluation complete."
    elif "metrics" in prompt:
        return f"### 📊 Dashboard Metrics\n*Derived from Step 2 Review:*\n- **Risk Class:** Class II\n- **Predicate Match:** 94%\n- **Missing Docs:** 2 Files\n- **Approval Probability:** 88%\n\n> *Source Snippet used: {ctx_snippet}*"
    elif "checklist" in prompt:
        return f"### ✅ Submission Checklist\n*Derived from Step 2 Review:*\n- [x] Cover Letter\n- [x] Indications for Use Statement\n- [ ] 510(k) Summary\n- [ ] Software Architecture Document\n- [ ] Biocompatibility Report"
    elif "risk" in prompt.lower():
        return f"### 🎯 Risk Radar\n*Derived from Step 2 Review:*\n| Risk Category | Severity | Mitigated? |\n|---|---|---|\n| Software Failure | High | No ⚠️ |\n| Biocompatibility | Medium | Yes ✅ |\n| Electrical Safety | Low | Yes ✅ |\n| Usability | Medium | Pending 🔄 |"
    elif "matrix" in prompt.lower():
        return f"### 🧮 SE Matrix\n*Derived from Step 2 Review:*\n| Feature | Subject Device | Predicate | Equivalence |\n|---|---|---|---|\n| Intended Use | Tissue Cutting | Tissue Cutting | Same |\n| Material | Stainless Steel | Stainless Steel | Same |\n| Sterilization | Gamma | EO Gas | Different |\n| Software | Moderate | Moderate | Same |"
    elif "letter" in prompt.lower():
        return f"### 📝 FDA Cover Letter Draft\n**Date:** {time.strftime('%B %d, %Y')}\n\n**U.S. Food and Drug Administration**\nCenter for Devices and Radiological Health\n\n**SUBJECT: Premarket Notification 510(k)**\n\nDear Sir/Madam,\nWe are submitting this 510(k) based on the device outlined in our review:\n> *{ctx_snippet}*\n\nSincerely,\nRegulatory Affairs Team"
    else:
        return f"**AI Generated Response:**\nBased on your context `{ctx_snippet}`, the analysis is complete."

# ---- Custom WOW CSS Injection ----
def inject_custom_css():
    theme_bg = "#121212" if st.session_state['theme'] == 'dark' else "#F8FAFC"
    theme_color = "#E2E8F0" if st.session_state['theme'] == 'dark' else "#0F172A"
    card_bg = "#1E293B" if st.session_state['theme'] == 'dark' else "#FFFFFF"
    
    css = f"""
    <style>
        .stApp {{ background-color: {theme_bg}; color: {theme_color}; font-family: 'Inter', sans-serif; }}
        h1, h2, h3 {{ background: linear-gradient(45deg, #3B82F6, #8B5CF6, #EC4899); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-weight: 800; }}
        .stTextArea textarea {{ background-color: {card_bg}; color: {theme_color}; border-radius: 8px; border: 1px solid #CBD5E1; }}
        div[data-testid="stExpander"] {{ background-color: {card_bg}; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); border: none; }}
        div.stButton > button:first-child {{ background: linear-gradient(90deg, #3B82F6, #8B5CF6); color: white; border: none; border-radius: 8px; font-weight: 600; transition: all 0.3s ease; }}
        div.stButton > button:first-child:hover {{ transform: translateY(-2px); box-shadow: 0 6px 15px rgba(139, 92, 246, 0.4); }}
        .stChatMessage {{ background-color: {card_bg}; border-radius: 12px; padding: 15px; box-shadow: 0 2px 10px rgba(0,0,0,0.03); }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

inject_custom_css()

# ---- TOP NAV BAR ----
col1, col2, col3, col4 = st.columns([2.5, 1, 1, 1])
with col1:
    st.markdown("<h1>ReguAI WOW 🦾</h1>", unsafe_allow_html=True)
    st.caption("Next-Gen Regulatory Analysis & FDA Submission Intelligence")
with col2:
    lang = st.selectbox("Language", ['English', '繁體中文'], index=0 if st.session_state['language']=='English' else 1, key="langselect")
    st.session_state['language'] = lang
with col3:
    theme = st.selectbox("Theme",['Light', 'Dark'], index=0 if st.session_state['theme']=='light' else 1, key="themeselect")
    if theme.lower() != st.session_state['theme']:
        st.session_state['theme'] = theme.lower()
        st.rerun()
with col4:
    PAINTERS =['Van Gogh','Monet','Picasso','Da Vinci','Klimt','Dali','Matisse','Warhol']
    painter_style = st.selectbox("🎨 Painter Style", PAINTERS, key="paintersel")
    if st.button("Jackpot! 🎲", use_container_width=True):
        import random
        st.session_state['painter_style'] = random.choice(PAINTERS)
        st.rerun()

# ---- Secure API Key & Navigation Sidebar ----
with st.sidebar:
    st.markdown("### 🔐 Authentication")
    api_key_input = st.text_input("OpenAI API Key (Optional)", type="password", value=st.session_state['api_key'] if st.session_state['api_key'] else "")
    if api_key_input != st.session_state['api_key']:
        st.session_state['api_key'] = api_key_input
    if not st.session_state['api_key']:
        st.info("🟢 Running in **Simulation Mode** (Context-Aware Mocking).")

    st.markdown("---")
    st.markdown("### 🚀 Pipeline Flow")
    steps =['1. Upload Raw Doc', '2. Review & AI Parsing', '3. Dashboard Features', '4. AI Note Keeper']
    current_step = st.radio("Navigate:", steps, label_visibility="collapsed")


# ==========================================
# STEP 1: UPLOAD (Inputs to doc_content)
# ==========================================
if current_step == '1. Upload Raw Doc':
    st.markdown("<h2>Step 1: Ingest Raw Regulatory Document</h2>", unsafe_allow_html=True)
    st.write("Upload your FDA 510(k), PMA, CER, or paste raw text below.")
    
    colA, colB = st.columns(2)
    with colA:
        uploaded_file = st.file_uploader("Drop PDF/Text file here", type=["pdf", "txt"])
    with colB:
        raw_text = st.text_area("OR Paste Raw Text Here", height=150)
        
    if st.button("🚀 Ingest & Save Data", use_container_width=True):
        content = ""
        if uploaded_file:
            content = uploaded_file.read().decode('utf-8') if uploaded_file.name.endswith('.txt') else f"[PDF Extracted Data from {uploaded_file.name}]"
        if raw_text:
            content += "\n\n" + raw_text
            
        if content.strip():
            st.session_state['doc_content'] = content.strip()
            st.success("✅ Document Ingested successfully! Go to Step 2.")
            st.balloons()
        else:
            st.error("⚠️ Please upload a file or paste text.")

    if st.session_state['doc_content']:
        st.info(f"**Currently in memory:** {len(st.session_state['doc_content'])} characters ingested.")

# ==========================================
# STEP 2: REVIEW (doc_content -> review_md)
# ==========================================
elif current_step == '2. Review & AI Parsing':
    st.markdown("<h2>Step 2: Deep AI Parsing & Review</h2>", unsafe_allow_html=True)
    if not st.session_state['doc_content']:
        st.warning("⚠️ No document found. Please go back to Step 1 and Ingest Data.")
        st.stop()

    with st.expander("⚙️ Configure Deep AI Analysis Prompt", expanded=False):
        st.session_state['prompt_deep_analysis'] = st.text_area("Master Prompt:", value=st.session_state['prompt_deep_analysis'], height=100)
        st.session_state['model_global'] = st.selectbox("Master Model:", MODEL_OPTS, index=MODEL_OPTS.index(st.session_state['model_global']))

    col_text, col_actions = st.columns([3, 1])
    
    with col_actions:
        st.markdown("### Actions")
        if st.button("✨ Run Deep AI Analysis", use_container_width=True):
            with st.spinner(f"🤖 Processing Step 1 Data using {st.session_state['model_global']}..."):
                # LOGIC FIX: Feeding Step 1 content into Step 2 AI
                ai_structured_text = generate_ai_response(
                    prompt=st.session_state['prompt_deep_analysis'],
                    context=st.session_state['doc_content'],
                    model=st.session_state['model_global'],
                    api_key=st.session_state['api_key']
                )
                st.session_state["review_md"] = ai_structured_text
                st.session_state["dashboard_generated"] = True
            st.success("✅ Analysis Complete!")
            st.rerun()

    with col_text:
        doc_text = st.text_area(
            "Structured Document (Will be used as Context for Step 3)", 
            value=st.session_state["review_md"] if st.session_state["review_md"] else "Click 'Run Deep AI Analysis' to process the raw document.", 
            height=400
        )
        if doc_text != st.session_state["review_md"]:
            st.session_state["review_md"] = doc_text

# ==========================================
# STEP 3: DASHBOARD (review_md -> Agents)
# ==========================================
elif current_step == '3. Dashboard Features':
    st.markdown("<h2>Step 3: Interactive Multi-Agent Dashboard</h2>", unsafe_allow_html=True)
    if not st.session_state["dashboard_generated"] or not st.session_state["review_md"]:
        st.warning("⚠️ Run Deep AI Analysis in Step 2 first. The Dashboard requires Step 2 context.")
        st.stop()
        
    st.caption("Each agent reads your Step 2 Structured Review to generate highly specific dashboard metrics.")

    tabs = st.tabs([f"{ag['icon']} {ag['label']}" for ag in AGENTS])
    
    for i, ag in enumerate(AGENTS):
        with tabs[i]:
            st.markdown(f"### {ag['icon']} {ag['label']} Generator")
            
            with st.expander(f"⚙️ Configure Prompt & Model"):
                st.session_state[f"prompt_{ag['id']}"] = st.text_area("Agent Prompt:", value=st.session_state[f"prompt_{ag['id']}"], height=80, key=f"txt_{ag['id']}")
            
            # LOGIC FIX: Dashboard Generation driven explicitly by Step 2 review_md
            if st.button(f"🚀 Generate {ag['label']} based on Step 2 Context", key=f"btn_{ag['id']}"):
                with st.spinner(f"Generating based on Review Context..."):
                    result = generate_ai_response(
                        prompt=st.session_state[f"prompt_{ag['id']}"],
                        context=st.session_state['review_md'], # Using step 2 as context!
                        model=st.session_state[f"model_{ag['id']}"],
                        api_key=st.session_state['api_key']
                    )
                    st.session_state[f"res_{ag['id']}"] = result
                st.success("✅ Generated successfully!")

            st.markdown("---")
            
            # Display dynamically generated Markdown Results
            if st.session_state[f"res_{ag['id']}"]:
                with st.container(border=True):
                    st.markdown(st.session_state[f"res_{ag['id']}"])
            else:
                st.info("Click Generate to create this dashboard component.")

# ==========================================
# STEP 4: AI NOTE KEEPER (review_md -> Chat)
# ==========================================
elif current_step == '4. AI Note Keeper':
    st.markdown("<h2>Step 4: AI Note Keeper 🤖</h2>", unsafe_allow_html=True)
    st.write("Chat directly with your structured regulatory document (Reads Step 2 Context).")
    
    if not st.session_state["review_md"]:
        st.warning("⚠️ Complete Step 2 first to give the AI context.")
        st.stop()

    # --- 🪄 4 AI MAGICS BAR ---
    st.markdown("#### 🪄 AI Magics (Quick Actions)")
    colM1, colM2, colM3, colM4 = st.columns(4)
    magic_prompt = None
    if colM1.button("📊 Summarize Gaps", use_container_width=True):
        magic_prompt = "Identify what critical testing or documentation is missing based on the Step 2 context."
    if colM2.button("🔍 Regulatory Strategy", use_container_width=True):
        magic_prompt = "Based on the device description, suggest a 3-step high-level FDA clearance strategy."
    if colM3.button("🗣️ Explain to Layman", use_container_width=True):
        magic_prompt = "Translate the Step 2 technical text into a simple, layman-friendly explanation."
    if colM4.button("📩 Draft RFI Response", use_container_width=True):
        magic_prompt = "Draft a professional response to an FDA Request for Additional Information (RFI) regarding biocompatibility."

    if magic_prompt:
        st.session_state.chat_history.append({"role": "user", "content": magic_prompt})

    # --- CHAT INTERFACE ---
    chat_container = st.container(height=450)
    
    with chat_container:
        if not st.session_state.chat_history:
            st.info("👋 Hello! I am your AI Regulatory Assistant. Ask a question or use a Magic button above.")
            
        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"], avatar="🤖" if msg["role"] == "assistant" else "👤"):
                st.markdown(msg["content"])

        # Handle AI Generation Flow based on Step 2 Context
        if st.session_state.chat_history and st.session_state.chat_history[-1]["role"] == "user":
            user_msg = st.session_state.chat_history[-1]["content"]
            with st.chat_message("assistant", avatar="🤖"):
                with st.spinner("Consulting Step 2 Document Context..."):
                    reply = generate_ai_response(
                        prompt="You are a Regulatory AI assistant. Answer the user based ONLY on the provided context.",
                        context=f"USER QUESTION: {user_msg}\n\nDOCUMENT CONTEXT: {st.session_state['review_md']}",
                        model=st.session_state['model_global'],
                        api_key=st.session_state['api_key']
                    )
                    st.markdown(reply)
                    st.session_state.chat_history.append({"role": "assistant", "content": reply})

    # Standard Chat Input
    if prompt := st.chat_input("E.g., What is the primary predicate device?"):
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        st.rerun()

import os
import io
import time
import pandas as pd
import streamlit as st
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

# ---- Initialization and Session State ----
st.set_page_config(page_title="ReguAI - Regulatory Analysis", layout="wide", page_icon="🦾")

# Professional Default Prompts
DEFAULT_PROMPTS = {
    'deep_analysis': "Act as an Expert FDA Regulatory Consultant. Analyze the raw document and extract: 1. Device Description, 2. Intended Use / Indications for Use, 3. Proposed Predicate Device(s), 4. Key Performance Testing, 5. Identified Biocompatibility & Software components. Format as structured Markdown.",
    'infographics': "Based on the structured review context, extract top-level metrics: Risk Class, Predicate Match %, Missing Docs count, and Approval Probability %. Format clearly.",
    'checklist': "Based on the review context, generate the top 5 mandatory submission checklist items for this specific medical device.",
    'risk_radar': "Based on the review context, identify the top 4 product/regulatory risks (e.g., Software, Bio, EMC). Assign Severity (High/Medium/Low) and Mitigation Status.",
    'se_matrix': "Based on the review context, build a Substantial Equivalence (SE) Matrix comparing the subject device to the predicate across Intended Use, Material, Sterilization, and Software.",
    'fda_letter': "Based on the review context, draft a formal, ready-to-sign FDA Cover Letter for this premarket notification submission."
}

MODEL_OPTS =['gpt-4o', 'gpt-4o-mini', 'gemini-1.5-pro', 'gemini-1.5-flash', 'claude-3.5-sonnet']

default_states = {
    'language': 'English', 'theme': 'light', 'painter_style': 'Van Gogh', 
    'api_key': os.getenv('OPENAI_API_KEY') or os.getenv('GEMINI_API_KEY'),
    'doc_content': "", 'review_md': "", 'dashboard_generated': False, 
    'chat_history':[], 'checklist_states': [False]*5,
    'prompt_deep_analysis': DEFAULT_PROMPTS['deep_analysis'],
    'model_global': MODEL_OPTS[0]
}
for key, value in default_states.items():
    if key not in st.session_state:
        st.session_state[key] = value

# Initialize Agent specific states
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
        .magic-btn {{ display: flex; gap: 10px; margin-bottom: 15px; }}
        div.stButton > button:first-child {{
            background: linear-gradient(90deg, #3B82F6, #8B5CF6); color: white; border: none; border-radius: 8px; font-weight: 600; transition: all 0.3s ease;
        }}
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
    theme = st.selectbox("Theme", ['Light', 'Dark'], index=0 if st.session_state['theme']=='light' else 1, key="themeselect")
    if theme.lower() != st.session_state['theme']:
        st.session_state['theme'] = theme.lower()
        st.rerun()
with col4:
    PAINTERS =['Van Gogh','Monet','Picasso','Da Vinci','Klimt','Dali','Matisse','Warhol']
    painter_style = st.selectbox("🎨 Painter Style", PAINTERS, key="paintersel")
    if st.button("Jackpot! 🎲", use_container_width=True):
        import random
        new_style = random.choice(PAINTERS)
        st.session_state['painter_style'] = new_style
        st.rerun()

# ---- Secure API Key & Navigation Sidebar ----
with st.sidebar:
    st.markdown("### 🔐 Authentication")
    api_key_input = st.text_input("API Key (Optional for Demo)", type="password", value=st.session_state['api_key'] if st.session_state['api_key'] else "")
    if api_key_input != st.session_state['api_key']:
        st.session_state['api_key'] = api_key_input
    if not st.session_state['api_key']:
        st.info("🟢 Running in **Simulation Mode**.")

    st.markdown("---")
    st.markdown("### 🚀 Workflow Steps")
    steps = ['1. Upload', '2. Review & AI Parsing', '3. Dashboard Features', '4. AI Note Keeper']
    current_step = st.radio("Navigate:", steps, label_visibility="collapsed")


# ==========================================
# STEP 1: UPLOAD
# ==========================================
if current_step == '1. Upload':
    st.markdown("<h2>Step 1: Ingest Regulatory Document</h2>", unsafe_allow_html=True)
    st.write("Upload your FDA 510(k), PMA, CER, or paste raw regulatory text.")
    
    colA, colB = st.columns(2)
    with colA:
        uploaded_file = st.file_uploader("Drop PDF/Text file here", type=["pdf", "txt"])
    with colB:
        raw_text = st.text_area("OR Paste Raw Text Here", height=150)
        
    if st.button("🚀 Ingest & Continue", use_container_width=True):
        content = ""
        if uploaded_file:
            content = uploaded_file.read().decode('utf-8') if uploaded_file.name.endswith('.txt') else f"[PDF Extracted] {uploaded_file.name}"
        if raw_text:
            content += "\n\n" + raw_text
            
        if content.strip():
            st.session_state['doc_content'] = content
            st.success("✅ Document Ingested! Please move to Step 2.")
            st.balloons()
        else:
            st.error("⚠️ Please upload a file or paste text.")

# ==========================================
# STEP 2: REVIEW
# ==========================================
elif current_step == '2. Review & AI Parsing':
    st.markdown("<h2>Step 2: Deep AI Parsing & Review</h2>", unsafe_allow_html=True)
    if not st.session_state['doc_content']:
        st.warning("⚠️ No document found. Please go back to Step 1.")
        st.stop()

    with st.expander("⚙️ Configure Deep AI Analysis Prompt", expanded=False):
        st.session_state['prompt_deep_analysis'] = st.text_area("Master Prompt for initial structuring:", value=st.session_state['prompt_deep_analysis'], height=100)
        st.session_state['model_global'] = st.selectbox("Master Model:", MODEL_OPTS, index=MODEL_OPTS.index(st.session_state['model_global']))

    col_text, col_actions = st.columns([3, 1])
    
    with col_actions:
        st.markdown("### Actions")
        if st.button("✨ Run Deep AI Analysis", use_container_width=True):
            with st.spinner(f"🤖 Processing with {st.session_state['model_global']}..."):
                time.sleep(2) # Simulate API Call
                # Simulated response based on the prompt
                ai_structured_text = f"""### AI Regulatory Executive Summary
**Device Description:** A software-controlled Class II electrosurgical unit.
**Indications for Use:** Intended for cutting and coagulation of tissue during general surgery.
**Proposed Predicate:** K192233 (Electrosurgical Generator).
**Performance Testing:** Bench testing passed for thermal spread.
**Biocompatibility:** ISO 10993-1 compliant (Patient contacting parts).

*Generated using model: {st.session_state['model_global']}*
"""
                st.session_state["review_md"] = ai_structured_text
                st.session_state["dashboard_generated"] = True
            st.success("✅ Analysis Complete!")
            st.rerun()

    with col_text:
        doc_text = st.text_area("Structured Document Content (Markdown)", value=st.session_state["review_md"] if st.session_state["review_md"] else "Click 'Run Deep AI Analysis' to process the raw document.", height=400)
        if doc_text != st.session_state["review_md"]:
            st.session_state["review_md"] = doc_text

# ==========================================
# STEP 3: DASHBOARD (Agent Settings)
# ==========================================
elif current_step == '3. Dashboard Features':
    st.markdown("<h2>Step 3: Interactive Multi-Agent Dashboard</h2>", unsafe_allow_html=True)
    if not st.session_state["dashboard_generated"]:
        st.warning("⚠️ Run Deep AI Analysis in Step 2 first.")
        st.stop()
        
    st.caption("Each tab represents a specialized AI Agent. You can configure their specific prompts and models below.")

    tabs = st.tabs([f"{ag['icon']} {ag['label']}" for ag in AGENTS])
    
    # Render each agent's tab dynamically
    for i, ag in enumerate(AGENTS):
        with tabs[i]:
            st.markdown(f"### {ag['icon']} {ag['label']} Generator")
            
            # Agent Specific Configurations
            with st.expander(f"⚙️ Configure {ag['label']} Prompt & Model"):
                st.session_state[f"prompt_{ag['id']}"] = st.text_area(
                    "Agent Prompt:", value=st.session_state[f"prompt_{ag['id']}"], height=80, key=f"txt_{ag['id']}"
                )
                st.session_state[f"model_{ag['id']}"] = st.selectbox(
                    "Agent Model:", MODEL_OPTS, index=MODEL_OPTS.index(st.session_state[f"model_{ag['id']}"]), key=f"mod_{ag['id']}"
                )
            
            # Action Button
            if st.button(f"🚀 Generate {ag['label']} based on Step 2 Context", key=f"btn_{ag['id']}"):
                with st.spinner(f"Generating with {st.session_state[f'model_{ag['id']}']}..."):
                    time.sleep(1.5) # Simulate API call using review_md + agent prompt
                    st.toast(f"✅ {ag['label']} updated successfully!")

            st.markdown("---")
            
            # Simulated Dynamic Output Rendering
            if ag['id'] == 'infographics':
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Risk Class", "Class II", "Low Risk")
                m2.metric("Predicate Match", "94%", "+2% avg")
                m3.metric("Missing Docs", "2", "- Requires action", delta_color="inverse")
                m4.metric("Approval Prob.", "88%", "High")
                st.progress(88, text=f"AI Confidence Score (Model: {st.session_state[f'model_{ag['id']}']})")

            elif ag['id'] == 'checklist':
                checks =["Cover Letter & Form 3514", "Indications for Use Statement", "510(k) Summary", "Software Arch. Doc", "Biocompatibility Test"]
                for j, task in enumerate(checks):
                    st.session_state['checklist_states'][j] = st.checkbox(task, value=st.session_state['checklist_states'][j], key=f"chk_{ag['id']}_{j}")
                if all(st.session_state['checklist_states']):
                    st.success("🎉 All documents ready for submission!")

            elif ag['id'] == 'risk_radar':
                risk_data = pd.DataFrame({
                    "Risk Category":["Software Failure", "Biocompatibility", "Electrical Safety", "Usability"],
                    "Severity":["High", "Medium", "Low", "Medium"],
                    "Mitigated?":["No ⚠️", "Yes ✅", "Yes ✅", "Pending 🔄"]
                })
                def style_risks(val):
                    color = '#ef4444' if val == 'High' else '#f59e0b' if val == 'Medium' else '#10b981' if val == 'Low' else ''
                    return f'background-color: {color}; color: white; font-weight:bold;' if color else ''
                st.dataframe(risk_data.style.map(style_risks, subset=['Severity']), use_container_width=True)

            elif ag['id'] == 'se_matrix':
                se_data = pd.DataFrame({
                    "Feature": ["Intended Use", "Material", "Sterilization", "Software Level"],
                    "Subject Device": ["Cutting Tissue", "Stainless Steel", "Gamma", "Moderate"],
                    "Predicate":["Cutting Tissue", "Stainless Steel", "EO Gas", "Moderate"],
                    "Equivalence":["Same", "Same", "Different", "Same"]
                })
                st.data_editor(se_data, use_container_width=True)

            elif ag['id'] == 'fda_letter':
                draft = f"Date: {time.strftime('%B %d, %Y')}\n\nU.S. Food and Drug Administration\n\nSUBJECT: Premarket Notification 510(k)\n\nDear Sir/Madam,\nWe are submitting this 510(k) based on the context provided by {st.session_state[f'model_{ag['id']}']}. The device is substantially equivalent to K192233..."
                st.text_area("Edit Draft Letter", value=draft, height=250, key="fda_txt")

# ==========================================
# STEP 4: AI NOTE KEEPER & MAGICS
# ==========================================
elif current_step == '4. AI Note Keeper':
    st.markdown("<h2>Step 4: AI Note Keeper 🤖</h2>", unsafe_allow_html=True)
    st.write("Chat directly with your structured regulatory document using Custom AI Magics.")

    # --- 🪄 4 AI MAGICS BAR ---
    st.markdown("#### 🪄 AI Magics (Quick Actions)")
    colM1, colM2, colM3, colM4 = st.columns(4)
    magic_prompt = None
    if colM1.button("📊 Executive Summary", use_container_width=True):
        magic_prompt = "Provide a 3-bullet point executive summary of the entire submission."
    if colM2.button("🔍 Find Missing Gaps", use_container_width=True):
        magic_prompt = "Identify what critical testing or documentation is missing for an FDA submission."
    if colM3.button("🗣️ Explain to Layman", use_container_width=True):
        magic_prompt = "Translate the indications for use and core technology into simple, layman terms."
    if colM4.button("📩 Draft RFI Response", use_container_width=True):
        magic_prompt = "Draft a professional response to an FDA Request for Additional Information (RFI) regarding biocompatibility."

    if magic_prompt:
        st.session_state.chat_history.append({"role": "user", "content": magic_prompt})

    # --- CHAT INTERFACE ---
    chat_container = st.container(height=450)
    
    with chat_container:
        if not st.session_state.chat_history:
            st.info("👋 Hello! I am your AI Regulatory Assistant. Ask a question or use an AI Magic button above.")
            
        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"], avatar="🤖" if msg["role"] == "assistant" else "👤"):
                st.markdown(msg["content"])

        # Handle generation of AI response
        if magic_prompt:
            with st.chat_message("assistant", avatar="🤖"):
                with st.spinner("Casting AI Magic... ✨"):
                    time.sleep(1.5)
                    # Simulated targeted responses for the magics
                    reply = ""
                    if "executive summary" in magic_prompt.lower():
                        reply = "✨ **Executive Summary:**\n- **Device:** Class II Electrosurgical unit.\n- **Predicate:** K192233 (Substantially Equivalent).\n- **Status:** Bench testing passed; missing sterilization validation."
                    elif "missing gaps" in magic_prompt.lower():
                        reply = "✨ **Gap Analysis:**\n1. **Sterilization Validation:** Missing final report for Gamma irradiation.\n2. **Software:** Cybersecurity vulnerability assessment not found."
                    elif "layman" in magic_prompt.lower():
                        reply = "✨ **Layman Translation:**\nThis device is a high-tech electronic scalpel. Instead of a standard blade, it uses safe electrical currents to cut tissue and stop bleeding at the same time during surgery."
                    elif "rfi" in magic_prompt.lower():
                        reply = "✨ **Draft RFI Response:**\n*Dear FDA Reviewer,*\nIn response to your inquiry regarding biocompatibility, we have attached the updated ISO 10993-1 extractables and leachables report..."
                    
                    st.markdown(reply)
                    st.session_state.chat_history.append({"role": "assistant", "content": reply})

    # Standard User Chat Input
    if prompt := st.chat_input("E.g., What are the software documentation requirements?"):
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        st.rerun() # Rerun to display user message and then trigger assistant
        
    # Standard AI Response triggering after user input
    if st.session_state.chat_history and st.session_state.chat_history[-1]["role"] == "user" and not magic_prompt:
        with chat_container:
            with st.chat_message("assistant", avatar="🤖"):
                with st.spinner("Analyzing context..."):
                    time.sleep(1)
                    reply = f"Based on the Review Context, here is the information regarding: **{st.session_state.chat_history[-1]['content']}**\n\nThe FDA requires moderate level of concern software documentation as outlined in the 2023 premarket cybersecurity guidance."
                    st.markdown(reply)
                    st.session_state.chat_history.append({"role": "assistant", "content": reply})

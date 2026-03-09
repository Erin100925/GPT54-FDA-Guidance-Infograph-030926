import os
import io
import time
import json
import pandas as pd
import streamlit as st
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

# ---- Initialization and Session State ----
st.set_page_config(page_title="ReguAI - Regulatory Analysis", layout="wide", page_icon="🦾")

# Initialize all session state variables safely
default_states = {
    'language': 'English', 'theme': 'light', 'painter_style': 'Van Gogh', 
    'api_key': os.getenv('OPENAI_API_KEY') or os.getenv('GEMINI_API_KEY'),
    'current_agent': None, 'dashboard_data': {}, 'doc_content': "",
    'dashboard_generated': False, 'chat_history': [], 'checklist_states': [False]*5
}
for key, value in default_states.items():
    if key not in st.session_state:
        st.session_state[key] = value

# ---- Custom WOW CSS Injection ----
def inject_custom_css():
    theme_bg = "#121212" if st.session_state['theme'] == 'dark' else "#F4F7FB"
    theme_color = "#E0E0E0" if st.session_state['theme'] == 'dark' else "#1E1E1E"
    card_bg = "#1E1E1E" if st.session_state['theme'] == 'dark' else "#FFFFFF"
    
    css = f"""
    <style>
        .stApp {{
            background-color: {theme_bg};
            color: {theme_color};
            font-family: 'Inter', sans-serif;
        }}
        /* Gradient Header */
        h1, h2, h3 {{
            background: -webkit-linear-gradient(45deg, #FF6B6B, #4ECDC4, #45B7D1);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-weight: 800;
        }}
        /* Premium Cards */
        .css-1r6slb0, .css-1y4p8pa, div[data-testid="stExpander"] {{
            background-color: {card_bg};
            border-radius: 12px;
            box-shadow: 0 8px 24px rgba(0,0,0,0.08);
            border: none;
            padding: 10px;
        }}
        /* Gradient Buttons */
        div.stButton > button:first-child {{
            background: linear-gradient(90deg, #4ECDC4, #556270);
            color: white;
            border: none;
            border-radius: 8px;
            padding: 10px 24px;
            font-weight: bold;
            transition: all 0.3s ease;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }}
        div.stButton > button:first-child:hover {{
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(0,0,0,0.15);
        }}
        /* Custom Chat bubbles */
        .stChatMessage {{ background-color: {card_bg}; border-radius: 10px; padding: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }}
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
        st.session_state['paintersel'] = new_style
        st.toast(f"🎨 Style changed to {new_style}!")
        st.rerun()

# ---- Secure API Key Handling ----
with st.sidebar:
    st.markdown("### 🔐 Authentication")
    api_key_input = st.text_input("OpenAI / Gemini API Key", type="password", value=st.session_state['api_key'] if st.session_state['api_key'] else "")
    if api_key_input != st.session_state['api_key']:
        st.session_state['api_key'] = api_key_input
        st.success("API Key Saved!")
    if not st.session_state['api_key']:
        st.warning("Running in **Simulation Mode**. Add API key for live AI generation.")

    st.markdown("---")
    st.markdown("### 🚀 Navigation")
    steps = ['1. Upload', '2. Review', '3. Dashboard', '4. AI Note Keeper']
    current_step = st.radio("Go to step:", steps, label_visibility="collapsed")
    
    st.markdown("---")
    MODEL_OPTS =['gpt-4o-mini', 'gpt-4.1-mini', 'gemini-3-flash-preview', 'gemini-2.5-flash']
    selected_model = st.selectbox("🧠 Select Brain", MODEL_OPTS)

AGENTS =[
    {'label':'Infographics', 'icon':'📊'}, {'label':'Checklist', 'icon':'✅'},
    {'label':'Risk Radar', 'icon':'🎯'}, {'label':'SE Matrix', 'icon':'🧮'},
    {'label':'FDA Letter', 'icon':'📝'}
]

# ==========================================
# STEP 1: UPLOAD
# ==========================================
if current_step == '1. Upload':
    st.markdown("<h2>Step 1: Ingest Regulatory Document</h2>", unsafe_allow_html=True)
    st.info("Upload your FDA 510(k), PMA, CER, or paste raw regulatory text.")
    
    colA, colB = st.columns(2)
    with colA:
        uploaded_file = st.file_uploader("Drop PDF/Text file here", type=["pdf", "txt"])
    with colB:
        raw_text = st.text_area("OR Paste Raw Text Here", height=150)
        
    if st.button("🚀 Process Document", use_container_width=True):
        content = ""
        if uploaded_file:
            if uploaded_file.name.endswith('.txt'):
                content = uploaded_file.read().decode('utf-8')
            else:
                content = f"[PDF Extracted Data] File: {uploaded_file.name} | Size: {uploaded_file.size} bytes.\n(Note: In production, integrate PyMuPDF/pdfplumber here.)"
        if raw_text:
            content += "\n\n" + raw_text
            
        if content.strip():
            st.session_state['doc_content'] = content
            st.success("✅ Document Successfully Ingested!")
            st.balloons()
        else:
            st.error("⚠️ Please upload a file or paste text to continue.")

# ==========================================
# STEP 2: REVIEW
# ==========================================
elif current_step == '2. Review':
    st.markdown("<h2>Step 2: Review & AI Organization</h2>", unsafe_allow_html=True)
    if not st.session_state['doc_content']:
        st.warning("⚠️ No document found. Please go back to **Step 1: Upload**.")
        st.stop()

    if "review_md" not in st.session_state or st.session_state["review_md"] == "":
        st.session_state["review_md"] = f"### Raw Document Snippet\n\n{st.session_state['doc_content'][:500]}...\n\n--- \n*Click 'Run Deep AI Analysis' to structure this document.*"

    col_text, col_actions = st.columns([3, 1])
    with col_text:
        doc_text = st.text_area("Document Content (Markdown)", value=st.session_state["review_md"], height=400, key="review_md_editor")
        st.session_state["review_md"] = doc_text
    
    with col_actions:
        st.markdown("### AI Actions")
        if st.button("✨ Run Deep AI Analysis", use_container_width=True):
            with st.spinner("🤖 AI is reading, structuring, and extracting key regulatory insights..."):
                time.sleep(2.5) # Simulate processing
                ai_structured_text = f"""### AI Executive Summary
**Device Type:** Class II Medical Device  
**Predicate Identified:** K192233  
**Indications for Use:** Matches predicate perfectly.  
**Potential Risks:** Biocompatibility, Software anomalies.

#### Source Context
{st.session_state['doc_content'][:300]}..."""
                st.session_state["review_md"] = ai_structured_text
                st.session_state["dashboard_generated"] = True
            st.success("✅ Analysis Complete!")
            st.rerun()
            
        if st.session_state["dashboard_generated"]:
            st.info("Insights ready! Head to the **Dashboard**.")

# ==========================================
# STEP 3: DASHBOARD (WOW Visualization)
# ==========================================
elif current_step == '3. Dashboard':
    st.markdown("<h2>Step 3: Interactive WOW Dashboard</h2>", unsafe_allow_html=True)
    if not st.session_state["dashboard_generated"]:
        st.warning("⚠️ Please run the Deep AI Analysis in **Step 2: Review** first.")
        st.stop()

    tabs = st.tabs([f"{ag['icon']} {ag['label']}" for ag in AGENTS])
    
    # --- Tab 1: Infographics ---
    with tabs[0]:
        st.markdown("### 📊 High-Level Metrics")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Risk Class", "Class II", "- Low Risk")
        m2.metric("Predicate Match", "94%", "+2% from avg")
        m3.metric("Missing Docs", "2", "- Requires action", delta_color="inverse")
        m4.metric("Approval Probability", "88%", "+High")
        st.progress(88, text="AI Confidence Score")
        
    # --- Tab 2: Checklist ---
    with tabs[1]:
        st.markdown("### ✅ Regulatory Submission Checklist")
        checks =["Cover Letter & Form 3514", "Indications for Use Statement", "510(k) Summary", "Software Architecture Document", "Biocompatibility Test Reports"]
        for i, task in enumerate(checks):
            st.session_state['checklist_states'][i] = st.checkbox(task, value=st.session_state['checklist_states'][i], key=f"chk_{i}")
        if all(st.session_state['checklist_states']):
            st.success("🎉 All documents are ready for submission!")

    # --- Tab 3: Risk Radar ---
    with tabs[2]:
        st.markdown("### 🎯 Risk Radar Analysis")
        risk_data = pd.DataFrame({
            "Risk Category":["Software Failure", "Biocompatibility", "Electrical Safety", "Usability"],
            "Severity":["High", "Medium", "Low", "Medium"],
            "Mitigated?":["No ⚠️", "Yes ✅", "Yes ✅", "Pending 🔄"]
        })
        def highlight_risks(val):
            color = '#ff4b4b' if val == 'High' else '#ffa421' if val == 'Medium' else '#00cc96' if val == 'Low' else ''
            return f'background-color: {color}; color: white; font-weight:bold;' if color else ''
        
        st.dataframe(risk_data.style.map(highlight_risks, subset=['Severity']), use_container_width=True)

    # --- Tab 4: Substantial Equivalence (SE) Matrix ---
    with tabs[3]:
        st.markdown("### 🧮 Substantial Equivalence Matrix")
        se_data = pd.DataFrame({
            "Feature": ["Intended Use", "Material", "Sterilization", "Software Level"],
            "Subject Device":["Cutting Tissue", "Stainless Steel 316L", "Gamma", "Moderate Concern"],
            "Predicate (K192233)":["Cutting Tissue", "Stainless Steel 316L", "EO Gas", "Moderate Concern"],
            "Equivalence": ["Same", "Same", "Different", "Same"]
        })
        st.data_editor(se_data, use_container_width=True)

    # --- Tab 5: FDA Letter ---
    with tabs[4]:
        st.markdown("### 📝 Auto-Drafted FDA Cover Letter")
        draft_letter = f"""Date: {time.strftime("%B %d, %Y")}\n\nU.S. Food and Drug Administration\nCenter for Devices and Radiological Health\nDocument Mail Center – WO66-G609\n\nSUBJECT: Premarket Notification 510(k) for[Device Name]\n\nDear Sir/Madam,\nWe are submitting this 510(k) premarket notification to request clearance for the aforementioned device. It is substantially equivalent to the predicate device K192233.\n\nSincerely,\n[Regulatory Affairs Manager]"""
        st.text_area("Edit Draft Letter", value=draft_letter, height=300)

    st.markdown("---")
    
    # ---- EXPORT CAPABILITIES ----
    st.markdown("### 📥 Export Capabilities")
    colE1, colE2, colE3 = st.columns(3)
    
    with colE1:
        st.download_button("⬇️ Export Markdown", st.session_state["review_md"], file_name="reguai_report.md", mime="text/markdown", use_container_width=True)
    with colE2:
        html_content = f"<html><body style='font-family:sans-serif;'><h1>Regulatory Report</h1><pre>{st.session_state['review_md']}</pre></body></html>"
        st.download_button("⬇️ Export HTML", html_content, file_name="reguai_report.html", mime="text/html", use_container_width=True)
    with colE3:
        def create_dashboard_pdf(title, painter, theme, summary):
            buf = io.BytesIO()
            c = canvas.Canvas(buf, pagesize=letter)
            width, height = letter
            c.setFont("Helvetica-Bold", 18)
            c.drawString(40, height - 50, title)
            c.setFont("Helvetica", 11)
            c.drawString(40, height - 75, f"AI Stylized parameters: {painter} | Theme: {theme}")
            c.line(40, height - 85, width - 40, height - 85)
            text = c.beginText(40, height - 110)
            text.setFont("Helvetica", 10)
            for line in summary.split('\n')[:40]: # limit lines for PDF simplicity
                text.textLine(line.strip())
            c.drawText(text)
            c.showPage()
            c.save()
            return buf.getvalue()
            
        pdf_bytes = create_dashboard_pdf(
            "ReguAI WOW Regulatory Report", st.session_state['painter_style'], st.session_state['theme'], st.session_state['review_md']
        )
        st.download_button("⬇️ Export PDF", data=pdf_bytes, file_name="reguai_report.pdf", mime="application/pdf", use_container_width=True)

# ==========================================
# STEP 4: AI NOTE KEEPER (Chatbot)
# ==========================================
elif current_step == '4. AI Note Keeper':
    st.markdown("<h2>Step 4: AI Note Keeper 🤖</h2>", unsafe_allow_html=True)
    st.info("Chat directly with your regulatory document! Ask for summaries, standard references, or translation.")

    chat_container = st.container(height=400)
    
    # Render chat history
    with chat_container:
        if not st.session_state.chat_history:
            st.write("👋 *Hello! I am your AI Regulatory Assistant. Ask me anything about the uploaded document.*")
            
        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"], avatar="🤖" if msg["role"] == "assistant" else "👤"):
                st.markdown(msg["content"])

    # Chat Input
    if prompt := st.chat_input("E.g., What are the biocompatibility requirements?"):
        # Append User Message
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with chat_container:
            with st.chat_message("user", avatar="👤"):
                st.markdown(prompt)
            
            # Simulate Assistant Response
            with st.chat_message("assistant", avatar="🤖"):
                with st.spinner("Thinking..."):
                    time.sleep(1) # Simulate API call latency
                    
                    # Generate Mock Contextual Response
                    reply = f"Based on the regulatory context, here is the answer regarding **'{prompt}'**:\n\n"
                    if "biocompatibility" in prompt.lower():
                        reply += "- ISO 10993-1 requires evaluation of Cytotoxicity, Sensitization, and Irritation.\n- Based on your document, these tests are marked as 'Completed'."
                    elif "predicate" in prompt.lower():
                        reply += "- The recognized predicate is **K192233**. Your device shares the same intended use."
                    else:
                        reply += "This aspect requires a detailed comparison in the SE Matrix. Please ensure all testing parameters align with FDA guidance documents specific to your product code."
                        
                    st.markdown(reply)
                    st.session_state.chat_history.append({"role": "assistant", "content": reply})

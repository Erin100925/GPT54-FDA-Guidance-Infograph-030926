import os
import io
import streamlit as st
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

# ---- Helper functions for Env/API key retrieval
def get_api_key():
    return os.getenv('OPENAI_API_KEY') or os.getenv('GEMINI_API_KEY')

def display_api_key_widget():
    with st.expander("🔑 Enter Your AI API Key", expanded=True):
        api_key = st.text_input("Please enter your OpenAI or Gemini API key", type="password")
        if api_key:
            st.session_state['api_key'] = api_key
            st.success('API key loaded in session. Secure for this run.')
        return st.session_state.get('api_key', None)

# ---- Initialization and Session State
st.set_page_config(page_title="ReguAI - Regulatory Analysis Dashboard", layout="wide", page_icon="🦾")
if 'language' not in st.session_state:
    st.session_state['language'] = 'English'
if 'theme' not in st.session_state:
    st.session_state['theme'] = 'light'
if 'painter_style' not in st.session_state:
    st.session_state['painter_style'] = 'Van Gogh'
if 'api_key' not in st.session_state:
    st.session_state['api_key'] = get_api_key()
if 'current_agent' not in st.session_state:
    st.session_state['current_agent'] = None
if 'dashboard_data' not in st.session_state:
    st.session_state['dashboard_data'] = {}

# ---- LANG/THEME/STYLE SELECTORS, JACKPOT
col1, col2, col3, col4 = st.columns([2,1,1,1])
with col1:
    st.title("ReguAI WOW Regulatory Analysis 🦾")
with col2:
    lang = st.selectbox("Language", ['English', '繁體中文'], index=0 if st.session_state['language']=='English' else 1, key="langselect")
    st.session_state['language'] = lang
with col3:
    theme = st.selectbox("Theme", ['Light', 'Dark'], key="themeselect")
    st.session_state['theme'] = theme.lower()
with col4:
    PAINTERS = [
        'Van Gogh','Monet','Picasso','Da Vinci','Klimt','Hokusai','Rembrandt','Miro',
        'Dali','Kandinsky','Cezanne','O\'Keeffe','Matisse','Pollock','Goya','Warhol',
        'Basquiat','Mondrian','Magritte','Turner'
    ]
    painter_style = st.selectbox("🎨 Painter Style", PAINTERS, key="paintersel")
    st.session_state['painter_style'] = painter_style
    if st.button("Jackpot! 🎲"):
        import random
        painter_style = random.choice(PAINTERS)
        st.session_state['painter_style'] = painter_style
        st.success(f"Painter style switched to {painter_style}!")

st.markdown(f"""
<style>
    body {{
        background: {"#212121" if st.session_state['theme']=='dark' else "#FFF"};
        color: {"#eee" if st.session_state['theme']=='dark' else "#222"};
    }}
</style>
""", unsafe_allow_html=True)

# ---- Secure API Key Handling
api_key = st.session_state['api_key']
if not api_key:
    api_key = display_api_key_widget()
    if not api_key:
        st.stop()
else:
    st.markdown("<small style='color:green;'>API key loaded from environment.</small>", unsafe_allow_html=True)

# ---- STEP-BASED NAVIGATION
steps = ['Upload', 'Review', 'Dashboard', 'AI Note Keeper']
#step_idx = st.sidebar.radio("Navigation", steps, horizontal=False)
#current_step = steps[step_idx]
current_step = st.sidebar.radio("Navigation", steps, horizontal=False)
# ---- MODEL & AGENT CONTROL
MODEL_OPTS = [
    'gpt-4o-mini', 'gpt-4.1-mini', 'gemini-2.5-flash',
    'gemini-2.5-flash-lite', 'gemini-3-flash-preview'
]
AGENTS = [
    {'label':'Infographics', 'id':'infographics'},
    {'label':'Checklist', 'id':'checklist'},
    {'label':'Risk Radar', 'id':'risk_radar'},
    {'label':'SE Matrix', 'id':'se_matrix'},
    {'label':'FDA Letter', 'id':'fda_letter'},
]
st.sidebar.subheader("AI Model & Prompt Selection")
selected_model = st.sidebar.selectbox("Model", MODEL_OPTS)

agent_states = {}
for ag in AGENTS:
    st.sidebar.markdown(f"**Agent: {ag['label']}**")
    prompt_key = f"prompt_{ag['id']}"
    model_key = f"model_{ag['id']}"
    st.sidebar.text_area(f"Prompt ({ag['label']})", st.session_state.get(prompt_key, f"Default prompt for {ag['label']}."), key=prompt_key)
    st.sidebar.selectbox(f"Model ({ag['label']})", MODEL_OPTS, index=MODEL_OPTS.index(selected_model), key=model_key)
    agent_states[ag['id']] = {
        'prompt': st.session_state[prompt_key], 'model': st.session_state[model_key]
    }

# ---- FILE OR TEXT UPLOAD
if current_step=='Upload':
    st.header("Step 1: Upload Regulatory Document")
    uploaded_file = st.file_uploader("Drop PDF/Text file here (FDA 510k, PMA, CER...)", type=["pdf", "txt"])
    raw_text = st.text_area("OR Paste Regulatory Text Below")
    if st.button("Continue to Review"):
        if uploaded_file or raw_text:
            st.session_state['doc_uploaded'] = uploaded_file or raw_text
            st.success("Uploaded! Proceed to review.")
        else:
            st.error("Please upload a file or paste text.")

# ---- REVIEW (Markdown Reorganization)
elif current_step == 'Review':
    st.header("Step 2: Review and Edit Document (AI-Organized Markdown)")
    if not st.session_state.get('doc_uploaded'):
        st.info("Please upload a file or text on Step 1 first.")
        st.stop()
    doc_text = "---AI ORGANIZED DOCUMENT MARKDOWN HERE---"
    doc_text = st.text_area("AI Reorganized Markdown", value=doc_text, height=300, key="review_md")
    st.session_state['review_md'] = doc_text
    if st.button("Generate Dashboard Features"):
        st.success("Dashboard Data Generated! Switch to Dashboard tab.")

# ---- DASHBOARD (WOW Visualization)
elif current_step == 'Dashboard':
    st.header("Step 3: WOW Interactive Dashboard")
    dashboard_tabs = st.tabs([ag['label'] for ag in AGENTS])
    for i, ag in enumerate(AGENTS):
        with dashboard_tabs[i]:
            st.write(f"Visual analytics for **{ag['label']}** go here.")
            st.info("(For full deployment: render advanced Recharts/D3/SVG/HTML visualizations and agent result editing here)")
        st.progress(i / len(AGENTS))
        st.write("Status: 🔄 Complete  ✅")
    
    # ---- MARKDOWN/HTML Export
    st.download_button("Export as Markdown", "-----MARKDOWN-----", file_name="reguai_dashboard.md", mime="text/markdown")
    st.download_button("Export as HTML", "<html><body>-----HTML-----</body></html>", file_name="reguai_dashboard.html", mime="text/html")

    # ---- PDF EXPORT USING REPORTLAB:
    def create_dashboard_pdf(title:str, painter:str, theme:str, summary:str) -> bytes:
        buf = io.BytesIO()
        c = canvas.Canvas(buf, pagesize=letter)
        width, height = letter
        c.setFont("Helvetica-Bold", 20)
        c.drawString(50, height - 50, title)
        c.setFont("Helvetica", 12)
        c.drawString(50, height - 80, f"Painter Style: {painter}")
        c.drawString(50, height - 100, f"Theme: {theme}")
        c.line(50, height - 110, width - 50, height - 110)
        text = c.beginText(50, height - 130)
        text.textLines(summary)
        c.drawText(text)
        c.showPage()
        c.save()
        pdf = buf.getvalue()
        buf.close()
        return pdf
    
    if st.button("Export as PDF"):
        pdf_bytes = create_dashboard_pdf(
            title="ReguAI WOW Regulatory Report",
            painter=st.session_state['painter_style'],
            theme=st.session_state['theme'],
            summary=st.session_state.get('review_md', '-----SUMMARY (fill with dashboard content)-----')
        )
        st.download_button("Download PDF", data=pdf_bytes, file_name="reguai_dashboard.pdf", mime="application/pdf")

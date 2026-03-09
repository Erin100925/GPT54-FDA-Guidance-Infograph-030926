import streamlit as st
import yaml
from PyPDF2 import PdfReader, PdfWriter
from PIL import Image
import pytesseract
import io
import google.generativeai as genai
import openai
import os
from dotenv import load_dotenv
import traceback
from wordcloud import WordCloud
import matplotlib.pyplot as plt

# --- Page Configuration ---
st.set_page_config(
    page_title="Agentic PDF Processing System",
    page_icon="✨",
    layout="wide",
)

# Load environment variables for local development
load_dotenv()

# --- Embedded CSS ---
CSS_STYLE = """
/* Base Styles */
body {
    transition: background-color 0.3s, color 0.3s;
}
.stTabs [data-baseweb="tab-list"] {
	gap: 24px;
}
.stTabs [data-baseweb="tab"] {
	height: 50px;
    white-space: pre-wrap;
	background-color: transparent;
	border-radius: 4px 4px 0px 0px;
	gap: 1px;
	padding-top: 10px;
	padding-bottom: 10px;
}
.stTabs [aria-selected="true"] {
  	background-color: #2F4F4F;
}
.card {
    border: 1px solid #2F4F4F;
    border-radius: 10px;
    padding: 20px;
    margin: 10px 0;
    background-color: #1a1a1a;
    box-shadow: 0 4px 8px 0 rgba(0,0,0,0.2);
    transition: 0.3s;
}
.card:hover {
    box-shadow: 0 8px 16px 0 rgba(0,0,0,0.2);
}
.metric-label {
    font-size: 1.1em;
    color: #a0a0a0;
}
.metric-value {
    font-size: 2.5em;
    font-weight: bold;
    color: #f0f0f0;
}
/* Theme-specific overrides */
.theme-neat-dark { background-color: #1a1a1a; color: #f0f0f0; }
.theme-simple-white { background-color: #ffffff; color: #333333; }
.theme-alp-forest { background-color: #2f4f4f; color: #f5f5f5; }
.theme-blue-sky { background-color: #87ceeb; color: #00008b; }
.theme-deep-ocean { background-color: #000080; color: #add8e6; }
.theme-magic-purple { background-color: #4b0082; color: #e6e6fa; }
.theme-beethoven { background-color: #363636; color: #dcdcdc; }
.theme-mozart { background-color: #fffafa; color: #2f4f4f; }
.theme-jsbach { background-color: #d2b48c; color: #556b2f; }
.theme-chopin { background-color: #f0e68c; color: #8b4513; }
.theme-ferrari-sportscar { background-color: #ff2800; color: #ffffff; }
.theme-nba { background-color: #1d428a; color: #c8102e; }
.theme-mlb { background-color: #002d72; color: #d50032; }
.theme-nfl { background-color: #013369; color: #d50a0a; }
"""

# --- Model Definitions ---
MODEL_OPTIONS = {
    "Gemini": ["gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-2.0-flash", "gemini-2.0-flash-lite"],
    "OpenAI": ["gpt-5-nano", "gpt-4o-mini"],
    "Grok": ["grok-4-fast-reasoning", "grok-3-mini"]
}

# --- Function Definitions ---
# (trim_pdf, ocr_pdf, extract_text_from_pdf, to_markdown_with_keywords, load_agents_config, get_llm_client, execute_agent remain the same)
def trim_pdf(file_bytes, pages_to_trim):
    try:
        reader = PdfReader(io.BytesIO(file_bytes))
        writer = PdfWriter()
        start_page, end_page = pages_to_trim
        if start_page > end_page or start_page < 1 or end_page > len(reader.pages):
            st.error("Invalid page range selected.")
            return None, 0
        for i in range(start_page - 1, end_page):
            writer.add_page(reader.pages[i])
        output_pdf = io.BytesIO()
        writer.write(output_pdf)
        num_pages_processed = end_page - start_page + 1
        return output_pdf.getvalue(), num_pages_processed
    except Exception as e:
        st.error(f"Error trimming PDF: {e}")
        return None, 0

def ocr_pdf(file_bytes):
    try:
        from pdf2image import convert_from_bytes
        images = convert_from_bytes(file_bytes)
        full_text = ""
        for i, image in enumerate(images):
            text = pytesseract.image_to_string(image)
            full_text += f"\n--- Page {i+1} ---\n{text}"
        return full_text
    except ImportError:
        st.error("The 'pdf2image' library is not installed. This is required for OCR.")
        return None
    except Exception as e:
        st.warning(f"Could not perform OCR. Ensure 'poppler' and 'tesseract' are installed. Error: {e}")
        return None

def extract_text_from_pdf(file_bytes):
    try:
        reader = PdfReader(io.BytesIO(file_bytes))
        text = ""
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
        return text
    except Exception as e:
        st.error(f"Error extracting text from PDF: {e}")
        return ""

def to_markdown_with_keywords(text, keywords):
    if keywords:
        keyword_list = [kw.strip() for kw in keywords.split(',') if kw.strip()]
        for keyword in keyword_list:
            text = text.replace(keyword, f"<span style='color:coral;'>{keyword}</span>")
    return text

@st.cache_data
def load_agents_config():
    try:
        with open("agents.yaml", 'r') as file:
            return yaml.safe_load(file)
    except FileNotFoundError:
        st.error("agents.yaml not found. Please create it.")
        return {}

def get_llm_client(api_choice):
    try:
        if api_choice == "Gemini":
            api_key = st.secrets.get("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY")
            if not api_key:
                st.error("Google Gemini API key is not set.")
                return None
            genai.configure(api_key=api_key)
            return genai
        elif api_choice == "OpenAI":
            api_key = st.secrets.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
            if not api_key:
                st.error("OpenAI API key is not set.")
                return None
            return openai.OpenAI(api_key=api_key)
        elif api_choice == "Grok":
            try:
                from xai_sdk import Client as GrokClient
            except ImportError:
                st.error("The 'xai-sdk' is required for Grok.")
                return None
            api_key = st.secrets.get("GROK_API_KEY") or os.getenv("GROK_API_KEY")
            if not api_key:
                st.error("GROK_API_KEY (for Grok) is not set.")
                return None
            return GrokClient(api_key=api_key, timeout=3600)
    except Exception as e:
        st.error(f"Error initializing {api_choice} client: {e}")
        return None
    return None

def execute_agent(agent_config, input_text):
    client = get_llm_client(agent_config['api'])
    if not client:
        return f"Could not initialize the {agent_config['api']} client. Check API keys."
    prompt = agent_config['prompt'].format(input_text=input_text)
    model = agent_config['model']
    try:
        if agent_config['api'] == "Gemini":
            model_instance = client.GenerativeModel(model)
            response = model_instance.generate_content(prompt)
            return response.text
        elif agent_config['api'] == "OpenAI":
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                **agent_config.get('parameters', {})
            )
            return response.choices[0].message.content
        elif agent_config['api'] == "Grok":
            try:
                from xai_sdk.chat import user
            except ImportError:
                return "Could not import from 'xai_sdk.chat'."
            chat = client.chat.create(model=model)
            chat.append(user(prompt))
            response = chat.sample()
            return response.content
    except Exception as e:
        st.error(f"An error occurred executing agent '{agent_config['name']}': {e}")
        traceback.print_exc()
        return None

# --- Main Application ---
def main():
    st.markdown(f'<style>{CSS_STYLE}</style>', unsafe_allow_html=True)
    st.title("✨ Agentic PDF Intelligence System")

    # --- Initialize Session State ---
    if 'processed_texts' not in st.session_state:
        st.session_state.processed_texts = {}
    if 'agent_configs' not in st.session_state:
        st.session_state.agent_configs = {}
    if 'agent_outputs' not in st.session_state:
        st.session_state.agent_outputs = []
    if 'total_pages_processed' not in st.session_state:
        st.session_state.total_pages_processed = 0

    # --- Sidebar for Theme Selection ---
    with st.sidebar:
        st.header("🎨 Theme Selector")
        themes = ["Neat dark", "Simple white", "Alp. forest", "Blue sky", "Deep ocean", "Magic purple", "Beethoven", "Mozart", "J.S.Bach", "Chopin", "Ferrari Sportscar", "NBA", "MLB", "NFL"]
        selected_theme = st.selectbox("Choose a UI theme", themes)
        theme_class = selected_theme.lower().replace(" ", "-").replace(".", "")
        st.markdown(f'<body class="{theme_class}"></body>', unsafe_allow_html=True)

    # --- Main Interface with Tabs ---
    tab1, tab2, tab3 = st.tabs(["**① File Processing**", "**② Agent Workflow**", "**③ Results Dashboard**"])

    with tab1:
        st.header("Upload and Pre-process Your Documents")
        uploaded_files = st.file_uploader("📂 Select PDF files to analyze", type="pdf", accept_multiple_files=True)

        if uploaded_files:
            for uploaded_file in uploaded_files:
                with st.expander(f"Configure '{uploaded_file.name}'"):
                    file_bytes = uploaded_file.getvalue()
                    try:
                        reader = PdfReader(io.BytesIO(file_bytes))
                        total_pages = len(reader.pages)
                        pages_to_trim = st.slider(f"Pages to process for '{uploaded_file.name}'", 1, total_pages, (1, total_pages), key=f"trim_{uploaded_file.name}")
                    except Exception:
                        st.error(f"Could not read '{uploaded_file.name}'. The file may be corrupted.")
                        continue
                    keywords = st.text_input(f"Keywords to highlight (comma-separated)", key=f"kw_{uploaded_file.name}")

                    if st.button(f"Process '{uploaded_file.name}'", key=f"proc_{uploaded_file.name}"):
                        with st.status(f"Processing {uploaded_file.name}...", expanded=True) as status:
                            st.write("Trimming PDF to selected pages...")
                            trimmed_pdf_bytes, pages_processed = trim_pdf(file_bytes, pages_to_trim)
                            st.session_state.total_pages_processed += pages_processed
                            
                            if trimmed_pdf_bytes:
                                st.write("Extracting text...")
                                text = extract_text_from_pdf(trimmed_pdf_bytes)
                                if len(text.strip()) < 100 * pages_processed:
                                    st.write("Low text content found, attempting OCR...")
                                    ocr_text = ocr_pdf(trimmed_pdf_bytes)
                                    if ocr_text: text = ocr_text
                                
                                st.write("Highlighting keywords and finalizing...")
                                markdown_text = to_markdown_with_keywords(text, keywords)
                                st.session_state.processed_texts[uploaded_file.name] = markdown_text
                                status.update(label="Processing Complete!", state="complete", expanded=False)
                                st.success(f"'{uploaded_file.name}' processed successfully!")
                            else:
                                status.update(label="Processing Failed!", state="error")
                
                if uploaded_file.name in st.session_state.processed_texts:
                    st.markdown(f"#### Processed & Editable Text from '{uploaded_file.name}'")
                    edited_text = st.text_area(f"Edit Markdown", st.session_state.processed_texts[uploaded_file.name], height=300, key=f"edit_{uploaded_file.name}")
                    st.session_state.processed_texts[uploaded_file.name] = edited_text

    with tab2:
        st.header("Construct Your Agentic Workflow")
        if not st.session_state.processed_texts:
            st.info("Please upload and process at least one PDF in the 'File Processing' tab first.")
        else:
            initial_input_text = "\n\n---\n\n".join(st.session_state.processed_texts.values())
            agents_config_yaml = load_agents_config()
            if not agents_config_yaml or 'agents' not in agents_config_yaml:
                st.error("Agent configuration (agents.yaml) is missing or invalid.")
                return
            
            num_agents = st.slider("Select the number of agents to use in the sequence", 1, len(agents_config_yaml.get('agents', [])), 1)
            
            # --- Workflow Visualization ---
            st.subheader("Workflow Diagram")
            cols = st.columns(num_agents + 2)
            cols[0].write("📄\n\n**Input**")
            for i in range(num_agents):
                cols[i+1].write("➡️")
                agent_name = st.session_state.get(f'agent_{i}_config', {'name': 'Agent'})['name']
                cols[i+1].write(f"🤖\n\n**{agent_name}**")
            cols[num_agents+1].write("➡️")
            cols[num_agents+1].write("📊\n\n**Output**")
            st.divider()

            # --- Agent Configuration ---
            if len(st.session_state.agent_outputs) != num_agents:
                st.session_state.agent_outputs = [None] * num_agents
            
            next_input = initial_input_text
            for i in range(num_agents):
                st.subheader(f"Configure Agent {i+1}")
                # ... (Agent configuration logic remains the same)
                if i > 0 and st.session_state.agent_outputs[i-1]:
                    st.markdown(f"**Input for Agent {i+1} (Editable Output from Agent {i})**")
                    edited_input = st.text_area(f"Edit input for Agent {i+1}", st.session_state.agent_outputs[i-1], height=200, key=f"input_edit_{i}")
                    next_input = edited_input
                elif i == 0:
                    next_input = initial_input_text

                agent_options = [agent['name'] for agent in agents_config_yaml['agents']]
                selected_agent_name = st.selectbox(f"Select Agent {i+1}", agent_options, key=f"agent_select_{i}")
                
                if f'agent_{i}_config' not in st.session_state or st.session_state[f'agent_{i}_config']['name'] != selected_agent_name:
                    default_config = next((agent for agent in agents_config_yaml['agents'] if agent['name'] == selected_agent_name), None)
                    st.session_state[f'agent_{i}_config'] = default_config.copy()

                current_config = st.session_state[f'agent_{i}_config']
                
                with st.container(border=True):
                    current_config['prompt'] = st.text_area(f"Prompt", current_config['prompt'], height=150, key=f"prompt_{i}")
                    col1, col2 = st.columns(2)
                    with col1:
                        api_choice = st.selectbox("API", list(MODEL_OPTIONS.keys()), key=f"api_{i}", index=list(MODEL_OPTIONS.keys()).index(current_config['api']))
                        current_config['api'] = api_choice
                    with col2:
                        if current_config['model'] not in MODEL_OPTIONS[api_choice]:
                            st.warning(f"Model '{current_config['model']}' not in predefined list for {api_choice}. Defaulting to first option.")
                            current_config['model'] = MODEL_OPTIONS[api_choice][0]
                        model_choice_index = MODEL_OPTIONS[api_choice].index(current_config['model'])
                        model_choice = st.selectbox("Model", MODEL_OPTIONS[api_choice], key=f"model_{i}", index=model_choice_index)
                        current_config['model'] = model_choice
                
                if st.button(f"▶️ Execute Agent {i+1}", key=f"exec_{i}", type="primary"):
                    with st.spinner(f"Agent {i+1} ({current_config['name']}) is processing..."):
                        output = execute_agent(current_config, next_input)
                        st.session_state.agent_outputs[i] = output if output is not None else "Execution failed."
                        st.rerun() # Rerun to update UI and show output
                
                if st.session_state.agent_outputs[i]:
                    st.success(f"Agent {i+1} executed successfully.")
                    st.text_area("Result", st.session_state.agent_outputs[i], height=300, key=f"output_display_{i}", disabled=True)

    with tab3:
        st.header("Results and Analysis Dashboard")
        final_output = st.session_state.agent_outputs[-1] if any(st.session_state.agent_outputs) else None
        
        if not final_output:
            st.info("Run an agent workflow to see the results dashboard here.")
        else:
            # --- Metrics ---
            st.subheader("Execution Summary")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown(f'<div class="card"><div class="metric-label">Documents Processed</div><div class="metric-value">{len(st.session_state.processed_texts)}</div></div>', unsafe_allow_html=True)
            with col2:
                st.markdown(f'<div class="card"><div class="metric-label">Total Pages Processed</div><div class="metric-value">{st.session_state.total_pages_processed}</div></div>', unsafe_allow_html=True)
            with col3:
                st.markdown(f'<div class="card"><div class="metric-label">Final Word Count</div><div class="metric-value">{len(final_output.split())}</div></div>', unsafe_allow_html=True)

            # --- Visualizations ---
            st.subheader("Content Analysis")
            vis1, vis2 = st.columns(2)
            with vis1:
                st.markdown("#### Key Terms Word Cloud")
                try:
                    wordcloud = WordCloud(width=800, height=400, background_color='white').generate(final_output)
                    fig, ax = plt.subplots()
                    ax.imshow(wordcloud, interpolation='bilinear')
                    ax.axis("off")
                    st.pyplot(fig)
                except Exception as e:
                    st.warning(f"Could not generate word cloud: {e}")
            
            with vis2:
                st.markdown("#### Content Transformation")
                # Prepare data for the chart
                chart_data = {'Agent': [], 'Character Count': []}
                # Initial text
                chart_data['Agent'].append('Initial Text')
                chart_data['Character Count'].append(len(initial_input_text))
                # Agent outputs
                for i, output in enumerate(st.session_state.agent_outputs):
                    if output:
                        agent_name = st.session_state.get(f'agent_{i}_config', {'name': f'Agent {i+1}'})['name']
                        chart_data['Agent'].append(agent_name)
                        chart_data['Character Count'].append(len(output))
                
                st.bar_chart(chart_data, x='Agent', y='Character Count')

            st.divider()
            st.subheader("Final Output")
            st.text_area("Final result from the last agent in the workflow", final_output, height=500)

if __name__ == "__main__":
    main()
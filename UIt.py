import requests
import streamlit as st
import asyncio
import nest_asyncio
from autogen_agentchat.base import TaskResult
from autogen_agentchat.messages import TextMessage
from agents import build_team  # ensure this returns a fresh instance
import time

nest_asyncio.apply()
st.set_page_config(page_title="🧠 Advantech Ticket Analyzer", layout="centered")

# ---------- Custom CSS ----------
st.markdown("""
<style>
    html, body, .main {
        background-color: white !important;
    }
    .agent-step {
        background-color: #f5faff;
        padding: 1em;
        border-left: 4px solid #4b8bbe;
        margin: 1em 0;
        border-radius: 8px;
        color: black;
        font-family: 'Segoe UI', sans-serif;
        box-shadow: 0 2px 6px rgba(0,0,0,0.05);
    }
    .sticky-header {
    position: sticky;
    top: 0;
    background-color: white;  /* match page background */
    z-index: 1000;            /* stay on top */
    padding-top: 0.5rem;
    padding-bottom: 0.5rem;
    box-shadow: 0 2px 5px rgba(0,0,0,0.1); /* subtle shadow to separate */
    }
    .final-answer {
        background-color: #e6fff0;
        padding: 1em;
        border-left: 5px solid #28a745;
        border-radius: 8px;
        margin-top: 1.5em;
        color: black;
    }

    .thinking {
        font-style: italic;
        color: gray;
        animation: pulse 1s infinite;
    }

    @keyframes pulse {
        0% { opacity: 0.4; }
        50% { opacity: 1; }
        100% { opacity: 0.4; }
    }

    .arrow {
        font-size: 1.4em;
        color: #4b8bbe;
        margin: 0.5em 0;
    }

    .footer-step {
        background-color: #fdf5e6;
        padding: 1.2em;
        border-left: 5px solid #ffc107;
        border-radius: 8px;
        margin-top: 2em;
        font-weight: bold;
        color: #333;
        font-family: 'Segoe UI', sans-serif;
    }
</style>
""", unsafe_allow_html=True)

# ---------- Company Branding ----------
logo_col, header_col = st.columns([1, 4])

with logo_col:
    st.image("https://logos-world.net/wp-content/uploads/2023/03/Advantech-Logo.png", width=200)

with header_col:
    st.markdown("""
        <h2 style='margin: 0; padding-left: 10px; line-height: 1.2;'>
            Advantech Technical Support Agent
        </h2>
        <p style='color: gray; margin-top: 0; font-size: 1rem; padding-left: 10px;'>
            Technical Support Reasoning Flow
        </p>
    """, unsafe_allow_html=True)

# ---------- Async utility ----------
def run_async(coro):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    if loop.is_running():
        return asyncio.ensure_future(coro)
    else:
        return loop.run_until_complete(coro)
    



# ---------- Main agentic flow ----------
async def run_agent_flow(query: str):
    team = build_team()
    await team.reset()

    steps = []

    async for item in team.run_stream(task=query):
        if isinstance(item, TextMessage):
            steps.append(("text", item.source, item.content))

    st.session_state.agent_steps = steps
    st.session_state.step_index = 0
    st.session_state.flow_completed = False       


# ---------- UI ----------
#query = st.text_area("Incoming email content:", height=200, placeholder="e.g. Hello, my ARK-1123 is overheating...")
ticket_options = {
    "Ticket 1 - ARK-11 Password Configuration ": """Dear Advantech Support Team,

I have recently purchased ARK-11. I cannot find any information about re-setting the admin password and whether BIOS lock is supported by the device. I would be grateful if you could provide me information of admin password change and the lock for BIOS. 

Kind regards,""",
    
    "Ticket 2 - UNO-2271G Overheating Issue": """Hi Support,

Our customer reports that the UNO-2271G unit is overheating after 3 hours of operation. Could you suggest any cooling alternatives or common causes?

Thanks,""",
    
    "Ticket 3 - AIR-150": """Hello Advantech,

I have recently purchased AIR-150. I cant find the instruction on SATA installation. Could you provide me instructions on that? 

Regards,""",
    
    "Ticket 4 - BIOS Update for EPC-S202": """Dear Support Team,

Is there a newer BIOS version for EPC-S202 that supports Wake-on-LAN? I'm using version 1.03 currently.

Thanks in advance,"""
}

# Initialize selected ticket and UI display control
if "selected_ticket" not in st.session_state:
    st.session_state.selected_ticket = None
if "query" not in st.session_state:
    st.session_state.query = ""
if "ticket_chosen" not in st.session_state:
    st.session_state.ticket_chosen = False

if not st.session_state.ticket_chosen:
    st.markdown("### 🎫 Select a Customer Ticket to Analyze")
    selected_option = st.radio("Choose one:", list(ticket_options.keys()), key="ticket_choice")

    if st.button("▶️ Start Agentic Flow"):
        st.session_state.selected_ticket = selected_option
        st.session_state.query = ticket_options[selected_option]
        st.session_state.ticket_chosen = True
        st.rerun()
else:
    st.markdown(f"#### 📨 Selected Ticket:\n```\n{st.session_state.selected_ticket}\n```")
    run_button = st.button("▶️ Start Agentic Flow")

    if run_button and st.session_state.query.strip():
        run_async(run_agent_flow(st.session_state.query))

if "agent_steps" not in st.session_state:
    st.session_state.agent_steps = []
if "step_index" not in st.session_state:
    st.session_state.step_index = 0
if "flow_completed" not in st.session_state:
    st.session_state.flow_completed = False
if "step_shown" not in st.session_state:
    st.session_state.step_shown = False
     
    

# Show step-by-step results
if "step_index" not in st.session_state:
    st.session_state.step_index = 0
if "step_shown" not in st.session_state:
    st.session_state.step_shown = False

agent_display_names = {
    "ticket_classifier": "🤖 Classify Ticket",
    "ticket_analyzer": "🤖 Analyze Ticket",
    "retriever_agent": "🤖 Search Information using Agentic RAG",
    "responder_agent": "🤖 Draft Response",
    "evaluator_agent": "🤖Evaluator Agent",
    "user": " 📧 Receive Incoming Ticket"
}

step_descriptions = {
    'ticket_classifier': 'Checking if the ticket is relevant and could be answered by Advantech Technical Support Team...',
    'ticket_analyzer': 'Detecting the intent and analyzing the request to narrow down the documents to be searched...',
    'retriever_agent': 'Performing search over the knowledge base for relevant information...',
    'responder_agent': 'Writing the user-friendly response based on retrieved information...',
    'evaluator_agent': 'Evaluating the quality and relevance of the response...',
    'user': 'Retrieving user inquiry from Outlook.'
}

if st.session_state.agent_steps:
    for i in range(st.session_state.step_index + 1):
        step = st.session_state.agent_steps[i]
        agent_key = step[1]
        full_text = step[2]
        agent_name = agent_display_names.get(agent_key, agent_key.replace("_", " ").title())
        description = step_descriptions.get(agent_key, "Running agent task...")

        # Show step header
        st.markdown(f"""
            <div style='border-left: 4px solid #2b7cff; padding-left: 1em; margin: 1em 0;'>
                <div style='font-weight: bold; font-size: 0.9rem;'>STEP #{i+1}</div>
                <div style='font-weight: 600; color: #444;'>{agent_name}</div>
                <div style='font-size: 0.85rem; color: #666;'>{description}</div>
                <div style='font-size: 0.9rem; color: #222; margin-top: 0.5em;'>
                    <b>Outcome:</b> 
                </div>
            </div>
        """, unsafe_allow_html=True)

        # Outcome typing effect only for current step
        if i == st.session_state.step_index and not st.session_state.step_shown:
            placeholder = st.empty()
            typed_text = ""
            for char in full_text:
                typed_text += char
                placeholder.markdown(f"<div style='font-size: 0.9rem; color: #222; margin-left: 1em;'>{typed_text}</div>", unsafe_allow_html=True)
                time.sleep(0.02)
            st.session_state.step_shown = True
        else:
            # For previous steps, just show full text immediately
            st.markdown(f"<div style='font-size: 0.9rem; color: #222; margin-left: 1em;'>{full_text}</div>", unsafe_allow_html=True)

        if i < st.session_state.step_index:
            st.markdown("<div class='arrow'>⬇️</div>", unsafe_allow_html=True)

        # Save outputs if needed
        if agent_key == 'responder_agent':
            st.session_state.responder_agent_message = full_text
        if agent_key == 'user':
            st.session_state.user_inquiry = full_text

    # Check for approval and send to Teams
    last_step = st.session_state.agent_steps[-1]
    if last_step[1] == "evaluator_agent" and 'APPROVE' in last_step[2].upper():
        webhook_url = "https://advantecho365.webhook.office.com/webhookb2/c81b03f5-93bb-41f9-bdbe-26e3600b9a42@a77d40d9-dcba-4dda-b571-5f18e6da853f/IncomingWebhook/2dcafd747c2243f695b4279157d8dc41/f4cdb5a2-8613-44fe-81c7-5e3ee2c909b8/V2ZFfDvGZVE4pdmzX5xI00IdIpFgT6LEo2r_-L3d0q8XE1"
        payload = {
            "text": f"User Inquiry 📧: \n {st.session_state.get('user_inquiry')}\n\n\n--------------------------\n\n🧠 Responder Agent Output:\n\n{st.session_state.get('responder_agent_message', 'No responder message found')}"
        }
        try:
            response = requests.post(webhook_url, json=payload)
            print("Teams response:", response.status_code, response.text)
        except Exception as e:
            print("Failed to send message to Teams:", e)


    if not st.session_state.flow_completed and st.session_state.step_index < len(st.session_state.agent_steps) - 1:
        if st.button("➡️ Proceed"):
            st.session_state.step_index += 1
            st.session_state.step_shown = False  # Reset for next step animation
            st.rerun()

    else:
        st.markdown("<div class='arrow'>⬇️</div>", unsafe_allow_html=True)
        st.markdown(f"""
            <div class='footer-step'>
                ✅ Response Approved<br>
                📤 Draft sent to Technical Support for final review via Microsoft Teams.
            </div>
        """, unsafe_allow_html=True)
        st.session_state.flow_completed = True


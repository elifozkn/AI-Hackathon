import requests
import streamlit as st
import asyncio
import nest_asyncio
from autogen_agentchat.base import TaskResult
from autogen_agentchat.messages import TextMessage
from agents import build_team  # ensure this returns a fresh instance
import time

nest_asyncio.apply()
st.set_page_config(page_title="🧠 Advantech Agentic Technical Support", layout="centered")

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
            

  .gray-box {
    background-color: #f2f2f2;
    padding: 1.2em;
    border-radius: 10px;
    margin-top: 0.5em;
    font-family: 'Segoe UI', sans-serif;
    box-shadow: 0 2px 4px rgba(0,0,0,0.05);
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
            Advantech Agent AI Based Technical support
        </h2>
        <p style='color: gray; margin-top: 0; font-size: 1rem; padding-left: 10px;'>
            Agentic Reasoning Flow
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
    "Ticket 1 - ARK-11 Password Configuration ": {
        "sender": "Emily Zhao",
        "email": "emily.zhao@iot-solutions.com",
        "timestamp": "2025-07-18 09:21 AM",
        "body": """Dear Advantech Support Team,

I have recently purchased ARK-11. I cannot find any information about re-setting the admin password and whether BIOS lock is supported by the device. I would be grateful if you could provide me information of admin password change and the lock for BIOS. 

Kind regards,"""
    },

    "Ticket 2 - AIMB-217 Technical Information Inquiry": {
        "sender": "David Kim",
        "email": "david.kim@sysperf.com",
        "timestamp": "2025-07-18 10:43 AM",
        "body": """Hi Support,

I'm looking into the AIMB-217 board. I'm working on system-level performance tracing and I have a few questions about using blktrace and perf. For blktrace, could you explain how to properly configure buffer size and count u, and how to limit event types? I'm also curious about how to stream live output using blkparse, and whether there's a recommended way to set a trace duration with -w. As for perf, I'm particularly interested in tracing dynamic system events. could you elaborate on how to collect things like stack traces or profiling specific tasks? Any best practices for combining these tools efficiently would be really helpful!

Thanks,"""
    },

    "Ticket 3 - ADAM-3600 ": {
        "sender": "Isabella Rossi",
        "email": "isabella.rossi@indcontrol.net",
        "timestamp": "2025-07-17 04:17 PM",
        "body": """Dear Advantech,

Hi, I'm evaluating the ADAM-3600-C2GL1A1E for an industrial IoT project and wanted to confirm some of its capabilities. Could you please provide detailed information on its power requirements? I'm also interested in the CPU specs, memory configuration, supported protocols, OS compatibility, and available expansion slots. Does it also include a VGA video port, and what certifications does it carry? Thanks!

Regards,"""
    },

    "Ticket 4 - Price Inquiry for UNO": {
        "sender": "Liam Becker",
        "email": "liam.becker@procurelogic.com",
        "timestamp": "2025-07-19 08:08 AM",
        "body": """Dear Support Team,

I'm interested in purchasing an UNO computer. Could you inform me about the prices and help me to compare between different models ? 

Thanks in advance,"""
    }
}

# Initialize selected ticket and UI display control
if "selected_ticket" not in st.session_state:
    st.session_state.selected_ticket = None
if "query" not in st.session_state:
    st.session_state.query = ""
if "ticket_chosen" not in st.session_state:
    st.session_state.ticket_chosen = False

if not st.session_state.ticket_chosen:
    st.markdown(f"""
        <div style='border-left: 4px solid #2b7cff; padding-left: 1em; margin: 1em 0;'>
            <div style='font-weight: bold; font-size: 0.9rem;'>STEP #{1}</div>
            <div style='font-weight: 600; color: #444;'>📨 Retrive User Inquiry Email from Ticketing System</div>
            <div style='font-size: 0.85rem; color: #666;'>AI Agent retrieves ticket from the ticketing system (e.g Salesforce, Zendesk) through webhook protocol. As this demonstration act as a proof of concept, the connection is not yet available. For this purpose, we provide a list of emails that simulate the user tickets sent to the ticketing system below. Please select a ticket to proceed with the agentic flow. </div>
        </div>
    """, unsafe_allow_html=True)

    selected_option = st.radio("", list(ticket_options.keys()), key="ticket_choice")

    # Extract structured data
    ticket_data = ticket_options[selected_option]
    sender = ticket_data["sender"]
    email = ticket_data["email"]
    timestamp = ticket_data["timestamp"]
    body = ticket_data["body"]

    # Show fake email format in gray box
    st.markdown(f"""
        <div class="gray-box">
            <div style='
                font-size: 0.7rem;
                color: #222;
                white-space: pre-wrap;
            '>
                <b>From:</b> {sender} &lt;{email}&gt;<br>
                <b>To:</b> Advantech Support &lt;support@advantech.com&gt;<br>
                <b>Date:</b> {timestamp}<br>
                <b>Subject:</b> {selected_option}<br><br>
                {body}
            </div>
        </div>
    """, unsafe_allow_html=True)


    # Save state
    st.session_state.selected_ticket = selected_option
    st.session_state.query = body



    if st.button("▶️ Start Agentic Flow"):
        st.session_state.selected_ticket = selected_option
        st.session_state.query = ticket_options[selected_option]
        st.session_state.ticket_chosen = True
        st.rerun()
else:
    st.markdown(f"""
        <div style='border-left: 4px solid #2b7cff; padding-left: 1em; margin: 1em 0;'>
            <div style='font-weight: bold; font-size: 0.9rem;'>STEP #{1}</div>
            <div style='font-weight: 600; color: #444;'>📨 Retrive User Inquiry Email from Ticketing System :</div>
            <div style='font-size: 0.85rem; color: #666;'>User Email :</div>
        </div>
        <div class="gray-box">
            <div style='font-size: 0.9rem; color: #222; white-space: pre-wrap;'>{st.session_state.query['body']}</div>
        </div>
    """, unsafe_allow_html=True)

    st.markdown("<div class='arrow'>⬇️</div>", unsafe_allow_html=True)

    # Automatically start flow if not already started
    if not st.session_state.agent_steps:
        run_async(run_agent_flow(st.session_state.query['body']))


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
    "retriever_agent": "🤖 Search Information using Agentic Retrieval",
    "responder_agent": "🤖 Draft Response",
    "evaluator_agent": "🤖 Evaluate Draft",
    "user": " 📧 Receive Ticket from the Ticketing System"
}

step_descriptions = {
    'ticket_classifier': 'Many tickets, regarding topics are being created on the ticketing system and not all of them are related to Technical Support. Thus, in the second step, Ticket Classifier identifies if the retrieved ticket could be answerable by the Technical Support Team.',
    'ticket_analyzer': 'Once classified as relevant, the ticket is analyzed by the Ticket Analyzer Agent. In this step the agent breaks down the ticket and identifies the user intent, main topic, product name, related metadata (if available). This process is the starting point of Agentic Retrieval which aims to narrow down the search space prior to semantic search to enhance retrieval capability.',
    'retriever_agent': 'Following ticket analysis, Retriever Agent, first applies filter on the documents to be searched based on the extracted information in the previous step. The filtering ensures that the search step is narrowed down by only involving the most relevant documents and chunks. \n After filtering process, Retrieval Agent performs semantic ranking and vector search to retrieve the most relevant information to user inquiry.',
    'responder_agent': 'Once the information from the knowledge base is retrieved, the Responder Agent drafts a user-friendly response. In the drafting process, the user intent, inquiry and the retrieved information is taken into consideration. No additional information is given and the drafter is restricted to not fabricate information which is not present in the retrieved information.',
    'evaluator_agent': 'In this step, an Evaluator Agent assesses the quality, relevance and the correctness of the drafted response. The evaluation criteria is based on whether the drafted answer answers the question, and whether the response is faithful to the retrieved information from the knowledge base. This evaluation is the very first step in the validation of the response. ',
    'user': 'AI Agent retrieves ticket from the ticketing system (e.g Salesforce, Zendesk) through webhook protocol. As this demonstration act as a proof of concept, the connection is not yet available. For this purpose, we provide a list of emails that simulate the user tickets sent to the ticketing system below : '
}

if st.session_state.agent_steps:
    for i, step in enumerate(st.session_state.agent_steps[:st.session_state.step_index + 1]):
        agent_key = step[1]
        if agent_key == "user":
            continue  # Skip this step

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
                </div>
            </div>
        """, unsafe_allow_html=True)

        # Outcome typing effect only for current step
        if i == st.session_state.step_index and not st.session_state.step_shown:
            placeholder = st.empty()
            typed_text = ""
            for char in full_text:
                typed_text += char
                placeholder.markdown(f"""
                <div class="gray-box">
                    <div style='font-size: 0.9rem; color: #222;'>{typed_text}</div>
                </div>
            """, unsafe_allow_html=True)

                time.sleep(0.02)
            st.session_state.step_shown = True
        else:
          
            st.markdown(f"""
                <div class="gray-box">
                    <div style='font-size: 0.9rem; color: #222;'>{full_text}</div>
                </div>
            """, unsafe_allow_html=True)


        if i < st.session_state.step_index:
            st.markdown("<div class='arrow'>⬇️</div>", unsafe_allow_html=True)

        # Save outputs if needed
        if agent_key == 'responder_agent':
            st.session_state.responder_agent_message = full_text


    # Check for approval and send to Teams
    last_step = st.session_state.agent_steps[-1]

    # 1. Set ticket relevance
    if last_step[1] == 'ticket_classifier' and 'FALSE' in last_step[2].upper():
        st.session_state.ticket_relevant = False
    else: 
        st.session_state.ticket_relevant = True

    # 2. Send to Teams if evaluator approved
    if last_step[1] == "evaluator_agent" and 'APPROVE' in last_step[2].upper():
        webhook_url = "https://advantecho365.webhook.office.com/webhookb2/c81b03f5-93bb-41f9-bdbe-26e3600b9a42@a77d40d9-dcba-4dda-b571-5f18e6da853f/IncomingWebhook/2dcafd747c2243f695b4279157d8dc41/f4cdb5a2-8613-44fe-81c7-5e3ee2c909b8/V2ZFfDvGZVE4pdmzX5xI00IdIpFgT6LEo2r_-L3d0q8XE1"
        payload = {
            "text": f" Date : {st.session_state.get('query')['timestamp']} \n Sender : {st.session_state.get('query')['email']}\n\n\n\n--------------------------\n\n User Inquiry 📧: \n {st.session_state.get('query')['body']}\n\n\n--------------------------\n\n🧠 Responder Agent Output:\n\n{st.session_state.get('responder_agent_message', 'No responder message found')}"
        }
        try:
            response = requests.post(webhook_url, json=payload)
            print("Teams response:", response.status_code, response.text)
        except Exception as e:
            print("Failed to send message to Teams:", e)

    # 3. Step-by-step flow controller
    if not st.session_state.get("flow_completed", False) and st.session_state.step_index < len(st.session_state.agent_steps):
        if st.button("➡️ Proceed"):
            st.session_state.step_index += 1
            st.session_state.step_shown = False  # Reset animation
            st.rerun()

    # 4. Hardcoded last steps
    if st.session_state.step_index >= len(st.session_state.agent_steps):
        st.markdown("<div class='arrow'>⬇️</div>", unsafe_allow_html=True)

        if st.session_state.get("ticket_relevant", True):
            # STEP 7 – Agent Approval
            st.markdown(f"""
                <div style='border-left: 4px solid #2b7cff; padding-left: 1em; margin: 1em 0;'>
                    <div style='font-weight: bold; font-size: 0.9rem;'>STEP #7</div>
                    <div style='font-weight: 600; color: #444;'>Agent Approval</div>
                    <div style='font-size: 0.85rem; color: #666;'>If the Evaluator Agent approves the answer, the response is then sent to the Technical Support Domain Experts through Microsoft Teams for human validation.</div>
                </div>
            """, unsafe_allow_html=True)

            st.markdown(f"""
                <div class="gray-box">
                    <div style="font-size: 0.9rem; color: #222;">
                        ✅ Response Approved by the Evaluator Agent.  <br>
                        📤 Draft sent to Technical Support for final review via Microsoft Teams.
                        Waiting for approval... 
                    </div>
                </div>
            """, unsafe_allow_html=True)
            st.markdown("<div class='arrow'>⬇️</div>", unsafe_allow_html=True)
            # STEP 8 – Reminder Email
            st.markdown(f"""
                <div style='border-left: 4px solid #2b7cff; padding-left: 1em; margin: 1em 0;'>
                    <div style='font-weight: bold; font-size: 0.9rem;'>STEP #8</div>
                    <div style='font-weight: 600; color: #444;'>Send reminder email</div>
                    <div style='font-size: 0.85rem; color: #666;'>Once the response draft is sent through Teams to domain experts, the agentic flow also sends a reminder email indicating that there is a new response draft waiting to be approved. This step makes sure the team is being updated about the status of the tickets.</div>
                </div>
            """, unsafe_allow_html=True)

            st.markdown(f"""
                <div class="gray-box">
                    <div style="font-size: 0.9rem; color: #222;">
                        ✅ Sent reminder email on Outlook for final approval of the draft<br>
                        Waiting for approval... 
                    </div>
                </div>
            """, unsafe_allow_html=True)

        else:
            # Not relevant path
            st.markdown(f"""
                <div class="gray-box">
                    <div style="font-size: 0.9rem; color: #222;">
                        ⚠️ This ticket has been classified as <b>not relevant to Technical Support</b>.<br>
                        🛑 No further agent processing is needed.
                    </div>
                </div>
            """, unsafe_allow_html=True)

        st.session_state.flow_completed = True


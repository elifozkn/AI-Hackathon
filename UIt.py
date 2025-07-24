import requests
import streamlit as st
import asyncio
import nest_asyncio
from autogen_agentchat.base import TaskResult
from autogen_agentchat.messages import TextMessage
from agents import build_team  # ensure this returns a fresh instance
import time
import json 
import html
import json
import pygments
from pygments.lexers import JsonLexer
from pygments.formatters import HtmlFormatter
from datetime import datetime, timedelta

now = datetime.now()
formatted_now = now.strftime("%A, %B %d at %I:%M %p")
def render_custom_json(data):
    def format_value(value):
        if isinstance(value, str):
            return f'<span class="json-string">"{html.escape(value)}"</span>'
        elif isinstance(value, bool):
            return f'<span class="json-boolean">{"true" if value else "false"}</span>'
        elif isinstance(value, (int, float)):
            return f'<span class="json-number">{value}</span>'
        elif value is None:
            return f'<span class="json-null">null</span>'
        return value

    def recurse(obj, indent=0):
        space = '&nbsp;' * (indent * 4)
        if isinstance(obj, dict):
            items = []
            for k, v in obj.items():
                key = f'<span class="json-key">"{html.escape(str(k))}"</span>'
                value = recurse(v, indent + 1)
                items.append(f'{space}&nbsp;&nbsp;{key}: {value}')
            return f'{{<br>{"<br>".join(items)}<br>{space}}}'
        elif isinstance(obj, list):
            items = [recurse(i, indent + 1) for i in obj]
            return f'[{", ".join(items)}]'
        else:
            return format_value(obj)

    return recurse(data)


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
header_col,logo_col= st.columns([7, 1])

#with logo_col:
    #st.image("https://logos-world.net/wp-content/uploads/2023/03/Advantech-Logo.png", width=200)

if "ticket_chosen" not in st.session_state:
    st.session_state.ticket_chosen = False
with header_col:
    if not st.session_state.ticket_chosen:
        st.markdown("""
            <h2 style='margin: 0; padding-left: 0px; line-height: 1.2;'>
                Agentic RAG: Building Accurate & Trustworthy AI Agent for Technical Support
            </h2>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
            <h2 style='margin: 0; padding-left: 0px; line-height: 1.2;'>
                Demo : Agent AI for Technical Support
            </h2>
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

if "hardcoded_step_index" not in st.session_state:
    st.session_state.hardcoded_step_index = 0

# ---------- UI ----------
#query = st.text_area("Incoming email content:", height=200, placeholder="e.g. Hello, my ARK-1123 is overheating...")
ticket_options = {
    "Ticket 1 - ARK-11 Password Configuration ": {
"sender": "Emily Zhao",
"email": "customer@company.com",
"timestamp": "2025-07-18 09:21 AM",
"body": """

Dear  Support Team,

I have recently purchased ARK-11. I cannot find any information about re-setting the admin password and whether BIOS lock is supported by the device. I would be grateful if you could provide me information of admin password change and the lock for BIOS. 
Kind regards,"""
    },

"Ticket 2 - AIMB-217 Technical Information Inquiry": {
"sender": "Emily Zhao",
"email": "customer@company.com",
"timestamp": "2025-07-18 10:43 AM",
    "body": """
Hi Support,

I'm looking into the AIMB-217 board. I'm working on system-level performance tracing and I have a few questions about using blktrace and perf. For blktrace, could you explain how to properly configure buffer size and count u, and how to limit event types? I'm also curious about how to stream live output using blkparse, and whether there's a recommended way to set a trace duration with -w. As for perf, I'm particularly interested in tracing dynamic system events. could you elaborate on how to collect things like stack traces or profiling specific tasks? Any best practices for combining these tools efficiently would be really helpful!
Thanks,"""
    },

    "Ticket 3 - ADAM-3600 ": {
"sender": "Emily Zhao",
"email": "customer@company.com",
"timestamp": "2025-07-17 04:17 PM",
"body": """

Dear Advantech,

Hi, I'm evaluating the ADAM-3600-C2GL1A1E for an industrial IoT project and wanted to confirm some of its capabilities. Could you please provide detailed information on its power requirements? I'm also interested in the CPU specs, memory configuration, supported protocols, OS compatibility, and available expansion slots. Does it also include a VGA video port, and what certifications does it carry? Thanks!
Regards,"""
    },

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
        <div margin: 1em 0;'>
            <div style='font-weight: bold; font-size: 1.5em; margin-top:1.2em;margin-bottom:0.75em'>Ticketing System Emulator</div>
            <div style='font-size: 1rem; color: #423F3F;'>To demonstrate how Agentic AI works in real practice, we’ve prepared several sample support emails from actual customer scenarios.
           <br> In this demo, you’ll walk through the entire process step by step—from receiving the email, to Agentic RAG retrieval, and finally sending the response.
            <br>For simplicity, certain integrations that require complex configurations or restricted access have been virtually simulated, with some outputs pre-set for demonstration purposes.
           <br><br> Please select one of the tickets below and click “Send to AI Agent” to begin the workflow.
    """, unsafe_allow_html=True)

    selected_option = st.radio("", list(ticket_options.keys()), key="ticket_choice")

    # Extract structured data
    ticket_data = ticket_options[selected_option]
    sender = ticket_data["sender"]
    email = ticket_data["email"]
    timestamp = ticket_data["timestamp"]
    body = ticket_data["body"]
    st.markdown("""
    <style>
        .custom-box {
            background-color: #000000;
            color: white;
            font-family: 'Courier New', monospace;
            padding: 1em;
            margin: 1em 0;
            border-radius: 5px;
            font-size: 0.8rem;
            white-space: pre-wrap;
            line-height: 1.1;
            text-align: left;     /* Ensures left alignment */
        }

        .custom-box * {
            margin: 0;
            padding: 0;
        }
    </style>
    """, unsafe_allow_html=True)



    st.markdown(f""" 
        <div class="custom-box">
            <b>From:</b> {sender} &lt;{email}&gt;<br>
            <b>To:</b> Advantech Support &lt;support@advantech.com&gt;<br>
            <b>Date:</b> {timestamp}<br>
            <b>Subject:</b> {selected_option}<br><br>
            {body}
        </div>
    """, unsafe_allow_html=True)




    # Save state
    st.session_state.selected_ticket = selected_option
    st.session_state.query = body



    if st.button("▶️ Send to AI Agent"):
        st.session_state.selected_ticket = selected_option
        st.session_state.query = ticket_options[selected_option]
        st.session_state.ticket_chosen = True
        st.rerun()
else:

    st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=Roboto&display=swap" rel="stylesheet">
<style>
    .roboto {
        font-family: 'Roboto', sans-serif;
    }
    .courier {
        font-family: 'Courier New', monospace;
    }
</style>
""", unsafe_allow_html=True)

    st.markdown(f"""
        <div class="roboto" style='border-left: 4px solid #2b7cff; padding-left: 1em; margin: 1em 0;'>
            <div style='font-weight: bold; font-size: 1.1rem; margin-bottom:0.75em'>STEP {1} : Receive Email from Ticketing System</div>
            <div style='font-size: 1rem; color: #423F3F;'>The AI Agent receives an incoming support email, triggered via a webhook from the ticketing system—such as Salesforce Service Cloud.</div>
        </div>
        <div class="gray-box courier" style='background-color: #000; color: #fff; padding: 1em; border-radius: 8px;'>
            <div style='font-size: 0.9rem; white-space: pre-wrap;'>{st.session_state.query['body']}</div>
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
    "ticket_classifier": "Verify & Classify Ticket",
    "ticket_analyzer": "Analyze User Intent & Extract Metadata",
    "retriever_agent": "Retrieve Relevant Context using Agentic RAG",
    "responder_agent": "Compose Response Draft",
    "evaluator_agent": "Evaluate Response Quality",
    "user": " 📧 Receive Ticket from the Ticketing System"
}

step_descriptions = {
    'ticket_classifier': "It then determines whether the email is relevant. The agent evaluates key criteria—such as whether it’s a new inquiry, which support team is responsible, the product group involved, and the issue category. If the email doesn’t meet the criteria, it’s skipped. This filtering step narrows the agent’s focus—helping maintain accuracy and response quality.",
    'ticket_analyzer': "The AI Agent analyzes the email to understand the user’s intent and extract key metadata—such as product name, model, issue category, document version, and relevant keywords. This structured data helps guide the search for accurate answers.",
    'retriever_agent': 'Using the extracted metadata in the previous step, Agentic RAG filters the document pool—selecting only the most relevant sections. It then applies vector search within this narrowed scope to retrieve the precise context needed to address the issue.',
    'responder_agent': "The AI Agent receives the original email along with the relevant context retrieved by Agentic RAG. It then composes a high-quality draft response—grounded in accurate information and tailored to the user’s inquiry",
    'user': 'AI Agent retrieves ticket from the ticketing system (e.g Salesforce, Zendesk) through webhook protocol. As this demonstration act as a proof of concept, the connection is not yet available. For this purpose, we provide a list of emails that simulate the user tickets sent to the ticketing system below : ',
    'evaluator_agent' : "A dedicated AI Agent reviews the draft for quality—evaluating clarity, conciseness, and relevance. It also cross-references historical replies to ensure consistency and maintain a professional tone. If the quality gap is too significant, it can trigger a new draft request—ensuring only high-quality responses are delivered."
}

st.markdown("""
    <style>
    .fade-in {
        animation: fadeIn 0.7s ease-in;
    }
    @keyframes fadeIn {
        from {opacity: 0; transform: translateY(10px);}
        to {opacity: 1; transform: translateY(0);}
    }
    </style>
""", unsafe_allow_html=True)

if st.session_state.agent_steps:
    for i, step in enumerate(st.session_state.agent_steps[:st.session_state.step_index + 1]):
        agent_key = step[1]
        if agent_key == "user":
            continue

        full_text = step[2]
        agent_name = agent_display_names.get(agent_key, agent_key.replace("_", " ").title())
        description = step_descriptions.get(agent_key, "Running agent task...")

        st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=Roboto&display=swap" rel="stylesheet">
<style>
    .roboto {
        font-family: 'Roboto', sans-serif;
    }
    .courier {
        font-family: 'Courier New', monospace;
    }
    .gray-box {
        background-color: #000;
        color: #fff;
        padding: 1em;
        border-radius: 8px;
        font-family: 'Courier New', monospace;
        font-size: 0.9rem;
        white-space: pre-wrap;
        margin-top: 0.5em;
    }
</style>
""", unsafe_allow_html=True)


        # Header
        st.markdown(f"""
    <div class="roboto" style='border-left: 4px solid #2b7cff; padding-left: 1em; margin: 1em 0;'>
        <div style='font-weight: bold; font-size: 1.1rem; margin-bottom: 0.75em;'>STEP {i+1} : {agent_name}</div>
        <div style='font-size: 1rem; color: #423F3F;'>{description}</div>
    </div>
""", unsafe_allow_html=True)
        
        # Inside the for loop
        st.markdown("""
            <style>
            .custom-json-box {
                background-color: #000;
                color: #e0e0e0;
                font-family: "Courier New", monospace;
                padding: 1em;
                border-radius: 8px;
                font-size: 0.9rem;
                overflow-x: auto;
                white-space: pre-wrap;
            }
            .json-key {
                color: #4FC3F7;
            }
            .json-string {
                color: #A5D6A7;
            }
            .json-number {
                color: #FFD54F;
            }
            .json-boolean {
                color: #F06292;
            }
            .json-null {
                color: #BDBDBD;
            }
            </style>
        """, unsafe_allow_html=True)

        # Render JSON for every step up to current
        try:
            parsed_json = json.loads(full_text)
            formatted_json = render_custom_json(parsed_json)
            st.markdown(f'<div class="custom-json-box">{formatted_json}</div>', unsafe_allow_html=True)

            # Only save responder output once (at current step)
            if i == st.session_state.step_index and not st.session_state.step_shown:
                if agent_key == 'responder_agent':
                    st.session_state.responder_agent_message = parsed_json.get('response', '')
        except json.JSONDecodeError:
            st.error("Invalid JSON")

        st.markdown("<div class='arrow'>⬇️</div>", unsafe_allow_html=True)
        # Save outputs if needed
        


    # Check for approval and send to Teams
    last_step = st.session_state.agent_steps[-1]

    # 1. Set ticket relevance
    if last_step[1] == 'ticket_classifier' and 'FALSE' in last_step[2].upper():
        st.session_state.ticket_relevant = False
    else: 
        st.session_state.ticket_relevant = True
    sent = False
    # 2. Send to Teams if evaluator approved
    if last_step[1] == "evaluator_agent" and 'APPROVE' in last_step[2].upper() and st.session_state.step_index>=6 and not sent:
        webhook_url = "https://advantecho365.webhook.office.com/webhookb2/c81b03f5-93bb-41f9-bdbe-26e3600b9a42@a77d40d9-dcba-4dda-b571-5f18e6da853f/IncomingWebhook/2dcafd747c2243f695b4279157d8dc41/f4cdb5a2-8613-44fe-81c7-5e3ee2c909b8/V2ZFfDvGZVE4pdmzX5xI00IdIpFgT6LEo2r_-L3d0q8XE1"
        payload = {
            "text": f" Date : {st.session_state.get('query')['timestamp']} \n Sender : {st.session_state.get('query')['email']}\n\n\n\n--------------------------\n\n User Inquiry 📧: \n {st.session_state.get('query')['body']}\n\n\n--------------------------\n\n🧠 Responder Agent Output:\n\n{st.session_state.get('responder_agent_message', 'No responder message found')}"
        }
        try:
            response = requests.post(webhook_url, json=payload)
            print("Teams response:", response.status_code, response.text)
            sent = True
        except Exception as e:
            print("Failed to send message to Teams:", e)

    # 3. Step-by-step flow controller
    if not st.session_state.get("flow_completed", False) and st.session_state.step_index < len(st.session_state.agent_steps):
        if st.button("➡️ Next"):
            st.session_state.step_index += 1
            st.session_state.step_shown = False  # Reset animation
            st.rerun()


    # 4. Hardcoded last steps
    if st.session_state.step_index >= len(st.session_state.agent_steps):

        if st.session_state.get("ticket_relevant", True):
            hardcoded_steps = [
                {
                    "title": "STEP 7 : Send Draft to Support Team & Register Reminder",
                    "description": "The AI Agent sends the draft response to the support team via Microsoft Teams for review and final approval. Simultaneously, it creates a reminder in Microsoft Outlook to ensure timely follow-up by the support team.",
                    "box": """
                    🔗 The draft has been sent to the Technical Support Team.<br>You could view the draft: <a href="https://teams.microsoft.com/l/channel/19%3AXILR4XTVcvkQRU8ovnElUGo8jmQhXssT9aDd0Njqtpk1%40thread.tacv2/General?groupId=c81b03f5-93bb-41f9-bdbe-26e3600b9a42&tenantId=a77d40d9-dcba-4dda-b571-5f18e6da853f" target="_blank" style="color: #2b7cff;">here</a>"""
                },
                {
                    "title": "STEP 8: Support Team Gives Feedback",
                    "description": "The support team can approve, revise, or reject the draft response based on their assessment.",
                    "box": """
                    Waiting for approval... <br>Approval received ✔️"""
                },
                {
                    "title": "STEP 9 : Send Approved Response to Customer",
                    "description": "Once feedback is received, the AI Agent sends the final response to the customer through the ticketing system. The associated reminder is automatically cancelled.",
                    "box": "The final response is sent to the customer via ticketing system ✔️"
                },
                {
                    "title": "STEP 10: Store Approved Response to Knowledge Base",
                    "description": "Finally, the AI Agent stores the approved response as part of its learning loop. This historical data is then used by the Evaluator Agent to enhance future draft evaluations",
                    "box": "The final response is stored in the database for future reference 🗃️"
                }
            ]

            current = st.session_state.hardcoded_step_index
            if current < len(hardcoded_steps):
                for i in range(current + 1):  # <-- Show all steps up to current
                    step = hardcoded_steps[i]

                    st.markdown(f"""
                        <div style='border-left: 4px solid #2b7cff; padding-left: 1em; margin: 1em 0;'>
                            <div style='font-weight: bold; font-size: 1.1rem; margin-bottom:0.75em'>{step["title"]}</div>
                            <div style='font-size: 1rem; color: #423F3F;'>{step["description"]}</div>
                        </div>
                    """, unsafe_allow_html=True)

                    st.markdown(f"""
                        <div class="gray-box">
                            <div style="font-size: 0.9rem; color:#FFFFFF;">
                                {step["box"]}
                            </div>
                        </div>
                    """, unsafe_allow_html=True)

                    if i < current:
                        st.markdown("<div class='arrow'>⬇️</div>", unsafe_allow_html=True)

                # Arrow for current step (optional)
                st.markdown("<div class='arrow'>⬇️</div>", unsafe_allow_html=True)

                
                if st.session_state.hardcoded_step_index == 2:
                    st.markdown(f"""
                        <div style="
                            position: fixed;
                            bottom: 80px;
                            right: 30px;
                            width: 360px;
                            background-color: #ffffff;
                            color: #1a1a1a;
                            border-radius: 10px;
                            padding: 1em;
                            display: flex;
                            align-items: center;
                            box-shadow: 0px 4px 12px rgba(0, 0, 0, 0.2);
                            font-family: 'Segoe UI', sans-serif;
                            z-index: 1000;
                        ">
                            <img src="https://logospng.org/download/microsoft-outlook/logo-microsoft-outlook-1024.png"
                                style="width: 40px; height: 40px; margin-right: 1em;" />
                            <div>
                                <div style="font-weight: bold; font-size: 1.05rem;">Outlook Notification</div>
                                <div style="font-size: 0.9rem; margin-top: 0.4em;">
                                    <b>Subject:</b>Approved Content Sent to the Customer<br>
                                    <b>Date:</b> {formatted_now}<br>
                                    <b>Notes:</b> This notification is to update you that the approved response to customer ticket has been send to customer@company.com
                                </div>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)


                if st.session_state.hardcoded_step_index == 0:
                    st.markdown(f"""
                        <div style="
                            position: fixed;
                            bottom: 80px;
                            right: 30px;
                            width: 360px;
                            background-color: #ffffff;
                            color: #1a1a1a;
                            border-radius: 10px;
                            padding: 1em;
                            display: flex;
                            align-items: center;
                            box-shadow: 0px 4px 12px rgba(0, 0, 0, 0.2);
                            font-family: 'Segoe UI', sans-serif;
                            z-index: 1000;
                        ">
                            <img src="https://logospng.org/download/microsoft-outlook/logo-microsoft-outlook-1024.png"
                                style="width: 40px; height: 40px; margin-right: 1em;" />
                            <div>
                                <div style="font-weight: bold; font-size: 1.05rem;">Outlook Reminder</div>
                                <div style="font-size: 0.9rem; margin-top: 0.4em;">
                                    <b>Subject:</b> Follow-up on Support Team Draft<br>
                                    <b>Date:</b> {formatted_now}<br>
                                    <b>Notes:</b> Please review and respond to the AI-generated draft.
                                </div>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
                # Next button
                if not st.session_state.hardcoded_step_index >= len(hardcoded_steps) - 1:
                    if st.button("➡️ Next", key=f"hardcoded_next_{current}") and current < len(hardcoded_steps) - 1:
                        st.session_state.hardcoded_step_index += 1
                        st.rerun()

            if st.session_state.hardcoded_step_index >= len(hardcoded_steps) - 1:
                col1, col2 = st.columns([1, 1])
                with col1:
                    if st.button("🔁 Reset"):
                        st.session_state.hardcoded_step_index = 0
                        st.session_state.ticket_chosen = False
                        st.session_state.step_index = 0
                        st.session_state.query = None
                        st.session_state.flow_completed = False
                        st.session_state.selected_ticke = None
                        st.session_state.hardcoded_step_index = 0
                        
                        st.session_state.agent_steps = []
                        st.session_state.step_index = 0
                        st.session_state.flow_completed = False
                        st.session_state.step_shown = False
                        sent = False
                        st.rerun()
        else:
            st.markdown(f"""
                <div class="gray-box">
                    <div style="font-size: 0.9rem; color: #222;">
                        ⚠️ This ticket has been classified as <b>not relevant to Technical Support</b>.<br>
                        🛑 No further agent processing is needed.
                    </div>
                </div>
            """, unsafe_allow_html=True)


        st.session_state.flow_completed = True


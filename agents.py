from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.ui import Console
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_agentchat.base import TaskResult
from autogen_agentchat.conditions import ExternalTermination, TextMentionTermination
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_core import CancellationToken
from build_retrieval import load_index,hybrid_search
import asyncio
import os

API_KEY = os.getenv("OPENAI_API_KEY")
model_client = OpenAIChatCompletionClient(
    model="gpt-4.1-nano",
    api_key=API_KEY,
)

index, texts, metadata, bm25, model = load_index()



# Define a simple function tool that the agent can use.
# For this example, we use a fake weather tool for demonstration purposes.
async def retrieve(query: str) -> str:
    """Get the weather for a given city."""
    results = str(hybrid_search(query,index,bm25,texts,metadata,20))
    return results


def build_team():
    # Define an AssistantAgent with the model, tool, system message, and reflection enabled.
    # The system message instructs the agent via natural language.
    ticket_classifier_agent = AssistantAgent(
        name="ticket_classifier",
        model_client=model_client,
        system_message="Classify whether the ticket is relevant to Advantech technical support respond with RELEVANT.The ticket is If not,respond with NOT RELEVANT.",
        reflect_on_tool_use=True,
        model_client_stream=True,  # Enable streaming tokens from the model client.
    )

    ticket_analyzer_agent = AssistantAgent(
        name="ticket_analyzer",
        model_client=model_client,
        system_message='''You are a helpful assistant in a technical support system for industrial products.

Given the user query:
"{query}"

If the query contains multiple distinct tasks or intents (e.g., installation + specs), split it accordingly.

For each subquery:

1. Rewrite it if it contains multiple requests.
2. Extract the **product model** mentioned (e.g., AFE-3600).
3. Extract terms which could match the metadata stored in the KB could be specs, product name, keyword, etc. 
4. Classify the intent into one of:
   - spec_request
   - instruction
   - troubleshooting
   - product information
   - product discovery
   - other

Respond clearly with bullet points for each subquery, in this format:

---
Subquery 1:
- 🪄Rewritten Query: ... \n
- 🖥️Product Model: ...\n
-🔍 Intent: ...\n
- 🗄️ Related metadata : 

Subquery 2:
- 🪄Rewritten Query: ...\n
- 🖥️Product Model: ...\n
- 🔍Intent: ...
-🗄️ Related Metadata : 

... and so on.''',
        reflect_on_tool_use=True,
        model_client_stream=True,  # Enable streaming tokens from the model client.
    )

    retriever = AssistantAgent(
        name="retriever_agent",
        model_client=model_client,
        system_message="""In the beginning of your response say "Here's what I found in the knowledge base 🔍 : " 
        
        Given the user ticket and the relevant product, retrieve relevant documents from the internal knowledge base. Make sure to provide as much as detail as possible from the retrieved context. Do not add additional interpretation.Ignore non-informative chunks such as section descriptions.After retrieval respond with : 
          - if you have found relevant information. \n
          - name the source along with the product name related to the source (manual,specs,features etc.) \n
          - what you have found (bullet point list each point should end with \n). 
            """,
        tools=[retrieve],
        reflect_on_tool_use=True,
        model_client_stream=True,  # Enable streaming tokens from the model client.
    )

    responder_agent = AssistantAgent(
        name="responder_agent",
        model_client=model_client,
        system_message="Write a professional support response to the user’s ticket using the ticket content and retrieved documents. Take only what is relevant from the retrieved documents, but do not summarize just give the information/instructions. If retrieved documents are none, ask for the specific model name, product type. End the response with Kind regards, Advantech Technical Support Team",
        reflect_on_tool_use=True,
        model_client_stream=True,  # Enable streaming tokens from the model client.
    )

    evaluator_agent = AssistantAgent(
        name="evaluator_agent",
        model_client=model_client,
        system_message="Evaluate the support draft. Is it accurate, concise, and helpful? Does it miss any information from the retrieved context or add irrelevant/ fabricated information? "
            "If yes, respond with 'APPROVE'.",
        reflect_on_tool_use=True,
        model_client_stream=True,  # Enable streaming tokens from the model client.
    )


    text_termination = TextMentionTermination("APPROVE")
    text_termination1 = TextMentionTermination("NOT RELEVANT")
    external_termination = ExternalTermination()

    team = RoundRobinGroupChat([ticket_classifier_agent, retriever,responder_agent,evaluator_agent], termination_condition=external_termination|text_termination|text_termination1)
    return team
# Run the agent and stream the messages to the console.
# When running inside a script, use a async main function and call it from `asyncio.run(...)`.
#asyncio.run(team.reset())# Reset the team for a new task.




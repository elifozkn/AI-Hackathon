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
        system_message= "Respond with  a VALID json : {new_inquiry : 'true', product_group_involved: , responsible_support_team: 'AEU IIoT Support Team',  issue :, relevant: 'true',received_date: '23.07.2025 9:05' CET, requestor: customer@company.com, email_subject: ,  email_body:  }.",
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
   - spec_request : when the user asks for specifications of a product 
   - instruction : when the user asks for some instructions, how-to s regarding a product
   - troubleshooting : when the user asks for instructions to troubleshoot the issue they have
   - product information : when the user asks for detail about the attributes/features of a product
   - product discovery : when the user is trying to explore the available products, given a attribute/usecase of interest 
5. State the document_type. If intent is spec_request, product information, or discovery it should be "Products Features JSON and Datasheet" 
If intent is instruction or troubleshooting, it should be "Product Manual" 
5. Extract other related metadata if available.
6. Keywords should be the keywords which will facilitate filtering of the documents to be searched.  
Respond in VALID json format and make sure include all keys.: 

{**intent**: ,
**issue_category** :, 
**document_type**: ,
**product_name**: ,
**model_name**: , 
**document_version**: , 
**keywords**: ,
**email_subject: ,
**email_body**: 
}
''',
        reflect_on_tool_use=True,
        model_client_stream=True,  # Enable streaming tokens from the model client.
    )

    retriever = AssistantAgent(
        name="retriever_agent",
        model_client=model_client,
        system_message="""  
        Given the user ticket and the relevant product, retrieve relevant documents from the internal knowledge base. Make sure to provide as much as detail as possible from the retrieved context.  Do not add additional interpretation.Ignore non-informative chunks such as section descriptions.After retrieval respond with : 
          - return a VALID list of json with the following keys : 

    
    {
            email_subject="",

            email_body="",

            contexts=[

                {

                "document_type":"",

                "location":"\\172.21.34.83\\aits\Documents\<document_type>\<product_name>",

                "retrieval_score":"",

                "retrieved_content":""

                },

                {

                "document_type":"",

                "location":""\\172.21.34.83\\aits\Documents\<document_type>\<product_name>"",

                "retrieval_score":"",

                "retrieved_content":""

                },

            ]

            }
 
            """,
        tools=[retrieve],
        reflect_on_tool_use=True,
        model_client_stream=True,  # Enable streaming tokens from the model client.
    )

    responder_agent = AssistantAgent(
        name="responder_agent",
        model_client=model_client,
        system_message="""
 
        
          In the end ONLY return a VALID json with : 
          {"draft_creation_timestamp": 23-07-2025,  
          "requestor": customer@company.com, 
          "issue_category:  ",
          "draft_subject" : ,
          "draft_body: Write a professional support response to the user’s ticket using the ticket content and retrieved documents.
          Take only what is relevant from the retrieved documents, but do not summarize just give the information/instructions. Avoid suggesting consulting the manual or documentation as much as possible.
          If retrieved documents are none, ask for the specific model name, product type. End the response with Kind regards, Advantech Technical Support Team. }
          }""",
        reflect_on_tool_use=True,
        model_client_stream=True,  # Enable streaming tokens from the model client.
    )

    evaluator_agent = AssistantAgent(
        name="evaluator_agent",
        model_client=model_client,
        system_message="Evaluate the support draft. Is it accurate, concise, and helpful? Does it miss any information from the retrieved context or add irrelevant/ fabricated information? "
            "In the end respond with a VALID json with following keys : {'irrelevant_facts' : 0, 'semantic_score:' , 'evaluation_status' : PASSED,'draft_subject' : ,'draft_body': ,}",
        reflect_on_tool_use=True,
        model_client_stream=True,  # Enable streaming tokens from the model client.
    )


    text_termination = TextMentionTermination("PASSED")
    text_termination1 = TextMentionTermination("NOT RELEVANT")
    text_termination2 = TextMentionTermination('false')
    text_termination3 = TextMentionTermination('FALSE')
    external_termination = ExternalTermination()

    team = RoundRobinGroupChat([ticket_classifier_agent, ticket_analyzer_agent, retriever,responder_agent,evaluator_agent], termination_condition=external_termination|text_termination|text_termination1 | text_termination2 | text_termination3)
    return team
# Run the agent and stream the messages to the console.
# When running inside a script, use a async main function and call it from `asyncio.run(...)`.
#asyncio.run(team.reset())# Reset the team for a new task.
# Run the agent and stream the messages to the console.
# When running inside a script, use a async main function and call it from `asyncio.run(...)`.
#asyncio.run(team.reset())# Reset the team for a new task.







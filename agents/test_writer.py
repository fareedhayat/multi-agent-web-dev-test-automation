'''
This agent goes through the requirements files and the artifacts folder to write natural language playwright test suite.
Tools:
    - requirements parser (Writes a summary of what was required)
    - artifacts folder parser (Writes a summary of what is present in code)
    - tests generator (Writes test cases for the application)
'''

from agent_framework.azure import AzureOpenAIAssistantsClient
from agent_framework import ai_function
from azure.identity import AzureCliCredential

import os
from dotenv import load_dotenv

load_dotenv()

endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
api_key = os.getenv("AZURE_OPENAI_KEY")
requirements_summary_deployment = os.getenv("")
code_summary_deployment = os.getenv("")
test_writer_deployment = os.getenv("")

@ai_function(
    name="requiremnts_file_parser",
    description="Gets the contents of the requirements file and writes a summary of it to feed to the test writer."
)
def requirements_file_parser():
    '''
    Uses a basic LLM for summary.
    We will use the requirements summary deployment LLM here.
    This function will access the requirements file and create the summary using LLM.
    '''
    
    print('')
    
    
@ai_function(
    name="generated_code_parser",
    description="Gets the contents of the artifacts folder and writes a summary of it to feed to the test writer."
)
def generated_code_parser():
    '''
    parameters: The output from the coder agent.
    Uses an LLM for summary.
    We will use the code summary deployment LLM here.
    This function will access the artifacts folder and all the files in it.
    This will create a seperate summary file for each code file.
    '''
    print('')


@ai_function(
    name="test_generator",
    description="Gets the output from requirement parser and the code parser and write test cases based on that."
)
def test_generator():
    '''
    parameters: 
        - Requirements summary
        - code summary
    Uses an LLM to generate test cases based on both summaries.
    We will use the main agent LLM in this that will take both summaries and generate the test cases.
    '''
    print('')
    

async def main() -> None:
    
    async with AzureOpenAIAssistantsClient(
        endpoint=endpoint,
        api_key=api_key,
        deployment_name=test_writer_deployment,
        api_version="2024-12-01-preview"
    ).create_agent(
        name="TestWriterAgent",
        instructions="""
        """,
        tools=[requirements_file_parser, generated_code_parser, test_generator]
    ) as agent:
        print('')
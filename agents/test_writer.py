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

@ai_function(
    name="requiremnts_file_parser",
    description="Gets the contents of the requirements file and writes a summary of it to feed to the test writer."
)
def requirements_file_parser():
    '''Uses a basic LLM for summary.'''
    print('')
    
    
@ai_function(
    name="generated_code_parser",
    description="Gets the contents of the artifacts folder and writes a summary of it to feed to the test writer."
)
def generated_code_parser():
    '''
    parameters: The output from the coder agent.
    Uses an LLM for summary.
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
    Uses an LLM for summary.
    '''
    print('')
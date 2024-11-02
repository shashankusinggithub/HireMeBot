from langchain_ollama import OllamaLLM
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel
from typing import List
from langchain.output_parsers import ResponseSchema, StructuredOutputParser
import json
from json_repair import repair_json


# Define the expected output structure
response_schemas = [
    ResponseSchema(
        name="matching_percent",
        description="matching percentage for the job description should be a 2 digit number",
    ),
    ResponseSchema(
        name="cover letter",
        description="cover letter relevant to my profile and job description and company",
    ),
]

my_resume = json.loads(open("data/resume.json").read())
# Initialize the parser
parser = StructuredOutputParser.from_response_schemas(response_schemas)

# Create the prompt template with specific instructions for JSON format
prompt = PromptTemplate(
    template="""Provide a matching percentage and cover letter review for {my_resume} and {job_description} for {company} in JSON format.
    
    {format_instructions}
    
    Please ensure the review includes:
    - Match percentage of my_resume and job_description
    - Cover Letter if match percentage is greater than 50
    
    Return the response in valid JSON format.""",
    input_variables=["my_resume", "job_description", "company"],
    partial_variables={"format_instructions": parser.get_format_instructions()},
)

# Initialize Ollama
llm = OllamaLLM(model="llama3.2")


def get_result(job_description: str, company: str = "") -> dict:
    # Get the formatted prompt
    formatted_prompt = prompt.format(
        my_resume=my_resume, job_description=job_description, company=company
    )

    # Get response from Ollama

    for _ in range(3):
        try:
            response = llm.invoke(formatted_prompt)
            # Parse the response to ensure it's valid JSON
            # First, find the JSON content (it might be wrapped in markdown code blocks)
            json_content = response
            if "```json" in response:
                json_content = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                json_content = response.split("```")[1].split("```")[0].strip()

            # Parse the JSON content
            parsed_response = json.loads(repair_json(json_content))
            if parsed_response["matching_percent"]:
                return parsed_response

        except json.JSONDecodeError as e:
            print(f"Error parsing JSON: {e}")
            print("Raw response:", response)
    return None


options_response_schemas = [
    ResponseSchema(
        name="text",
        description="option thats suitable to the question and also that increases the chance to get selected for an interview",
    ),
    ResponseSchema(
        name="value", description="should match always with the given options"
    ),
]
options_parser = StructuredOutputParser.from_response_schemas(options_response_schemas)

options_prompt = PromptTemplate(
    template="""You are a bot who are expert in selecting option from multiple options or if options are not provided you give descriptive answer. You have to select the option that is suitable for the question and also increases the chance of getting selected for an interview.
    Output:
    ```json
    {format_instructions}
    ```
    question: {question}

    options: 
    ```json
    {options}
    ```

    resume: 
    ```json
    {my_resume}
    ```
    
    Please ensure the option and data includes only the appropriate option from options if options are provided or descriptive answer that is suitable for the question and resume.
    - Option should always match with the given options if provided.
    - Data should always match with the given options.
    - Avoid Descriptive answers.
    - Prefer answering direct in number values if options are not provided.
    - Output should be in JSON
    - Return the response in valid JSON
    - if options are not provided return json with descriptive answer should be in string 
    
    
    Return the response in valid JSON format.""",
    input_variables=["my_resume", "question", "options"],
    partial_variables={"format_instructions": options_parser.get_format_instructions()},
)


def choose_option(question: str, options: List[dict] = None) -> dict:
    # Get the formatted prompt
    formatted_prompt = options_prompt.format(
        my_resume=my_resume, question=question, options=options
    )

    # Get response from Ollama
    response = llm.invoke(formatted_prompt)

    try:
        # Parse the response to ensure it's valid JSON
        # First, find the JSON content (it might be wrapped in markdown code blocks)
        json_content = response
        if "```json" in response:
            json_content = response.split("```json")[1].split("```")[0].strip()
        elif "```" in response:
            json_content = response.split("```")[1].split("```")[0].strip()

        # Parse the JSON content
        parsed_response = json.loads(repair_json(json_content))
        return parsed_response

    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}")
        print("Raw response:", response)
        return None


# Example usage
if __name__ == "__main__":
    try:
        description = """
• Bachelor’s degree in computer science, or related technical discipline with proven experience coding in languages including, but not limited to, C, C++, C#, Java, JavaScript, or Python
• Understanding of Computer Science fundamentals
"""
        review = get_result(description, "Microsoft")
        print("\nRaw JSON output:")
        print(json.dumps(review, indent=2))

    except Exception as e:
        print(f"Error: {e}")

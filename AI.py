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

my_resume = {
    "personalInfo": {
        "name": "Shashank Chutke",
        "contact": {
            "phone": "+91 8143127849",
            "email": "shashank.chutke@gmail.com",
            "links": {
                "linkedin": "LinkedIn",
                "portfolio": "Portfolio",
                "github": "GitHub",
            },
        },
    },
    "profileSummary": "Experienced Full-Stack Developer skilled in JavaScript, Python, and modern frameworks. Proven success in building scalable APIs, integrating AI, and automating data security tasks. Strong background in project leadership and competitive coding achievements.",
    "skills": [
        "JavaScript",
        "Python",
        "TypeScript",
        "MSSQL",
        "Node",
        "Express",
        "React JS",
        "Vue JS",
        "Next JS",
        "Redux",
        "NoSQL",
        "Git",
        "GraphQL",
        "Jest",
        "Flask",
        "MongoDB",
        "Linux/Unix",
        "Docker",
        "CSS",
        "HTML",
        "Microservices",
        "Postgres",
        "Backend",
        "Full-Stack",
        "Cypress",
        "Playwright",
        "Django",
        "Redis",
        "Selenium",
        "RabitMQ",
    ],
    "experience": [
        {
            "title": "Principal Software Engineer",
            "company": "Wexa.ai",
            "location": "Hyderabad, India",
            "period": "10/2024 – current",
            "responsibilities": [
                "Contributed to building AI co-workers by refactoring the application for improved performance and scalability, optimizing it for handling heavy loads."
            ],
        },
        {
            "title": "SDE-1",
            "company": "CloudSEK",
            "location": "Bangalore, India",
            "period": "03/2024 – 08/2024",
            "responsibilities": [
                "Created an automated script to scrape data from various websites using specific keywords, successfully identifying and flagging fake customer care numbers.",
                "Created an automated script to download stealer logs and files from various cloud file storage services.",
                "Actively monitored and scraped forums on the dark web to detect and report sensitive information breaches, contributing to enhanced data security measures.",
            ],
        },
        {
            "title": "Founding Engineer",
            "company": "Truto",
            "location": "Bangalore, India",
            "period": "09/2023 – 02/2024",
            "responsibilities": [
                "Integrated AI Chat bots on various platforms like Meta Messenger, Meta Workspace, Microsoft Teams, Google Chat, etc.",
                "Added many features and revamped the company website.",
            ],
        },
        {
            "title": "Software Engineer",
            "company": "Pensieve",
            "location": "Jakarta, Indonesia",
            "period": "09/2022 - 09/2023",
            "responsibilities": [
                "Designed and implemented scalable APIs for setting up a license monitoring project from scratch which was an internal project.",
                "Worked with face-recognition AWS APIs to create an application for detecting faces in videos using Django.",
                "Developed Web Scraping bots to scrape social media websites like Facebook, Instagram and Twitter using Playwright automation framework.",
                "Added feature to the product which helped the clients to categorize different telecom users with graphical representation of the data.",
                "Continuous Integration/Deployment Pipeline Integration, pull requests, code reviews, unit/integration/e2e testing",
            ],
        },
    ],
    "education": {
        "degree": "Bachelor of Technology",
        "major": "Electronics and Communication Engineering",
        "institution": "JNTU, Hyderabad",
        "location": "Hyderabad, India",
        "period": "08/2016 - 08/2021",
    },
    "projects": [
        {
            "name": "Movie Search App",
            "date": "06/2022",
            "description": "Designed an Interactive movies search app using external API which can be bookmarked and create playlists which can be shared using sharable link generated.",
            "technologies": ["React", "Node.js", "Express.js", "MongoDB"],
            "link": "Movies App",
        }
    ],
    "achievements": [
        {
            "title": "HackOn Top Contestant",
            "issuer": "Amazon Coding Competition",
            "year": "2022",
            "description": "In top 100 participants Pan India of HackOn with Amazon Coding Competition.",
        },
        {
            "title": "3rd Position in zonal Round of RoboTryst-15",
            "year": "2015",
            "description": "Secured Third position in zonal Round of RoboTryst-15 organized by Robosapiens Technologies Pvt Ltd.",
        },
    ],
}
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
    response = llm.invoke(formatted_prompt)

    for _ in range(3):
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


options_response_schemas = [
    ResponseSchema(
        name="text",
        description="option thats suitable to the question and also that increases the chance to get selected for an interview",
    ),
    ResponseSchema(name="value", description="should match with the given options"),
]
options_parser = StructuredOutputParser.from_response_schemas(options_response_schemas)

options_prompt = PromptTemplate(
    template="""You are a bot who are expert in selecting option from multiple options or if options are not provided you give descriptive answer. You have to select the option that is suitable for the question and also increases the chance of getting selected for an interview.
    Output:
    {format_instructions}
    
    Please ensure the option and data includes only the appropriate option from options if options are provided or descriptive answer that is suitable for the question and resume.
    - Option should match with the given options if provided.
    - Data should match with the given options.
    - Output should be in JSON
    - Return the response in valid JSON
    - if options are not provided return json with descriptive answer should be in string 
    
    question: {question}
    options: {options}
    resume: {my_resume}

  

    
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
        parsed_response = json.loads(json_content)
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

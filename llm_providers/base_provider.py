from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from langchain.prompts import PromptTemplate
from langchain.output_parsers import ResponseSchema, StructuredOutputParser
import json
from json_repair import repair_json
import os


class BaseLLMProvider(ABC):
    def __init__(self):
        base_path = os.path.dirname(os.path.dirname(__file__))
        self.resume = json.loads(
            open(os.path.join(base_path, "data", "resume.json")).read()
        )
        self.metadata = json.loads(
            open(os.path.join(base_path, "data", "metadata.json")).read()
        )
        self._setup_parsers()
        self._setup_prompts()
        self._setup_system_messages()

    def _setup_system_messages(self):
        """Set up system messages for different tasks."""
        self.match_system_message = """You are an expert AI recruitment assistant specialized in analyzing job descriptions 
        and matching them with candidate profiles. Your task is to provide accurate matching percentages based on skills, 
        experience, and qualifications. Always return responses in valid JSON format with careful consideration of both 
        technical and soft skills."""

        self.get_answers_system_message = """You are an expert AI career counselor specialized in helping candidates make 
        optimal choices for job applications and interviews. Your role is to analyze questions and options in the context 
        of the candidate's profile and select the most advantageous response. Always return responses in valid JSON format 
        and prioritize choices that enhance interview success probability."""

    def _setup_parsers(self):
        self.match_schemas = [
            ResponseSchema(
                name="matching_percent",
                description="matching percentage for the job description should be a 2 digit number",
            )
        ]

        self.get_answers_schemas = [
            ResponseSchema(
                name="answers",
                description="list of answers for questions provided",
                type="list",
            )
        ]

        self.match_parser = StructuredOutputParser.from_response_schemas(
            self.match_schemas
        )
        self.get_answers_parser = StructuredOutputParser.from_response_schemas(
            self.get_answers_schemas
        )

    def _setup_prompts(self):
        self.match_prompt = PromptTemplate(
            template="""Provide a matching percentage for {my_resume} and {job_description} for {company} in JSON format.
            
            {format_instructions}
            
            Please ensure the review includes:
            - Match percentage of my_resume and job_description
            - Respond should be parsable JSON.
            - No other information is required.
            
            Return the response in valid JSON format.""",
            input_variables=["my_resume", "job_description", "company"],
            partial_variables={
                "format_instructions": self.match_parser.get_format_instructions()
            },
        )

        self.get_answers_prompt = PromptTemplate(
            template="""You are a human being and a software developer applying job online. Always answer like a human being
            Output:
            ```json
            {format_instructions}
            ```
            questions:
             ```json
            {questions}
            ```

            resume: 
            ```json
            {my_resume}
            ```

            metadata:
            ```json
            {metadata}
            ```

            
            Please ensure the option and data includes only the appropriate option from options if options are not provided respond with descriptive answer that is suitable for the question and resume and metadata.
            - Return the response in valid JSON   
            - Response should always match with the given options.
            - Avoid Descriptive answers.
            - Prefer answering direct in number values if options are not provided.
            - If options are not provided return json with descriptive answer should be in string 
            
            Return the response in valid JSON format.""",
            input_variables=["my_resume", "questions", "metadata"],
            partial_variables={
                "format_instructions": self.get_answers_parser.get_format_instructions()
            },
        )

    @abstractmethod
    def _get_llm_response(self, prompt: str, system_message: str = None) -> str:
        """Abstract method to get response from specific LLM provider."""
        pass

    def _parse_json_response(self, response: str) -> dict:
        json_content = response
        if "```json" in response:
            json_content = response.split("```json")[1].split("```")[0].strip()
        elif "```" in response:
            json_content = response.split("```")[1].split("```")[0].strip()
        return json.loads(repair_json(json_content))

    def get_result(self, job_description: str, company: str = "") -> Optional[dict]:
        formatted_prompt = self.match_prompt.format(
            my_resume=self.resume, job_description=job_description, company=company
        )

        for _ in range(3):
            try:
                response = self._get_llm_response(
                    formatted_prompt, self.match_system_message
                )
                parsed_response = self._parse_json_response(response)
                if parsed_response.get("matching_percent"):
                    return parsed_response
            except Exception as e:
                print(f"Error: {e}")
        return None

    def get_answers(self, questions: str, options: List[dict] = None) -> Optional[dict]:
        formatted_prompt = self.get_answers_prompt.format(
            my_resume=self.resume,
            questions=questions,
            options=options,
            metadata=self.metadata,
        )

        try:
            response = self._get_llm_response(
                formatted_prompt, self.get_answers_system_message
            )
            return self._parse_json_response(response)
        except Exception as e:
            print(f"Error: {e}")
            return None

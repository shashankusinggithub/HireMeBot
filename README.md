# Comprehensive Documentation for Job Application Automation Tool

## Overview

The Job Application Automation Tool is designed to automate the process of applying for jobs on platforms such as LinkedIn and Microsoft. It utilizes web scraping techniques and AI models to streamline the application process, generate tailored responses, and manage job application submissions efficiently.

## Table of Contents

1. [Project Structure](#project-structure)
2. [Installation](#installation)
3. [Configuration](#configuration)
4. [Usage](#usage)
   - [Applying for Jobs](#applying-for-jobs)
   - [AI Integration](#ai-integration)
5. [AI Providers](#ai-providers)
   - [OllamaProvider](#ollamaprovider)
   - [GeminiProvider](#geminiprovider)
6. [Logging and Error Handling](#logging-and-error-handling)
7. [Contributing](#contributing)
8. [License](#license)

## Project Structure

The project is organized into several directories and files, each serving a specific purpose:

```
.
├── .env                     # Environment variables for configuration
├── AI.py                    # Main AI interaction module
├── cookie_file.json         # JSON file for storing cookies
├── main.py                  # Entry point for the application
├── assets/                  # Directory for additional assets (e.g., PDFs)
│   └── Shashank_Chutke.pdf  # Example PDF document
├── config/                  # Configuration files
│   ├── settings.py          # Settings and configurations using Pydantic
│   └── __init__.py         # Package initialization
├── core/                    # Core functionalities of the application
│   ├── browser_manager.py    # Manages browser interactions using Selenium
│   ├── exceptions.py         # Custom exception definitions
│   ├── queue_manager.py      # Manages job queues for URLs
│   └── url_processor.py      # Processes URLs and interacts with site handlers
├── data/                    # Data storage directory
│   ├── cookie_file.json      # Cookie storage for sessions
│   ├── credentials.json      # User credentials for job applications
│   ├── metadata.json         # Metadata related to job applications
│   ├── processed.json        # Log of processed applications
│   └── resume.json           # User resume information
├── llm_providers/           # Language model providers for AI interaction
│   ├── base_provider.py       # Base class for LLM providers
│   ├── factory.py            # Factory class to create LLM provider instances
│   ├── gemini_provider.py     # Specific implementation for Gemini provider
│   ├── ollama_provider.py     # Specific implementation for Ollama provider
│   ├── opennAI_provider.py    # Specific implementation for OpenAI provider
│   └── __init__.py          # Package initialization
├── logs/                    # Log files directory
│   ├── application_attempts.log  # Log of application attempts
│   ├── error.log              # Error logs during execution
│   └── main.log               # General logs for the application run
└── sites/                   # Site-specific handlers for job applications
    ├── base_site.py          # Base class for site handlers
    ├── linkedin.py           # Handler for LinkedIn interactions
    ├── microsoft.py          # Handler for Microsoft interactions
    └── __init__.py          # Package initialization
└── utils/                   # Utility functions and helpers
    ├── logger.py             # Logger setup and configuration
    └── utilities.py          # Miscellaneous utility functions
```

## Installation

To set up this project, follow these steps:

1. **Clone the Repository**:

   ```bash
   git clone <repository-url>
   cd <repository-name>
   ```

2. **Install Dependencies**: Ensure you have Python installed, then install the required packages:

   ```bash
   pip install -r requirements.txt
   ```

3. **Environment Variables**: Create a `.env` file in the root directory and add your API keys:

   ```
   GEMINI_API_KEY=your_api_key_here
   GEMINI_API_KEY2=your_second_api_key_here
   GEMINI_API_KEY3=your_third_api_key_here
   ```

4. **Ollama Installation**: To use the Ollama language model, ensure you have it installed on your system. You can install Ollama by following these steps:

   - Visit the [Ollama installation page](https://ollama.com/docs/install) and follow the instructions specific to your operating system.

5. **Run the Application**: Start the application by executing:
   ```bash
   python main.py
   ```

## Configuration

The configuration settings are defined in `config/settings.py`, which uses Pydantic to manage environment variables and application settings.

### Key Configuration Options:

- `BASE_DIR`: Base directory of the project.
- `DATA_DIR`: Directory where data files are stored.
- `CREDENTIALS_FILE`: Path to the credentials JSON file.
- `BROWSER_TIMEOUT`: Timeout setting for browser operations.
- `IMPLICIT_WAIT`: Implicit wait time for Selenium operations.
- `MAX_RETRIES`: Maximum retries allowed when processing URLs.
- `QUEUE_SLEEP_TIME`: Time to wait before retrying a failed URL.

## Usage

### Applying for Jobs

The main functionality of the application is encapsulated in `main.py`, which initializes the browser, loads credentials, and processes job URLs.

1. **Load Credentials**: The application requires user credentials to log into job sites. Ensure your `credentials.json` file in the `data` directory contains your login details formatted as follows:

```json
{
  "linkedin": {
    "username": "your_linkedin_username",
    "password": "your_linkedin_password"
  },
  "microsoft": {
    "username": "your_microsoft_username",
    "password": "your_microsoft_password"
  }
}
```

2. **Add Job URLs**: You can add URLs directly in `main.py` using:

```python
job_queue.add_url("https://www.linkedin.com/jobs/search/?currentJobId=3801964907&f_AL=true")
job_queue.add_url("https://jobs.careers.microsoft.com/global/en/job/1748714/Software-Engineer")
```

Alternatively, you can read from a file containing URLs (one per line) by using `job_queue.add_urls_from_file("job_urls.txt")`.

3. **Process Job Applications**: The application processes each URL in the queue, logging in with provided credentials, navigating to job postings, and submitting applications based on predefined criteria.

### AI Integration

The tool utilizes AI to generate responses tailored to job descriptions:

- The interaction with Ollama is handled in `AI.py`. You can generate responses using:

```python
result = get_result(job_description="Your Job Description Here", company="Company Name")
```

## AI Providers

### OllamaProvider

The `OllamaProvider` is implemented in the `ollama_provider.py` file within the `llm_providers` directory. It is designed to interact with the Ollama API to generate responses based on job descriptions or specific questions.

**Key Functions:**

- `get_result(job_description: str, company: str = "") -> dict`: This function takes a job description and an optional company name as input and returns a structured response generated by the Ollama model.

**Example Usage:**

```python
ollama_llm = LLMProviderFactory.create_provider(
    provider_type="ollama",
    model_name="gemma2",
)
result = ollama_llm.get_result(job_description="Software Engineer at XYZ", company="XYZ Corp")
```

### GeminiProvider

The `GeminiProvider` is similarly structured and implemented in the `gemini_provider.py` file. It interfaces with the Gemini API to provide answers to questions, making it suitable for scenarios requiring more structured responses.

**Key Functions:**

- `get_answers(question: str, options: List[dict] = None) -> dict`: This function accepts a question and optional answer choices (in case of multiple-choice questions) and returns a response from the Gemini model.

**Example Usage:**

```python
llm = LLMProviderFactory.create_provider(
    provider_type="gemini",
    api_key=api_key,
    model_name="gemini-1.5-flash",
)
answers = llm.get_answers(question="What are your strengths?", options=[{"text": "Teamwork"}, {"text": "Communication"}])
```

## Logging and Error Handling

Logging is configured using Loguru, allowing you to track application behavior and errors through log files located in the `logs/` directory.

### Custom Exceptions

Custom exceptions are defined in `exceptions.py` to handle various error scenarios:

- `JobBotException`: Base exception class.
- `BrowserException`: Raised when browser-related operations fail.
- `ApplicationException`: Raised when there is an issue with job applications.

### Log Files

Log files are generated during execution:

- **application_attempts.log**: Logs attempts made to apply for jobs.
- **error.log**: Logs any errors encountered during execution.
- **main.log**: General logs that capture information about application runs.

## Contributing

Contributions are welcome! Please fork the repository and submit a pull request with your changes. Ensure that your code adheres to existing coding standards and includes appropriate tests.

import logging
import os
from datetime import datetime
from typing import List
from dotenv import load_dotenv
from dateutil import parser as dateparser
from dateutil.relativedelta import relativedelta
from pydantic import BaseModel, Field

load_dotenv()
logger = logging.getLogger(__name__)

if "OPENAI_API_KEY" not in os.environ:
    raise EnvironmentError(
        "OPENAI_API_KEY is not set. "
        "Please set it as an environment variable before starting the application."
    )


def format_list_as_string(l: list, list_sep: str = "\n- ") -> str:
    if isinstance(l, list):
        return list_sep + list_sep.join(l)
    return str(l)


def format_prompt_inputs_as_strings(prompt_inputs: list[str], **kwargs):
    """Convert values to string for all keys in kwargs matching list in prompt inputs"""
    return {
        k: format_list_as_string(v) for k, v in kwargs.items() if k in prompt_inputs
    }


def parse_date(d: str) -> datetime:
    """Given an arbitrary string, parse it to a date"""
    # set default date to January 1 of current year
    default_date = datetime(datetime.today().year, 1, 1)
    try:
        return dateparser.parse(str(d), default=default_date)
    except dateparser._parser.ParserError as e:
        logger.error(f"Date input `{d}` could not be parsed.")
        raise e


def datediff_years(start_date: str, end_date: str) -> float:
    """Get difference between arbitrarily formatted dates in fractional years to the floor month"""
    datediff = relativedelta(parse_date(end_date), parse_date(start_date))
    return datediff.years * 1.0 + datediff.months / 12.0


# Pydantic class that defines the format to be returned by the LLM
class Job_Description(BaseModel):
    """Description of a job posting"""

    company: str = Field(
        ..., description="Name of the company that has the job opening"
    )
    job_title: str = Field(..., description="Job title")
    job_link: str = Field(..., description="Link of job application")
    team: str = Field(
        ...,
        description="Name of the team within the company. Team name should be null if it's not known.",
    )
    job_summary: str = Field(
        ..., description="Brief summary of the job, not exceeding 100 words"
    )
    salary: str = Field(
        ...,
        description="Salary amount or range. Salary should be null if it's not known.",
    )
    duties: List[str] = Field(
        ...,
        description="The role, responsibilities and duties of the job as an itemized list, not exceeding 500 words",
    )
    qualifications: List[str] = Field(
        ...,
        description="The qualifications, skills, and experience required for the job as an itemized list, not exceeding 500 words",
    )
    is_fully_remote: bool = Field(
        ...,
        description="Does the job have an option to work fully (100%) remotely? Hybrid or partial remote is marked as `False`. Use `None` if the answer is not known.",
    )


class Job_Skills(BaseModel):
    """Skills from a job posting"""

    technical_skills: List[str] = Field(
        ...,
        description="An itemized list of technical skills, including programming languages, technologies, and tools. Examples: Python, MS Office, Machine learning, Marketing, Optimization, GPT",
    )
    non_technical_skills: List[str] = Field(
        ...,
        description="An itemized list of non-technical Soft skills. Examples: Communication, Leadership, Adaptability, Teamwork, Problem solving, Critical thinking, Time management",
    )


# Pydantic class that defines each highlight to be returned by the LLM
class Resume_Section_Highlight(BaseModel):
    highlight: str = Field(..., description="one highlight")
    relevance: int = Field(
        ..., description="relevance of the bullet point", enum=[1, 2, 3, 4, 5]
    )


# Pydantic class that defines a list of highlights to be returned by the LLM
class Resume_Section_Highlighter_Output(BaseModel):
    plan: List[str] = Field(..., description="itemized <Plan>")
    additional_steps: List[str] = Field(..., description="itemized <Additional Steps>")
    work: List[str] = Field(..., description="itemized <Work>")
    final_answer: List[Resume_Section_Highlight] = Field(
        ..., description="itemized <Final Answer> in the correct format"
    )


# Pydantic class that defines a list of skills to be returned by the LLM
class Resume_Skills(BaseModel):
    technical_skills: List[str] = Field(
        ...,
        description="An itemized list of technical skills",
    )
    non_technical_skills: List[str] = Field(
        ...,
        description="An itemized list of non-technical skills",
    )


# Pydantic class that defines a list of skills to be returned by the LLM
class Resume_Skills_Matcher_Output(BaseModel):
    plan: List[str] = Field(..., description="itemized <Plan>")
    additional_steps: List[str] = Field(..., description="itemized <Additional Steps>")
    work: List[str] = Field(..., description="itemized <Work>")
    final_answer: Resume_Skills = Field(
        ..., description="<Final Answer> in the correct format"
    )


class Resume_Summarizer_Output(BaseModel):
    plan: List[str] = Field(..., description="itemized <Plan>")
    additional_steps: List[str] = Field(..., description="itemized <Additional Steps>")
    work: List[str] = Field(..., description="itemized <Work>")
    final_answer: str = Field(..., description="<Final Answer> in the correct format")


# Pydantic class that defines a list of improvements to be returned by the LLM
class Resume_Improvements(BaseModel):
    section: str = Field(
        ...,
        enum=[
            "summary",
            "education",
            "experience",
            "projects",
            "skills",
            "spelling and grammar",
            "other",
        ],
    )
    improvements: List[str] = Field(
        ..., description="itemized list of suggested improvements"
    )


class Resume_Improver_Output(BaseModel):
    plan: List[str] = Field(..., description="itemized <Plan>")
    additional_steps: List[str] = Field(..., description="itemized <Additional Steps>")
    work: List[str] = Field(..., description="itemized <Work>")
    final_answer: List[Resume_Improvements] = Field(
        ..., description="<Final Answer> in the correct format"
    )

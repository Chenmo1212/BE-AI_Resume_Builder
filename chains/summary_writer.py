from langchain_core.runnables import Runnable
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.language_models import BaseChatModel
from llm.prompt_loader import load_prompt
from prompts import Resume_Summarizer_Output


def build_summary_writer_chain(llm: BaseChatModel) -> Runnable:
    """
    Build the summary writer LCEL chain.

    Generates a professional resume summary based on the candidate's
    resume content and the target job posting.

    Args:
        llm: A LangChain BaseChatModel instance.

    Returns:
        A LangChain Runnable expecting keys:
        company, job_summary, degrees, projects, experiences, skills
    """
    prompt = load_prompt("summary_writer")
    parser = PydanticOutputParser(pydantic_object=Resume_Summarizer_Output)
    return prompt | llm | parser

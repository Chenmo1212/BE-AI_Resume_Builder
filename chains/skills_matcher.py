from langchain_core.runnables import Runnable
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.language_models import BaseChatModel
from llm.prompt_loader import load_prompt
from prompts import Resume_Skills_Matcher_Output


def build_skills_matcher_chain(llm: BaseChatModel) -> Runnable:
    """
    Build the skills matcher LCEL chain.

    Extracts technical and non-technical skills from the resume that match
    the job posting requirements.

    Args:
        llm: A LangChain BaseChatModel instance.

    Returns:
        A LangChain Runnable expecting keys:
        technical_skills, non_technical_skills, projects, experiences
    """
    parser = PydanticOutputParser(pydantic_object=Resume_Skills_Matcher_Output)
    prompt = load_prompt("skills_matcher").partial(
        format_instructions=parser.get_format_instructions()
    )
    return prompt | llm | parser

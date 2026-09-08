from langchain_core.runnables import Runnable
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.language_models import BaseChatModel
from llm.prompt_loader import load_prompt
from prompts import Resume_Improver_Output


def build_improver_chain(llm: BaseChatModel) -> Runnable:
    """
    Build the resume improver LCEL chain.

    Critiques the finalized resume against the job posting and
    suggests improvements by section.

    Args:
        llm: A LangChain BaseChatModel instance.

    Returns:
        A LangChain Runnable expecting keys:
        duties, qualifications, technical_skills, non_technical_skills,
        summary, experiences, projects, education, skills
    """
    parser = PydanticOutputParser(pydantic_object=Resume_Improver_Output)
    prompt = load_prompt("improver").partial(
        format_instructions=parser.get_format_instructions()
    )
    return prompt | llm | parser

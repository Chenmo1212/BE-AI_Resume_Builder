from langchain_core.runnables import Runnable
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.language_models import BaseChatModel
from llm.prompt_loader import load_prompt
from prompts import Resume_Section_Highlighter_Output


def build_section_highlighter_chain(llm: BaseChatModel) -> Runnable:
    """
    Build the section highlighter LCEL chain.

    Takes job posting details and a raw resume section, returns
    Resume_Section_Highlighter_Output with plan, work, and final_answer highlights.

    Args:
        llm: A LangChain BaseChatModel instance (e.g. from create_llm()).

    Returns:
        A LangChain Runnable expecting keys:
        duties, qualifications, technical_skills, non_technical_skills, section
    """
    parser = PydanticOutputParser(pydantic_object=Resume_Section_Highlighter_Output)
    prompt = load_prompt("section_highlighter").partial(
        format_instructions=parser.get_format_instructions()
    )
    return prompt | llm | parser

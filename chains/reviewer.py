from langchain_core.runnables import Runnable
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.language_models import BaseChatModel
from llm.prompt_loader import load_prompt
from prompts import ReviewerOutput


def build_reviewer_chain(llm: BaseChatModel) -> Runnable:
    """
    Build the reviewer LCEL chain.

    Evaluates resume content against hard-coded North American resume standards.
    Never rewrites content — only judges and provides revision instructions.

    Args:
        llm: A LangChain BaseChatModel instance.

    Returns:
        A LangChain Runnable expecting keys:
        section_type ("highlight" or "summary"), content, previous_feedback
    """
    parser = PydanticOutputParser(pydantic_object=ReviewerOutput)
    prompt = load_prompt("reviewer").partial(
        format_instructions=parser.get_format_instructions()
    )
    return prompt | llm | parser

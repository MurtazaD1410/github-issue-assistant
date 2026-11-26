from langchain_ollama import ChatOllama
from config import OLLAMA_MODEL, OLLAMA_TEMPERATURE

llm = ChatOllama(model=OLLAMA_MODEL, temperature=OLLAMA_TEMPERATURE)


async def generate_title(user_message: str) -> str | None:
    prompt = f"""
    Generate a concise title for a conversation based on
    the following first user message.

    Rules:
    - Maximum 6 words.
    - Return only the title.
    - No quotation marks.
    - No explanations.

    User message:
    {user_message}
    """

    try:
        response = await llm.ainvoke(prompt)
        title = response.content.strip()

        return title if title else None

    except Exception as e:
        print(f"Title generation failed: {e}")
        return None

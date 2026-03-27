from __future__ import annotations


def generate_hyde_query(user_query: str, llm) -> str:
    from langchain_core.prompts import ChatPromptTemplate

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are an expert software engineer. Write a brief hypothetical answer that would best retrieve documentation relevant to the user's question.",
            ),
            ("human", "{input}"),
        ]
    )
    try:
        chain = prompt | llm
        response = chain.invoke({"input": user_query})
        content = getattr(response, "content", "") or str(response)
        if content.strip():
            return f"{user_query}\n\n{content.strip()}"
    except Exception:
        pass
    return user_query

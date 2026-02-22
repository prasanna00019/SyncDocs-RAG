import os
from typing import List
from langchain_ollama import ChatOllama
from ollama_utils import get_best_ollama_model
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import CommaSeparatedListOutputParser

class URLFilter:
    def __init__(self):
        # We use a local Ollama model for this filtering task
        self.model_name = get_best_ollama_model()
        if not self.model_name:
            raise RuntimeError("Could not find a valid Ollama model. Ensure Ollama is running.")

        self.llm = ChatOllama(model=self.model_name, temperature=0)
        self.output_parser = CommaSeparatedListOutputParser()

        # Prompt to instruct the LLM to pick out the most relevant URLs
        self.prompt = PromptTemplate(
            template="""You are an intelligent documentation assistant. 
Your goal is to look at a list of documentation URLs and select ONLY the URLs that are most likely to contain the answer to the user's query.
Select at most 5 URLs. Return them as a comma-separated list.
If none of the URLs seem relevant, return an empty string.

User Query: {query}

Available URLs:
{urls}

Response (Comma-separated URLs only):""",
            input_variables=["query", "urls"]
        )

        self.chain = self.prompt | self.llm | self.output_parser

    def filter_urls(self, query: str, mapped_urls: List[str], max_urls_to_send: int = 150) -> List[str]:
        """
        Takes a huge list of mapped URLs and uses an LLM to select the most relevant ones.
        Limits the number of URLs sent in the prompt to avoid blowing up the context window.
        """
        if not mapped_urls:
            return []

        print(f"Filtering {len(mapped_urls)} URLs for query: '{query}'")

        # Truncate if there are way too many URLs
        urls_subset = mapped_urls[:max_urls_to_send]
        urls_string = "\n".join(urls_subset)

        try:
            # Run the LLM chain
            selected_urls = self.chain.invoke({
                "query": query,
                "urls": urls_string
            })

            # Clean up the URLs (LLMs sometimes add quotes or spaces)
            cleaned_urls = [url.strip().strip("'\"") for url in selected_urls if url.strip()]

            # Ensure the selected URLs were actually in our original list to prevent hallucinations
            valid_urls = [url for url in cleaned_urls if url in mapped_urls]

            print(f"LLM selected {len(valid_urls)} relevant URLs.")
            return valid_urls

        except Exception as e:
            print(f"Error during URL filtering: {e}")
            # Fallback: Just return the first few URLs if LLM fails
            return mapped_urls[:3]

if __name__ == "__main__":
    pass

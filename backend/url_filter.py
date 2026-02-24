import os
from typing import List, Dict, Any
import math
from langchain_community.embeddings import HuggingFaceEmbeddings

class URLFilter:
    def __init__(self):
        # We use a lightning fast local HuggingFace model for embeddings instead of Ollama
        self.model_name = "sentence-transformers/all-MiniLM-L6-v2"
        self.embeddings = HuggingFaceEmbeddings(model_name=self.model_name)

    def filter_urls(self, query: str, mapped_urls: List[Dict[str, Any]], max_urls_to_send: int = 150) -> List[str]:
        """
        Filters URLs semantically by comparing query embeddings to URL metadata embeddings.
        Leaves out URLs that don't have a title or description.
        """
        if not mapped_urls:
            return []

        print(f"Filtering {len(mapped_urls)} URLs for query: '{query}'")

        valid_links = []
        for link in mapped_urls:
            url = link.get("url")
            title = link.get("title")
            desc = link.get("description")
            # User specified: ignore URLs without title or description
            if url and (title or desc):
                valid_links.append({"url": url, "title": title, "description": desc})

        if not valid_links:
            print("No URLs with title/description found to filter.")
            return []

        try:
            # Generate embedding for the query
            query_embedding = self.embeddings.embed_query(query)

            # Construct representation string for each valid link
            texts = []
            for link in valid_links:
                rep = []
                if link.get("title"):
                    rep.append(f"Title: {link['title']}")
                if link.get("description"):
                    rep.append(f"Description: {link['description']}")
                texts.append(" | ".join(rep))

            # Generate embeddings for the documents
            link_embeddings = self.embeddings.embed_documents(texts)

            def cosine_similarity(v1, v2):
                dot_product = sum(x * y for x, y in zip(v1, v2))
                mag1 = math.sqrt(sum(x * x for x in v1))
                mag2 = math.sqrt(sum(y * y for y in v2))
                if mag1 == 0 or mag2 == 0:
                    return 0
                return dot_product / (mag1 * mag2)

            scored_links = []
            for i, doc_emb in enumerate(link_embeddings):
                score = cosine_similarity(query_embedding, doc_emb)
                scored_links.append((score, valid_links[i]["url"]))

            scored_links.sort(key=lambda x: x[0], reverse=True)
            
            selected_urls = [url for score, url in scored_links]
            print(f"Semantically sorted {len(selected_urls)} relevant URLs.")
            return selected_urls

        except Exception as e:
            print(f"Error during semantic URL filtering: {e}")
            # Fallback
            return [link["url"] for link in valid_links]

if __name__ == "__main__":
    pass

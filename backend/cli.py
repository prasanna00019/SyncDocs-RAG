import os
import sys
import argparse
from dotenv import load_dotenv

from firecrawl_client import DocsCrawler
from url_filter import URLFilter
from rag_system import RAGSystem

# Load environment variables
load_dotenv()

def check_env():
    if not os.getenv("FIRECRAWL_API_KEY"):
        print("Error: FIRECRAWL_API_KEY not found in environment.")
        sys.exit(1)
    
    if not os.getenv("OPENAI_API_KEY"):
        print("Note: OPENAI_API_KEY not found. Defaulting to local Ollama.")

def main():
    parser = argparse.ArgumentParser(description="Live Docs RAG System")
    parser.add_argument("--url", type=str, help="The base documentation URL to map and ingest")
    parser.add_argument("--query", type=str, required=True, help="Your coding question")
    parser.add_argument("--limit", type=int, default=5, help="Max URLs to scrape after filtering (keep <10 to save time/credits)")
    args = parser.parse_args()

    check_env()

    print("\n--- Live Docs RAG System Initializing ---")
    crawler = DocsCrawler()
    url_filter = URLFilter()
    rag = RAGSystem()
    
    # If a URL is provided, we do the full ingestion flow
    if args.url:
        print(f"\n[1/5] Mapping Documentation: {args.url}")
        mapped_urls = crawler.map_documentation(args.url)
        
        if not mapped_urls:
            print("Failed to map any URLs. Exiting.")
            sys.exit(1)
            
        print(f"\n[2/5] Intelligent URL Filtering for query: '{args.query}'")
        # We limit the number of URLs to scrape to save time and API costs
        filtered_urls = url_filter.filter_urls(args.query, mapped_urls)
        
        # Take only the top N specified by user
        urls_to_scrape = filtered_urls[:args.limit]
        print(f"Selected Top {len(urls_to_scrape)} URLs to scrape: {urls_to_scrape}")
        
        if not urls_to_scrape:
            print("No relevant URLs found. Try a different query or base URL.")
            sys.exit(1)
            
        print(f"\n[3/5] Scraping Markdown Content from {len(urls_to_scrape)} Pages")
        scraped_data = crawler.scrape_urls(urls_to_scrape)
        
        if not scraped_data:
            print("Failed to scrape markdown content. Exiting.")
            sys.exit(1)
            
        print(f"\n[4/5] Chunking and Ingesting to Vector DB")
        rag.chunk_and_ingest(scraped_data)
        
    else:
        print(f"\n[Skip 1-4] Note: No base --url provided. Assuming docs are already ingested into ChromaDB locally.")
        
    print(f"\n[5/5] Generating Answer")
    print("-" * 40)
    print(f"User Query: {args.query}")
    print("-" * 40)
    
    try:
        answer = rag.query(args.query)
        print("\nAnswer:\n")
        print(answer)
    except Exception as e:
        print(f"\nError generating answer: {e}")
        
    print("\n-----------------------------------------")

if __name__ == "__main__":
    main()

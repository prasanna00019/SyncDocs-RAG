import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def main():
    print("Welcome to Live Docs RAG System")
    # Verify API keys
    if not os.getenv("FIRECRAWL_API_KEY"):
        print("Warning: FIRECRAWL_API_KEY not found in environment.")
    if not os.getenv("OPENAI_API_KEY"):
        print("Warning: OPENAI_API_KEY not found in environment.")

if __name__ == "__main__":
    main()

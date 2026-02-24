import os
from firecrawl import Firecrawl
from typing import List, Dict, Any

class DocsCrawler:
    def __init__(self):
        # Firecrawl automatically looks for FIRECRAWL_API_KEY in the environment
        self.app = Firecrawl()

    def map_documentation(self, url: str) -> List[Dict[str, Any]]:
        """
        Takes a base URL and uses Firecrawl's v2 /map endpoint to find all related sub-links.
        Returns a list of dicts containing url and potentially metadata like title or description.
        """
        print(f"Mapping sub-links for: {url}...")
        try:
            # v2 API: app.map(url) returns a MapData object with .links
            map_result = self.app.map(url)

            # Extract raw links which could be objects or dicts
            links_raw = map_result.links if hasattr(map_result, "links") else map_result.get("links", [])
            
            links = []
            for link in links_raw:
                if isinstance(link, dict):
                    links.append(link)
                else:
                    links.append({
                        "url": getattr(link, "url", str(link)),
                        "title": getattr(link, "title", None),
                        "description": getattr(link, "description", None)
                    })

            print(f"Found {len(links)} links mapped from {url}")
            return links

        except Exception as e:
            print(f"Error mapping URL {url}: {e}")
            return []

    def scrape_urls(self, urls: List[str]) -> List[Dict[str, Any]]:
        """
        Takes a list of URLs and scrapes their content in Markdown format.
        Returns a list of dicts with 'url' and 'markdown' keys.
        """
        scraped_data = []
        print(f"Scraping {len(urls)} URLs...")

        for url in urls:
            try:
                # v2 API: app.scrape(url, formats=[...]) returns a Document object
                result = self.app.scrape(url, formats=["markdown"])

                # The Document object has a .markdown attribute
                if result and result.markdown:
                    scraped_data.append({
                        'url': url,
                        'markdown': result.markdown,
                        'metadata': result.metadata if hasattr(result, 'metadata') else {}
                    })
                    print(f"Successfully scraped: {url}")
                else:
                    print(f"Failed to extract markdown from: {url}")

            except Exception as e:
                print(f"Error scraping {url}: {e}")

        return scraped_data

if __name__ == "__main__":
    # Simple test (requires API key)
    # crawler = DocsCrawler()
    # links = crawler.map_documentation("https://docs.firecrawl.dev/")
    # print(links[:5])
    pass

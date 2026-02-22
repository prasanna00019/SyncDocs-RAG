import os
from firecrawl import Firecrawl
from typing import List, Dict, Any

class DocsCrawler:
    def __init__(self):
        # Firecrawl automatically looks for FIRECRAWL_API_KEY in the environment
        self.app = Firecrawl()

    def map_documentation(self, url: str) -> List[str]:
        """
        Takes a base URL and uses Firecrawl's v2 /map endpoint to find all related sub-links.
        Returns a list of URL strings.
        """
        print(f"Mapping sub-links for: {url}...")
        try:
            # v2 API: app.map(url) returns a MapData object with .links
            map_result = self.app.map(url)

            # map_result.links is a list of LinkResult objects, each with a .url attribute
            links = [link.url for link in map_result.links]

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

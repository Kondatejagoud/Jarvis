import webbrowser
import urllib.parse
import httpx
import re

def web_search(query: str) -> str:
    """
    Performs a real-time web search anonymously via DuckDuckGo.
    Returns the top 4 search results (title, snippet, and link) directly as text
    to the LLM. If the network request fails, falls back to opening Google in the browser.
    """
    cleaned_query = query.strip()
    if not cleaned_query:
        return "Error: Search query cannot be empty."
        
    url = "https://html.duckduckgo.com/html/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
    }
    payload = {"q": cleaned_query}
    
    try:
        # 1. Attempt to fetch live web search results as text
        response = httpx.post(url, data=payload, headers=headers, timeout=10.0)
        if response.status_code == 200:
            blocks = re.findall(r'result__body.*?class="clear"', response.text, re.DOTALL)
            results = []
            
            for block in blocks:
                title_match = re.search(r'class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', block, re.DOTALL)
                snippet_match = re.search(r'class="result__snippet"[^>]*href="[^"]+"[^>]*>(.*?)</a>', block, re.DOTALL)
                
                if title_match:
                    link = title_match.group(1)
                    if "uddg=" in link:
                        matches = re.search(r'uddg=([^&]+)', link)
                        if matches:
                            link = urllib.parse.unquote(matches.group(1))
                            
                    title = re.sub(r'<[^>]+>', '', title_match.group(2)).strip()
                    
                    snippet = ""
                    if snippet_match:
                        snippet = re.sub(r'<[^>]+>', '', snippet_match.group(1)).strip()
                        
                    # Decode HTML entities
                    title = title.replace('&amp;', '&').replace('&#x27;', "'").replace('&quot;', '"').replace('&lt;', '<').replace('&gt;', '>').replace('&nbsp;', ' ')
                    snippet = snippet.replace('&amp;', '&').replace('&#x27;', "'").replace('&quot;', '"').replace('&lt;', '<').replace('&gt;', '>').replace('&nbsp;', ' ')
                    
                    results.append(f"Title: {title}\nURL: {link}\nSnippet: {snippet}\n")
                    
            if results:
                return f"Top search results for query '{cleaned_query}':\n\n" + "\n".join(results[:4])
                
    except Exception as e:
        print(f"[WebSearch] Fetch failed ({e}). Falling back to browser tab...")
        
    # 2. Fallback: Open Google search tab in local browser
    try:
        safe_query = urllib.parse.quote(cleaned_query)
        webbrowser.open(f"https://www.google.com/search?q={safe_query}")
        return f"Warning: Failed to fetch live search snippets. Opened fallback browser search tab for query: '{cleaned_query}'."
    except Exception as e:
        return f"Failed to perform search fallback: {e}"

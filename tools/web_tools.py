import webbrowser
import urllib.parse

def web_search(query: str) -> str:
    """
    Open the default web browser and perform a search query.
    Ensures that query text is treated strictly as data.
    """
    cleaned_query = query.strip()
    if not cleaned_query:
        return "Error: Search query cannot be empty."
        
    safe_query = urllib.parse.quote(cleaned_query)
    url = f"https://www.google.com/search?q={safe_query}"
    
    try:
        webbrowser.open(url)
        return f"Successfully opened default browser search for: '{cleaned_query}'"
    except Exception as e:
        return f"Failed to open web search in browser: {e}"

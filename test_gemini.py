import os
import httpx
import config

def test_key():
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        print("ERROR: GEMINI_API_KEY environment variable is not set!")
        return

    print(f"Testing API Key (Starts with: '{key[:6]}...', Total Length: {len(key)})")
    
    # Standard Google AI Studio keys start with "AIzaSy"
    if not key.startswith("AIzaSy"):
        print("WARNING: Gemini API keys from Google AI Studio usually start with 'AIzaSy'.")
        print(f"Your key starts with '{key[:6]}'. Please double-check if you copied the correct key from https://aistudio.google.com/")
        print("-" * 60)

    # 1. Test standard generateContent API
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{config.GEMINI_MODEL}:generateContent?key={key}"
    payload = {
        "contents": [{"parts": [{"text": "Hello, write a 3-word greeting."}]}]
    }
    
    print(f"\n1. Testing Native Gemini API (generateContent) using {config.GEMINI_MODEL}...")
    try:
        response = httpx.post(url, json=payload, timeout=10.0)
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            print("Success! Native API Response:")
            print(response.json()["candidates"][0]["content"]["parts"][0]["text"])
        else:
            print(f"Failed! Raw Response: {response.text}")
    except Exception as e:
        print(f"Error calling Native API: {e}")

    # 2. Test OpenAI-compatible endpoint
    url_openai = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
    headers_openai = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json"
    }
    payload_openai = {
        "model": config.GEMINI_MODEL,
        "messages": [{"role": "user", "content": "Hello"}]
    }
    
    print(f"\n2. Testing OpenAI-Compatible Gemini Endpoint using {config.GEMINI_MODEL}...")
    try:
        response = httpx.post(url_openai, headers=headers_openai, json=payload_openai, timeout=10.0)
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            print("Success! OpenAI-Compatible Response:")
            print(response.json()["choices"][0]["message"]["content"])
        else:
            print(f"Failed! Raw Response: {response.text}")
    except Exception as e:
        print(f"Error calling OpenAI endpoint: {e}")

    # 3. List available models
    url_list = f"https://generativelanguage.googleapis.com/v1beta/models?key={key}"
    print("\n3. Fetching list of all available models for your key...")
    try:
        response = httpx.get(url_list, timeout=10.0)
        if response.status_code == 200:
            models_data = response.json().get("models", [])
            print("Supported models list:")
            for m in models_data:
                name = m.get("name", "").replace("models/", "")
                # Print only flash/lite/chat models to keep output clean
                if "flash" in name or "lite" in name or "chat" in name:
                    print(f" - {name}")
        else:
            print(f"Failed to list models: {response.text}")
    except Exception as e:
        print(f"Error listing models: {e}")

if __name__ == "__main__":
    test_key()

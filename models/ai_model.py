def process_document(file):
    text = file.read().decode('utf-8')
    # Placeholder for AI logic
    summary = f"Processed {len(text)} characters."
    return summary


def chat(prompt: str, model: str = 'mock') -> str:
    """Return a reply for the prompt. If OPENAI_API_KEY is set in env, will call OpenAI's chat API.
    For now 'mock' returns an echo reply useful for development.
    """
    import os
    key = os.environ.get('OPENAI_API_KEY')
    if key and model != 'mock':
        # Try calling OpenAI Chat Completions (simple implementation using requests)
        try:
            import requests
            url = 'https://api.openai.com/v1/chat/completions'
            headers = {
                'Authorization': f'Bearer {key}',
                'Content-Type': 'application/json'
            }
            data = {
                'model': model,
                'messages': [{'role': 'user', 'content': prompt}],
                'max_tokens': 500,
            }
            resp = requests.post(url, headers=headers, json=data, timeout=15)
            resp.raise_for_status()
            j = resp.json()
            return j['choices'][0]['message']['content'].strip()
        except Exception as e:
            return f"(AI error: {e})"
    # Mock reply
    return f"Echo: {prompt}"
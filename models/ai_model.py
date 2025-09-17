def process_document(file):
    # Try to detect type by filename attribute (Flask FileStorage provides .filename)
    filename = getattr(file, 'filename', None) or 'upload.txt'
    name = str(filename)
    # If it's a text file, save to /tmp and index it
    if name.lower().endswith('.txt'):
        import tempfile
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.txt')
        data = file.read()
        # ensure bytes -> text
        try:
            text = data.decode('utf-8')
        except Exception:
            text = data.decode('latin-1')
        tmp.write(text.encode('utf-8'))
        tmp.flush()
        tmp_path = tmp.name
        tmp.close()
        try:
            from models.retriever import index_text
            n = index_text(tmp_path, source_name=name)
            return f"Indexed {n} chunks from {name}."
        except Exception as e:
            return f"Indexing failed: {e}"
    # fallback: read and return a simple processed summary
    text = file.read().decode('utf-8')
    summary = f"Processed {len(text)} characters."
    return summary


def chat(prompt: str, model: str = 'mock') -> str:
    """Return a reply for the prompt. If OPENAI_API_KEY is set in env, will call OpenAI's chat API.
    For now 'mock' returns an echo reply useful for development.
    """
    import os
    key = os.environ.get('OPENAI_API_KEY')
    # Try retrieval first (if available)
    try:
        from models.retriever import search as retriever_search
        retrieved = retriever_search(prompt, k=5)
    except Exception:
        retrieved = []

    # If we have retrieved context, prepend it to the prompt
    if retrieved:
        ctx = "\n\n--- Retrieved documents ---\n"
        for r in retrieved:
            ctx += f"Source (row={r.get('meta', {}).get('source_row')}): {r.get('text')}\n\n"
        prompt = ctx + "\n\nUser question:\n" + prompt

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
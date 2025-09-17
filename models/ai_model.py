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
    # If no real model is configured, provide helpful rule-based troubleshooting responses
    # Simple heuristics: look for keywords and return structured guidance
    low = prompt.lower()
    # Common categories
    if any(k in low for k in ('error', 'traceback', 'exception', 'crash')):
        return (
            "It looks like you're seeing an error. Try these steps:\n"
            "1) Read the full traceback to find the error type and file/line.\n"
            "2) Search for the exact error message. Many issues are already reported.\n"
            "3) Check recent changes — what code or dependency was updated?\n"
            "4) Reproduce with a minimal test case and add logging around the failing area.\n"
            "If you paste the exact error message I can give more targeted advice."
        )
    if any(k in low for k in ('how do i fix', 'how to fix', 'fix it', 'help')):
        return (
            "Here's a troubleshooting checklist: \n"
            "- Confirm steps to reproduce the issue and the expected behavior.\n"
            "- Check logs and tracebacks (server and client).\n"
            "- Isolate the failure to a single component (frontend/backend/db).\n"
            "- Try rolling back recent changes or run in a clean environment.\n"
            "- If it's an import/module error, ensure dependencies are installed in the active venv.\n"
            "If you give me the error text or the command you ran I can suggest exact commands."
        )
    if any(k in low for k in ('slow', 'performance', 'lag')):
        return (
            "Performance troubleshooting suggestions:\n"
            "- Measure where time is spent (profilers for backend, devtools for frontend).\n"
            "- Check database query times and add indexes where needed.\n"
            "- Cache expensive computations and use pagination for large lists.\n"
            "- For TTS/ML models, ensure batching and GPU use where possible.\n"
        )
    # Generic helpful response wrapping the prompt
    return (
        "I can help troubleshoot. Here are a few starter steps:\n"
        "1) Share the exact command or action that caused the issue.\n"
        "2) Copy the full error or describe the unexpected behavior.\n"
        "3) Tell me what you have already tried.\n\n"
        f"You asked: {prompt}\n\nIf you paste the error text or logs I will give prioritized steps to fix it."
    )
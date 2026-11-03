"""OpenCode Go / OpenAI-compatible chat endpoint for 20004 Edition.
No API key is stored or logged. Intended for future native sidebar integration.
"""
import json
import os
import urllib.request
import urllib.error

OPENCODE_GO_ENDPOINT = "https://opencode.ai/inference/go/openai/v1/chat/completions"
DEFAULT_MODEL = "deepseek-v4-pro"

def chat(messages, api_key, model=DEFAULT_MODEL, endpoint=OPENCODE_GO_ENDPOINT, timeout=90):
    if not api_key or not api_key.strip():
        raise ValueError("API Key is required")
    if not endpoint.startswith("https://"):
        raise ValueError("A secure HTTPS endpoint is required")
    if not model or not model.strip():
        raise ValueError("Model ID is required")
    payload=json.dumps({"model":model,"messages":messages,"stream":False},ensure_ascii=False).encode("utf-8")
    req=urllib.request.Request(endpoint,data=payload,headers={
        "Authorization":"Bearer "+api_key,
        "Content-Type":"application/json",
        "User-Agent":"NotepadPP-20004-Edition/0.1"
    },method="POST")
    try:
        with urllib.request.urlopen(req,timeout=timeout) as response:
            result=json.loads(response.read(16*1024*1024).decode("utf-8"))
    except urllib.error.HTTPError as exc:
        # Do not leak response content, which may include secret or account details.
        raise RuntimeError("Provider returned HTTP "+str(exc.code)) from None
    return result["choices"][0]["message"]["content"]

if __name__ == "__main__":
    import argparse, getpass
    p=argparse.ArgumentParser()
    p.add_argument("--model",default=DEFAULT_MODEL)
    p.add_argument("--endpoint",default=OPENCODE_GO_ENDPOINT)
    p.add_argument("--text",required=True)
    a=p.parse_args()
    key=os.environ.get("OPENCODE_GO_API_KEY") or getpass.getpass("OpenCode Go API Key: ")
    print(chat([{"role":"user","content":a.text}],key,a.model,a.endpoint))

"""
Unified LLM Client supporting Groq Cloud API (fast Llama 3.3/3.1) and local Ollama.
"""
import json
import requests
from config import Config


class OllamaError(Exception):
    pass


def chat_completion(messages, tools=None, temperature=0.2, format=None):
    """
    Calls Groq (if configured) or falls back to Ollama.
    Returns OpenAI/Ollama compatible dict: {"message": {"role": "assistant", "content": "...", "tool_calls": [...]}}
    """
    provider = getattr(Config, "LLM_PROVIDER", "groq").lower()
    groq_key = getattr(Config, "GROQ_API_KEY", "").strip()

    if provider == "groq" and groq_key:
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {groq_key}",
            "Content-Type": "application/json",
        }
        
        # Clean messages for OpenAI/Groq schema
        # Keep system prompt + last 4 messages to stay safely within Groq 8,000 TPM free tier
        if len(messages) > 5:
            sys_msg = [messages[0]] if messages and messages[0].get("role") == "system" else []
            tail_msgs = messages[-4:]
            filtered_messages = sys_msg + [m for m in tail_msgs if m != sys_msg]
        else:
            filtered_messages = messages

        formatted_messages = []
        for idx, m in enumerate(filtered_messages):
            msg_dict = {"role": m.get("role"), "content": m.get("content") or ""}
            if m.get("tool_calls"):
                clean_tc = []
                for tc_idx, tc in enumerate(m["tool_calls"]):
                    fn = tc.get("function", {})
                    args = fn.get("arguments", {})
                    if not isinstance(args, str):
                        args = json.dumps(args)
                    call_id = tc.get("id") or f"call_{idx}_{tc_idx}"
                    clean_tc.append({
                        "id": call_id,
                        "type": "function",
                        "function": {
                            "name": fn.get("name"),
                            "arguments": args
                        }
                    })
                msg_dict["tool_calls"] = clean_tc
            if m.get("role") == "tool":
                msg_dict["name"] = m.get("name", "tool")
                if "tool_call_id" in m and m["tool_call_id"]:
                    msg_dict["tool_call_id"] = m["tool_call_id"]
                else:
                    # Find previous assistant tool call id if possible
                    prev_call_id = f"call_{idx-1}_0"
                    msg_dict["tool_call_id"] = prev_call_id
            formatted_messages.append(msg_dict)

        payload = {
            "model": getattr(Config, "GROQ_MODEL", "openai/gpt-oss-20b"),
            "messages": formatted_messages,
            "temperature": temperature,
        }

        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        if format == "json":
            payload["response_format"] = {"type": "json_object"}

        # Multi-model resilience: fallback through active Groq models supported by the account
        groq_models = [
            "qwen/qwen3.8-27b",
            "openai/gpt-oss-120b",
            "openai/gpt-oss-20b",
            "qwen/qwen3.6-27b"
        ]
        # remove duplicates maintaining order
        seen_models = []
        for gm in groq_models:
            if gm and gm not in seen_models:
                seen_models.append(gm)

        for current_model in seen_models:
            payload["model"] = current_model
            import time
            max_retries = 2
            for attempt in range(max_retries):
                try:
                    res = requests.post(url, headers=headers, json=payload, timeout=20)
                    if res.status_code == 429:
                        # If TPM limit, short sleep; if TPD limit, break to next fallback model
                        err_text = res.text.lower()
                        if "tokens per day" in err_text or "tpd" in err_text:
                            break # Try next fallback model immediately
                        if attempt < max_retries - 1:
                            time.sleep(2.5 * (attempt + 1))
                            continue
                    res.raise_for_status()
                    data = res.json()
                    choice = data["choices"][0]["message"]
                    
                    # Normalize tool calls structure if present
                    tool_calls = choice.get("tool_calls")
                    if tool_calls:
                        norm_tool_calls = []
                        for tc in tool_calls:
                            fn = tc.get("function", {})
                            args = fn.get("arguments", {})
                            if isinstance(args, str):
                                try:
                                    args = json.loads(args)
                                except Exception:
                                    pass
                            norm_tool_calls.append({
                                "id": tc.get("id", "call_1"),
                                "function": {
                                    "name": fn.get("name"),
                                    "arguments": args
                                }
                            })
                        choice["tool_calls"] = norm_tool_calls

                    return {"message": choice}
                except requests.exceptions.RequestException as e:
                    if hasattr(e, 'response') and e.response is not None and e.response.status_code == 429:
                        err_text = e.response.text.lower()
                        if "tokens per day" in err_text or "tpd" in err_text:
                            break # Fallback to next model
                        if attempt < max_retries - 1:
                            time.sleep(2.5 * (attempt + 1))
                            continue
                    pass # Try next model
        
        # If all Groq models exhausted, fallback to deterministic reply or Ollama

    # Local Ollama Execution
    url = f"{Config.OLLAMA_API_URL}/api/chat"
    candidate_models = [Config.OLLAMA_MODEL, "qwen3:14b", "qwen2.5:latest", "llama3.1:latest"]
    
    last_err = None
    for target_model in candidate_models:
        if not target_model:
            continue
        payload = {
            "model": target_model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": 350,       # Concise, snappy sales agent responses
                "num_ctx": 4096,          # Fast KV cache utilization
            },
        }
        if tools:
            payload["tools"] = tools
        if format:
            payload["format"] = format

        try:
            res = requests.post(url, json=payload, timeout=Config.OLLAMA_TIMEOUT_SECONDS)
            if res.status_code == 404 and "not found" in res.text.lower():
                continue # Try next locally available model while target is pulling
            res.raise_for_status()
            return res.json()
        except requests.exceptions.RequestException as e:
            last_err = e

    raise OllamaError(f"Ollama request failed on local server ({Config.OLLAMA_API_URL}): {last_err}") from last_err


def get_embedding(text: str, model: str = None) -> list[float]:
    """
    Generate dense vector embedding using local Ollama embedding endpoint (/api/embeddings).
    """
    candidate_embed_models = [model, getattr(Config, "OLLAMA_EMBED_MODEL", "bge-m3"), "bge-m3:latest", "nomic-embed-text:latest"]
    url = f"{Config.OLLAMA_API_URL}/api/embeddings"
    
    for candidate in candidate_embed_models:
        if not candidate:
            continue
        payload = {
            "model": candidate,
            "prompt": text
        }
        try:
            res = requests.post(url, json=payload, timeout=Config.OLLAMA_TIMEOUT_SECONDS)
            if res.status_code == 404 and "not found" in res.text.lower():
                continue
            res.raise_for_status()
            data = res.json()
            return data.get("embedding", [])
        except Exception:
            continue
    return []


import os
import re
import json
from groq import Groq
from .prompts import VALIDATE_PROMPT


CARD_RE = re.compile(r"\b(?:\d[ -]*?){13,16}\b")
CVV_RE = re.compile(r"\b\d{3,4}\b")


def pii_detect(text: str) -> bool:
    t = text.lower()
    if "card" in t and CARD_RE.search(text):
        return True
    if "cvv" in t and CVV_RE.search(text):
        return True
    return False


def llm_validate(ctx_docs, draft: str, model="llama3-8b-8192"):
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    prompt = VALIDATE_PROMPT.format(ctx="\n\n".join(ctx_docs), draft=draft)
    msg = [{"role": "user", "content": prompt}]
    
    out = client.chat.completions.create(
        model=model,
        messages=msg,
        temperature=0
    )
    
    txt = out.choices[0].message.content.strip()
    try:
        obj = json.loads(txt)
    except Exception:
        obj = {"is_valid": False, "reason": "Validator returned non-JSON"}
    
    if pii_detect(draft):
        obj["is_valid"] = False
        obj["reason"] = (obj.get("reason", "") + " | PII detected").strip()
    
    return obj

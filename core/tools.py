from langchain.tools import tool
from typing import List, Optional
from .rag import retrieve
from mail_io.imap_smtp import smtp_send
from utils import db


@tool
def rag_search(query: str, k: int = 4) -> List[str]:
    """Search the policy knowledge base for context relevant to `query`."""
    return retrieve(query, k=k)


@tool
def send_email(to: str, subject: str, body: str) -> str:
    """Send a plain-text email."""
    smtp_send(to_addr=to, subject=subject, body=body)
    return "sent"


@tool
def db_log_tool(email_id: int, event: str, payload: Optional[str] = None) -> str:
    """Write a log line for observability."""
    db.log(email_id, event, payload={"raw": payload} if payload else None)
    return "logged"

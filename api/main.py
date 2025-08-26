import os
import asyncio
from fastapi import FastAPI
from utils import db
from mail_io.imap_smtp import fetch_unread
from core.agent import app as agent_graph

api = FastAPI(title="Email Agent")
status = {"state": "idle"}


@api.on_event("startup")
async def start_poller():
    async def poll():
        while True:
            status["state"] = "polling"
            for uid, msg in fetch_unread(os.getenv("AGENT_LABEL")):
                subject = msg.get("Subject", "(no subject)")
                from_addr = msg.get("From")

                # Extract body (simple/plain cases)
                body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        ctype = part.get_content_type()
                        if ctype == "text/plain":
                            body = (part.get_payload(decode=True) or b"").decode(errors="ignore")
                            break
                else:
                    body = (msg.get_payload(decode=True) or b"").decode(errors="ignore")

                # Persist
                with db.get_conn() as c:
                    cur = c.cursor()
                    cur.execute(
                        """
                        INSERT IGNORE INTO emails(msg_id, from_addr, subject, body, status)
                        VALUES (%s, %s, %s, %s, 'new')
                        """,
                        (str(uid), from_addr, subject, body)
                    )
                    c.commit()
                    cur.execute("SELECT id FROM emails WHERE msg_id=%s", (str(uid),))
                    email_id = cur.fetchone()[0]
                    db.log(email_id, "INGESTED", payload={"from": from_addr, "subject": subject})

                # Run agentic graph
                out = agent_graph.invoke({
                    "email_id": email_id,
                    "sender": from_addr,
                    "subject": subject,
                    "email_text": body
                })

                db.log(email_id, "AGENT_OUTPUT", payload=out)

            status["state"] = "idle"
            await asyncio.sleep(10)  # avoid tight polling loop

    asyncio.create_task(poll())


@api.get("/status")
def get_status():
    return status


@api.post("/trigger-run")
def trigger_run():
    status["state"] = "manual"
    return {"ok": True}

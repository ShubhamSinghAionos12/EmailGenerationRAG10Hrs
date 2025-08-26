# Email Agent (Chroma + MySQL + LangGraph + Streamlit + FastAPI + Groq)


## What it does
- Polls email via **IMAP**.
- Runs an **agentic** LLM (Groq) using **LangGraph** + **tool calling** to decide actions.
- Uses **ChromaDB** for RAG over your policy docs.
- Sends replies via **SMTP** (or Gmail API, optional).
- Stores state/logs in **MySQL**.
- Shows live **Streamlit** dashboard (status, logs, escalations).


## Setup
1. Copy `.env.example` → `.env` and fill values.
2. `docker-compose up -d` to start MySQL.
3. Apply schema: run `storage/models.sql`.
4. Ingest your policy MD: `python storage/chroma_ingest.py airlines_policy.md`.
5. Install deps: `pip install -r requirements.txt`.
6. Start API: `uvicorn api.main:api --reload`.
7. Start UI: `streamlit run apps/streamlit_app.py`.


## Notes
- To switch to Gmail API sending, implement `mail_io/gmail_api.py` and call it from `core/tools.send_email` instead of SMTP.
- Guardrails are minimal; extend `core/guardrails.py` for stricter policy.
- To add more tools (e.g., ticketing, CRM), create new `@tool` functions and add to `TOOLS` in `core/agent.py`.
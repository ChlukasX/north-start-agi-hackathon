# app.py
# -----------------------------------------------------------
#  FastAPI wrapper around the `agent` from your previous code
# -----------------------------------------------------------
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Any, Dict
import os
from agent_pipeline import trigger_explore
# ---- import or paste your entire agent script here ----------

from dotenv import load_dotenv
load_dotenv()  # this reads .env and injects into os.environ

# 2. Configuration
DB_URL    = os.getenv(
    "DB_URL",
    "postgresql+psycopg2://devuser:devpassword@localhost:5433/devdb"
)
MODEL_STR = os.getenv("OPENAI_MODEL", "openai:gpt-4o")

# ------------------------------------------------------------
#  FastAPI setup
# ------------------------------------------------------------
app = FastAPI(title="Category Text‑to‑SQL Agent")

class AskRequest(BaseModel):
    message: str

class AskResponse(BaseModel):
    answer: str

@app.post("/ask", response_model=AskResponse)
def ask_endpoint(body: AskRequest):
    """
    Passes the user message straight to the LangChain agent and
    returns whatever the agent prints (markdown or code fences included).
    """
    try:
        ## 
        return AskResponse(answer="reply")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

class TriggerRequest(BaseModel):
    x: int
    y: int

class TriggerResponse(BaseModel):
    result: Any


@app.post("/trigger", response_model=TriggerResponse)
async def trigger_endpoint(body: TriggerRequest):
    """
    Calls `my_heavy_function` with the JSON payload and
    returns the result.  Handles all errors as HTTP 500.
    """
    try:
        output = trigger_explore
        return TriggerResponse(result=output)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)

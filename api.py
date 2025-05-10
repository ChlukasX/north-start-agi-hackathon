# app.py
# -----------------------------------------------------------
#  FastAPI wrapper around the `agent` from your previous code
# -----------------------------------------------------------
from langchain_google_genai import ChatGoogleGenerativeAI
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Any, Dict
from sqlalchemy import create_engine, text
import os
from agent_pipeline import trigger_explore
# ---- import or paste your entire agent script here ----------

from dotenv import load_dotenv

from chatbot_service.agent_factory import ChatSession, build_agent
from config import CAT_COL, DB_URL, TABLE
load_dotenv()  # this reads .env and injects into os.environ


gemini = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",
    temperature=0.0
)


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


sessions: Dict[str, "AgentExecutor"] = {}

class ChatReq(BaseModel):
    session_id: str
    message: str

class ChatRes(BaseModel):
    answer: str

@app.post("/chat", response_model=ChatRes)
def chat(body: ChatReq):
    try:
        if body.session_id not in sessions:
            # build underlying LangChain agent once
            lc_agent = build_agent(DB_URL, TABLE, CAT_COL, gemini)
            sessions[body.session_id] = ChatSession(
                lc_agent,                # the agent you already wrote
                create_engine(DB_URL),   # for listing categories
                TABLE,
                CAT_COL,
                llm=gemini
            )
        reply = sessions[body.session_id].send(body.message)
        
        print(reply)
        return ChatRes(answer=reply)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    
if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)

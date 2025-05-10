import json, re
import pandas as pd
from typing import Dict
from sqlalchemy import create_engine, text
from langchain.tools import Tool
from langchain.memory import ConversationBufferMemory
from langchain.chains import create_sql_query_chain
from langchain.agents import initialize_agent, AgentType


from chatbot_service.helpers import (
    build_category_schema,
    summarize_category_with_llm,
    json_safe,
)

# DB / table names are injected by api.py when it calls build_agent()
def build_agent(DB_URL: str, TABLE: str, CAT_COL: str, llm) -> "AgentExecutor":

    sql_db  = create_engine(DB_URL)
    sql_lc  = create_sql_query_chain(llm, sql_db)

    state: Dict[str, object] = {"cat": None, "schema": {}}
    memory = ConversationBufferMemory(return_messages=True)

    # -------- choose_category tool --------------------------------
    def choose(cat: str) -> str:
        with sql_db.connect() as conn:
            df = pd.read_sql(text(f"SELECT * FROM {TABLE} WHERE {CAT_COL}=:c"),
                             conn, params={"c": cat})
        if df.empty:
            return f"❌ Category '{cat}' not found."
        state["cat"]    = cat
        state["schema"] = build_category_schema(df, cat)
        return summarize_category_with_llm(df, cat, llm)["narrative"]

    choose_tool = Tool(
        name="choose_category",
        func=choose,
        description="Pick a category and get a markdown overview."
    )

    # -------- ask_sql tool ---------------------------------------
    def ask(q: str) -> str:
        cat = state["cat"]
        if not cat:
            return "❗ Choose a category first with choose_category(<name>)."
        schema_json = json.dumps(state["schema"], default=json_safe)
        prompt = f"""{q}

TABLE STRUCTURE:
{schema_json}

Rules:
• Use only `{TABLE}`.
• Filter by {CAT_COL} = '{cat}'.
"""
        raw_sql = sql_lc.run(prompt)
        final_sql = (
            raw_sql.rstrip(";") + f" WHERE {CAT_COL}='{cat}';"
            if "WHERE" not in raw_sql.upper()
            else re.sub(r"(?i)WHERE", f"WHERE {CAT_COL}='{cat}' AND ", raw_sql, 1)
        )
        with sql_db.connect() as conn:
            rows = conn.execute(text(final_sql)).fetchmany(25)
        return json.dumps([dict(r) for r in rows], indent=2, default=json_safe)

    ask_tool = Tool(
        name="ask_sql",
        func=ask,
        description="Ask questions about the currently‑selected category."
    )

    return initialize_agent(
        tools=[choose_tool, ask_tool],
        llm=llm,
        agent=AgentType.OPENAI_FUNCTIONS,
        memory=memory,
        verbose=False,
    )


# ------------------------------------------------------------------
#  SessionManager: front‑door that enforces {hi → pick category}
# ------------------------------------------------------------------
from sqlalchemy import text
from sqlalchemy import text
import pandas as pd

from sqlalchemy import text
class ChatSession:
    def __init__(self, agent, sql_db, table: str, cat_col: str, llm):
        self.agent           = agent
        self.sql_db          = sql_db
        self.table           = table
        self.cat_col         = cat_col
        self.llm             = llm
        self.menu_shown      = False
        self.category_chosen = False

    def _category_menu(self) -> str:
        rows = self.sql_db.connect().execute(
            text(f"SELECT DISTINCT {self.cat_col} FROM {self.table} ORDER BY 1")
        )
        cats = [r[0] for r in rows]
        bullets = "\n".join(f"- {c}" for c in cats)
        return (
            "👋 Hi!\n\nHere are the available categories:\n"
            f"{bullets}\n\n"
            "➡️ Please reply with **one** of the names above."
        )

    def send(self, user_msg: str) -> str:
        # 1) First turn: show the menu
        if not self.menu_shown:
            self.menu_shown = True
            return self._category_menu()

        # 2) Second turn: treat as the category choice
        if not self.category_chosen:
            self.category_chosen = True

            # a) Load the slice
            df_cat = pd.read_sql(
                text(f"SELECT * FROM {self.table} WHERE {self.cat_col} = :c"),
                self.sql_db,
                params={"c": user_msg}
            )
            if df_cat.empty:
                return f"❌ Category '{user_msg}' not found. Try again."

            # b) Build schema & narrative
            schema    = build_category_schema(df_cat, user_msg, self.cat_col)
            narrative = summarize_category_with_llm(df_cat, user_msg, self.llm)["narrative"]

            # c) Store state for the ask_sql tool
            choose_tool = next(t for t in self.agent.tools if t.name == "choose_category")
            choose_tool.func.__self__.state["cat"]    = user_msg
            choose_tool.func.__self__.state["schema"] = schema

            # **Return only the narrative** — no further agent.run() here!
            return narrative

        # 3) All later turns: normal SQL Q&A via the agent
        return self.agent.run(user_msg)

import os

DB_URL  = os.getenv(
    "DB_URL",
    "postgresql+psycopg2://devuser:devpassword@localhost:5433/devdb"
)

TABLE   = "nodes_categorized"
CAT_COL = "generated_category"
MODEL_STR = os.getenv("OPENAI_MODEL", "openai:gpt-4o")

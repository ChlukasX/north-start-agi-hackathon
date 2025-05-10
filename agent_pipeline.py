from api import DB_URL, MODEL_STR
from langchain_google_genai import ChatGoogleGenerativeAI
import pandas as pd
from sqlalchemy import create_engine

from langchain.tools import Tool
from langchain.chat_models import init_chat_model
from langgraph.prebuilt import create_react_agent

from typing import List
import json, pandas as pd, numpy as np
from sklearn.preprocessing import normalize
import hdbscan
from langchain_google_genai import GoogleGenerativeAIEmbeddings

from __future__ import annotations
from typing import List, Dict, Any
import json
import pandas as pd
from langchain_google_genai import ChatGoogleGenerativeAI  # Gemini chat

import os
import pandas as pd
from typing import Optional, Dict
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import (
    BIGINT, DOUBLE_PRECISION, TEXT, BOOLEAN, JSONB, ARRAY
)

import os, json
from typing import Dict, List

import pandas as pd
from sqlalchemy import create_engine
from langchain.sql_database import SQLDatabase
from langchain.tools import Tool


gemini = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",
    temperature=0.0
)



TABLE    = "nodes_categorized"
CAT_COL  = "generated_category"

llm      = gemini
db       = SQLDatabase.from_uri(DB_URL)


classification_columns: list[str] = []

# 4. Detection logic: read table, return column names

def detect_classification_columns(table_name: str) -> list[str]:
    """
    Load `table_name` into a DataFrame and return a list of columns
    that are not IDs (col=='id' or ending '_id') and not numeric.
    Also updates global `classification_columns`.
    """
    global classification_columns
    engine = create_engine(DB_URL)
    df = pd.read_sql_table(table_name, engine)
    cols = []
    for col in df.columns:
        lc = col.lower()
        if lc == "id" or lc.endswith("_id"):
            continue
        if pd.api.types.is_numeric_dtype(df[col]):
            continue
        cols.append(col)
    classification_columns = cols
    return cols



def get_records(sample_size=1000, table_name="nodes"):
    engine = create_engine(DB_URL)
    q = f"SELECT * FROM {table_name} LIMIT {sample_size}"
    df = pd.read_sql(q, engine)
    return df
    

def cluster_hdbscan_gemini(
    df: pd.DataFrame,
    columns: List[str],
    min_cluster_size: int = 15,
    min_samples: int | None = None,
    metric: str = "euclidean",
    model_name: str = "models/embedding-001"   # Gemini embedding model
) -> pd.DataFrame:


    # ── 1) Row‑text serialization (flatten JSON) ───────────────────────────
    def _ser(v):
        if isinstance(v, str):
            try: v = json.loads(v)
            except: return v
        if isinstance(v, dict):
            return "{" + ", ".join(
                f"{k}={json.dumps(v[k], sort_keys=True)}" for k in sorted(v)
            ) + "}"
        return str(v)

    texts = (
        df[columns]
        .applymap(_ser)
        .agg(" | ".join, axis=1)
        .tolist()
    )

    # ── 2) Gemini embeddings  ──────────────────────────────────────────────
    embedder = GoogleGenerativeAIEmbeddings(
        model=model_name,
        task_type="retrieval_document"     # recommended for doc‑level embeddings
    )
    embeddings = np.array(embedder.embed_documents(texts))
    embeddings = normalize(embeddings)    # so 'euclidean' ≈ cosine

    # ── 3) HDBSCAN clustering ──────────────────────────────────────────────
    clusterer = hdbscan.HDBSCAN(
        min_cluster_size=min_cluster_size,
        min_samples=min_samples,
        metric=metric,
        prediction_data=False,
    ).fit(embeddings)

    # ── 4) Attach labels & return ──────────────────────────────────────────
    df_out = df.copy()
    df_out["cluster_label"] = clusterer.labels_   # ‑1 = noise
    return df_out

# ---------------- helper to stringify selected cols ----------------
def _row_text(row: pd.Series, cols: List[str]) -> str:
    parts = []
    for c in cols:
        val = row[c]
        if isinstance(val, dict):
            val = json.dumps(val, sort_keys=True)
        parts.append(f"{c}={val}")
    return " | ".join(parts)

# ---------------- main routine -------------------------------------
def name_clusters_via_llm(
    df: pd.DataFrame,
    cluster_col: str,
    text_cols: List[str],
    llm=None,
    sample_per_cluster: int = 1_000,
) -> tuple[pd.DataFrame, Dict[int, str]]:
    """
    Adds a 'generated_category' column by LLM‑naming each cluster.

    Returns
    -------
    df_out : DataFrame   (copy with new column)
    mapping : {cluster_label: generated_name}
    """
    llm = gemini
    mapping: Dict[int, str] = {}

    for label, sub in df.groupby(cluster_col):
        if label == -1:               # treat noise separately
            mapping[label] = "noise"
            continue

        # take up to N rows for prompt
        sub_sample = sub.head(sample_per_cluster)

        examples = "\n".join(
            _row_text(r, text_cols) for _, r in sub_sample.iterrows()
        )

        prompt = f"""
You are assigned to invent a concise, human‑readable category name
for a cluster of data records.  Below are example rows from one cluster;
each line shows selected fields in "key=value" format.

Example rows:
{examples}

Provide ONE short category name (2–4 words max) that describes these rows.
Reply with ONLY the name, no bullet points, no extra text.
"""
        category = llm.predict(prompt).strip().strip('"').strip("'")
        mapping[label] = category or "unknown"

    # attach back
    df_out = df.copy()
    df_out["generated_category"] = df_out[cluster_col].map(mapping).fillna("unknown")
    return df_out, mapping


# --------------------------- helpers ---------------------------------
def _looks_like_json(val) -> bool:
    """True if val is a dict or a JSON‑parsable string."""
    if isinstance(val, dict):
        return True
    if isinstance(val, str):
        try:
            obj = json.loads(val)
            return isinstance(obj, dict)
        except Exception:
            return False
    return False

def _auto_json_columns(df: pd.DataFrame, sample: int = 50) -> List[str]:
    """Return column names whose sample values are mostly dicts / JSON strings."""
    json_cols = []
    for col in df.columns:
        sample_vals = df[col].dropna().head(sample)
        if sample_vals.empty:
            continue
        pct_json = sample_vals.map(_looks_like_json).mean()
        if pct_json > 0.5:          # >50 % of sampled rows look like JSON
            json_cols.append(col)
    return json_cols

def _flatten_json_series(s: pd.Series, prefix: str, sep="_") -> pd.DataFrame:
    """Recursively flatten a JSON/dict series into scalar columns."""
    def flat(v, px=""):
        if isinstance(v, str):
            try: v = json.loads(v)
            except: return {px[:-1]: v}
        if isinstance(v, dict):
            out = {}
            for k, val in v.items():
                out.update(flat(val, f"{px}{k}{sep}"))
            return out
        return {px[:-1]: v}
    return pd.json_normalize(s.map(lambda x: flat(x, f"{prefix}{sep}")))

# ------------------- summarizer with auto‑detection -------------------
def summarize_category_with_llm(
    df: pd.DataFrame,
    category: str,
    llm,
    id_col: str                = "id",
    auto_sample: int           = 50         # rows per column to test for JSON
) -> Dict[str, Any]:
    """
    1) Filters df to `category`
    2) Auto‑detects JSON‑like columns and flattens them
    3) Computes per‑column stats
    4) Returns stats + LLM narrative
    """
    sub = df[df["generated_category"] == category].copy()
    if sub.empty:
        return {"summary": {}, "narrative": f"No records for '{category}'."}

    # 1⃣  auto‑detect and flatten all JSON‑ish columns
    json_cols = _auto_json_columns(sub, sample=auto_sample)
    flat_parts = [sub]
    for jc in json_cols:
        flat_parts.append(_flatten_json_series(sub[jc], jc))
    wide = pd.concat(flat_parts, axis=1).drop(columns=json_cols)

    # 2⃣  quick type-aware stats
    summary = {"category": category, "n_rows": len(wide), "columns": {}}
    for col in wide.columns:
        if col in ("assigned_category", "geometry"):
            continue
        ser = wide[col].dropna()
        if ser.empty:
            summary["columns"][col] = {"all_null": True}
            continue
        if ser.dtype.kind in "if":
            summary["columns"][col] = {
                "type": "numeric",
                "min": ser.min(),
                "max": ser.max(),
                "mean": ser.mean(),
                "p50": ser.quantile(.5),
                "p95": ser.quantile(.95),
            }
        elif ser.dtype == bool or ser.isin([0, 1]).all():
            summary["columns"][col] = {
                "type": "boolean",
                "pct_true": float(ser.mean()),
            }
        else:
            top = ser.value_counts().head(5)
            summary["columns"][col] = {
                "type": "categorical",
                "distinct": int(ser.nunique()),
                "top_values": top.to_dict(),
            }

    # 3⃣  Ask LLM for narrative
    prompt = f"""
You are a data analyst. Summarize these statistics for the category "{category}"
in 3‑4 sentences, highlighting notable patterns in markdown format.

Stats JSON:
{json.dumps(summary, indent=2)}
"""
    narrative = llm.predict(prompt).strip()

    return {"summary": summary, "narrative": narrative}


def _infer_pg_dtype(series: pd.Series):
    if pd.api.types.is_integer_dtype(series):
        return BIGINT 
    if pd.api.types.is_float_dtype(series):
        return DOUBLE_PRECISION
    if pd.api.types.is_bool_dtype(series):
        return BOOLEAN
    if pd.api.types.is_object_dtype(series):
        # crude checks for JSON or list
        sample = series.dropna().head(1)
        if not sample.empty and isinstance(sample.iloc[0], (dict, list)):
            return JSONB if isinstance(sample.iloc[0], dict) else ARRAY(TEXT)
        return TEXT
    return TEXT  # fallback


# ─────────────────────────────────────────────────────────
# main writer
# ─────────────────────────────────────────────────────────
def write_df_to_postgres(
    df: pd.DataFrame,
    table_name: str,
    db_url: str = DB_URL,
    schema: Optional[str] = None,
    if_exists: str = "replace",   # "append" or "replace"
    chunksize: int = 10_000
) -> None:
    engine = create_engine(db_url)

    # Build dtype mapping
    dtype_map: Dict[str, Any] = {
        col: _infer_pg_dtype(df[col]) for col in df.columns
    }

    df.to_sql(
        name=table_name,
        con=engine,
        schema=schema,
        if_exists=if_exists,
        index=False,
        dtype=dtype_map,
        method="multi",
        chunksize=chunksize
    )
    print(f"✅  Wrote {len(df)} rows → {schema+'.' if schema else ''}{table_name}")



def trigger_explore():
    detect_tool = Tool(
        name="detect_classification_columns",
        func=detect_classification_columns,
        description=(
            "Given a Postgres table name, return non-ID, non-numeric columns "
            "for classification and store them in `classification_columns`."
        ),
    )

    # 6. Initialize LLM for tool-binding
    tt_model = init_chat_model(MODEL_STR, temperature=0)

    # 7. Create the React agent
    agent = create_react_agent(
        model=tt_model,
        tools=[detect_tool],
        prompt=(
            "You are an agent that receives a SQL table name, detects which columns "
            "are useful for classification, and stores them in the global variable."
        ),
    )
    
    table_name = "nodes"
    response = agent.invoke({"messages": [{"role": "user", "content": table_name}]})
    print("Detected classification columns:", classification_columns)
    sample_size = 1000
    
    df = get_records(sample_size=sample_size)
    clustered = cluster_hdbscan_gemini(
        df,
        columns=classification_columns,      # columns to embed
        min_cluster_size=20
    )
    
    df_named, cluster_to_name = name_clusters_via_llm(
        clustered,
        cluster_col="cluster_label",
        text_cols=classification_columns,       # columns you clustered on
        sample_per_cluster=1000           # cap rows per cluster sent to LLM
    )
    new_table_name = "nodes_categorized"

    write_df_to_postgres(df_named, table_name=new_table_name)
    
    

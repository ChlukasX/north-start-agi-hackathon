import json, pandas as pd, numpy as np
from typing import Any, Dict, List


import json

def find_non_serializable(obj, path="root"):
    """
    Recursively walks `obj` (which may be a dict/list/primitive)
    and returns a list of paths where json.dumps(...) fails.
    """
    try:
        json.dumps(obj)
        return []
    except TypeError:
        # if it's a dict, recurse into its values
        if isinstance(obj, dict):
            errs = []
            for k, v in obj.items():
                errs += find_non_serializable(v, f"{path}.{k}")
            return errs or [path]
        # if it's a list/tuple, recurse into its items
        if isinstance(obj, (list, tuple)):
            errs = []
            for i, v in enumerate(obj):
                errs += find_non_serializable(v, f"{path}[{i}]")
            return errs or [path]
        # otherwise it's a leaf that json can’t handle
        return [path]

# ────────────────────────── JSON helpers ──────────────────────────


def _auto_json_cols(df: pd.DataFrame, sample: int = 50) -> List[str]:
    return [
        c for c in df.columns
        if not df[c].dropna().empty
        and df[c].dropna().head(sample).map(_looks_like_json).mean() > 0.5
    ]

def _flatten_series(s: pd.Series, prefix: str, sep=".") -> pd.DataFrame:
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



# ───────────────────── safe JSON serializer ──────────────────────
def json_safe(o):
    if isinstance(o, np.generic):
        return o.item()
    return str(o)




# ─────────────────── build_category_schema() ─────────────────────
def build_category_schema(
    df: pd.DataFrame,
    category: str,
    cat_col: str = "generated_category",
    sample_rows: int = 10_000
) -> Dict[str, str]:
    sub = df[df[cat_col] == category]
    if sub.empty:
        return {}
    if len(sub) > sample_rows:
        sub = sub.sample(sample_rows, random_state=42)

    json_cols = _auto_json_cols(sub)
    parts = [sub]
    for jc in json_cols:
        parts.append(_flatten_series(sub[jc], jc))
    wide = pd.concat(parts, axis=1).drop(columns=json_cols)

    def _simple_dtype(s: pd.Series) -> str:
        if pd.api.types.is_integer_dtype(s): return "integer"
        if pd.api.types.is_float_dtype(s):   return "float"
        if pd.api.types.is_bool_dtype(s):    return "boolean"
        return "text"

    return {col: _simple_dtype(wide[col].dropna()) for col in wide.columns}

# ─────────────────── summarize_category_with_llm() ───────────────
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
    bad = find_non_serializable(summary)
    if bad:
        print("⚠️  Non-serializable paths in summary:", bad)
        
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
# Data Scavs — DataCrawler
## Agentic application that makes sense of dirty data
## Authors: 
- Lukas Nackmayr
- Ngoc Duy Lam
- Mykhailo Kruts


DataCrawler is an opinionated, modular micro‑service that extracts order from chaos. It ingests ad‑hoc notes, log files, e‑mails, CSV dumps, PDFs, or any other semi‑structured blob you point at it and returns a well‑defined, query‑ready dataset. Under the hood the engine applies semantic‑similarity clustering, entity‑resolution heuristics, and schema‑inference models to surface the latent structure that was always hiding in your information.

Why another data wrangler?
Teams still burn hours writing one‑off scripts every time a new spreadsheet lands in their inbox. DataCrawler eliminates that toil by letting agents do the heavy lifting. Each agent is a self‑contained skill—text normalisation, unit conversion, label propagation, summarisation—and can be chained into domain‑specific pipelines without touching the core. Analysts get clean tables in minutes, not days, and engineers can iterate on models instead of debugging parsers.

Multi‑agent fabric, built for the future
While the current release focuses on generating summaries, statistical snapshots, and actionable insights, the architecture is intentionally forward‑looking. The same message bus that orchestrates today’s preprocessing agents can host tomorrow’s reasoning agents, retrieval‑augmented QA bots, or reinforcement‑learning controllers. Because every artefact—from raw payload to final record—is stored in a version‑controlled object store, new agents can replay historical jobs, learn from past decisions, and collaborate with their peers without re‑crawling source data. Think of DataCrawler as the substrate on which a colony of intelligent workers can cooperate: one agent classifies, another annotates entities, a third drafts a natural‑language report, and a fourth triggers downstream workflows such as BI dashboards or alerting systems. Adding a new capability is as simple as dropping a Python module into the agents/ folder.

Backstory:


Run with:
`fastapi run main.py`

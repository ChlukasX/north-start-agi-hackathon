import os
import logging
from typing import List
import pandas as pd
from sqlalchemy import create_engine
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.tools import Tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent
from .base_agent import BaseAgent

logger = logging.getLogger(__name__)


# 1. Load environment (for OPENAI_API_KEY, optional DB_URL override)
# Note: dotenv is handled in enviroment_setup.py, no need to repeat here
# 2. Configuration
DB_URL = os.getenv(
    "DB_URL", "postgresql+psycopg2://devuser:devpassword@localhost:5433/devdb"
)
MODEL_STR = os.getenv("OPENAI_MODEL", "openai:gpt-4o")


# 3. Global storage variable for detected columns
classification_columns: List[str] = []


# 4. Detection logic: read table, return column names
def detect_classification_columns(table_name: str) -> List[str]:
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


def get_records(table_name: str, sample_size: int = 1000) -> pd.DataFrame:
    """
    Load `table_name` into a DataFrame and return a sample of the records.

    Args:
        table_name (str): The name of the table to load.
        sample_size (int, optional): The maximum number of rows to sample. Defaults to 1000.

    Returns:
        pd.DataFrame: A DataFrame containing the sampled records.  If the table
                      has fewer than `sample_size` rows, all rows are returned.
    """
    engine = create_engine(DB_URL)
    df = pd.read_sql_table(table_name, engine)
    if len(df) > sample_size:
        return df.sample(sample_size, random_state=42)  # Consistent sampling
    return df


class DataAccessAgent(BaseAgent):
    def __init__(self):
        super().__init__()
        # Validate Google API key
        self.api_key = os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            logger.warning("DataAccessAgent initialized without GOOGLE_API_KEY")

    def access_data(self, query: str):
        """Access data from a database or API."""
        # This is a placeholder implementation
        # In a real-world scenario, this method would interact with your database
        return f"Retrieved data for query: {query}"

    def _get_table_columns(self, table_name: str) -> List[str]:
        """Tool function to get classification columns."""
        return detect_classification_columns(table_name)

    def _get_table_records(self, table_name: str, sample_size: int = 1000) -> str:
        """Tool function to get records from a table."""
        df = get_records(table_name, sample_size)
        return df.to_string()  # Convert to string for LLM consumption

    def get_tools(self):
        tools = super().get_tools()

        access_data_tool = Tool(
            name="AccessData",
            description="Access data from a database or API.",
            func=self.access_data,
        )
        get_columns_tool = Tool(
            name="GetTableColumns",
            description="Get columns suitable for classification from a table.",
            func=self._get_table_columns,
        )

        get_records_tool = Tool(
            name="GetTableRecords",
            description="Get records from a table.",
            func=self._get_table_records,
        )

        tools.extend(
            [access_data_tool, get_columns_tool, get_records_tool]
        )  # Add new tools
        return tools

    def llm(self, query):
        if not self.api_key:
            logger.error("Cannot run DataAccessAgent: GOOGLE_API_KEY not set")
            raise ValueError("GOOGLE_API_KEY environment variable is not set")

        memory = MemorySaver()

        system_message = SystemMessage(
            content="You are a helpful assistant specialized in data access."
        )

        try:
            # Initialize the LLM with the API key
            llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash")

            agent_executor = create_react_agent(
                llm,
                self.get_tools(),
                checkpointer=memory,
            )

            config = {"configurable": {"thread_id": "data_access_agent"}}

            return agent_executor.stream(
                {"messages": [system_message, HumanMessage(content=query)]},
                config,
                stream_mode="values",
            )
        except Exception as e:
            logger.error(f"Error in DataAccessAgent.llm: {str(e)}")
            raise

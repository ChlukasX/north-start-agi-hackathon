import os
import logging
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.tools import Tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent
from .base_agent import BaseAgent

logger = logging.getLogger(__name__)


class DataAccessAgent(BaseAgent):
    def __init__(self):
        super().__init__()
        # Validate Google API key
        self.api_key = os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            logger.warning("DataAccessAgent initialized without GOOGLE_API_KEY")

    def access_data(self, query):
        """Access data from a database or API."""
        # This is a placeholder implementation
        # In a real-world scenario, this method would interact with your database
        return f"Retrieved data for query: {query}"

    def get_tools(self):
        _ = super().get_tools()

        access_data_tool = Tool(
            name="AccessData",
            description="Access data from a database or API.",
            func=self.access_data,
        )

        return [
            access_data_tool,
        ]

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

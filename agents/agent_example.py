import os
import logging
from langchain_core.tools import Tool
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent
from .base_agent import BaseAgent

logger = logging.getLogger(__name__)


class ExampleAgent(BaseAgent):
    def __init__(self):
        super().__init__()
        # Validate OpenAI API key
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            logger.warning("ExampleAgent initialized without OPENAI_API_KEY")

    def hello(self, query):
        """Tool to say hello to the user."""
        return f"Hello, you asked me the fun question: {query}"

    def answer_question(self, query):
        """Tool to provide a simple answer to a question."""
        return f"The answer to '{query}' is: This is a simple response from the answer_question tool."

    def get_tools(self):
        """Return all tools this agent can use."""
        _ = super().get_tools()

        hello_tool = Tool(
            name="Hello",
            description="Say hello to the user.",
            func=self.hello,
        )

        answer_tool = Tool(
            name="AnswerQuestion",
            description="Provide a simple answer to a user's question.",
            func=self.answer_question,
        )

        return [hello_tool, answer_tool]

    def llm(self, query):
        if not self.api_key:
            logger.error("Cannot run ExampleAgent: OPENAI_API_KEY not set")
            raise ValueError("OPENAI_API_KEY environment variable is not set")

        memory = MemorySaver()

        # Create a system message for the LLM
        system_message = SystemMessage(content="You are a helpful assistant.")

        try:
            # Initialize the LLM with the API key
            llm = ChatOpenAI()

            agent_executor = create_react_agent(
                llm,
                self.get_tools(),
                checkpointer=memory,
            )

            config = {"configurable": {"thread_id": "example_agent"}}

            return agent_executor.stream(
                {"messages": [system_message, HumanMessage(content=query)]},
                config,
                stream_mode="values",
            )
        except Exception as e:
            logger.error(f"Error in ExampleAgent.llm: {str(e)}")
            raise

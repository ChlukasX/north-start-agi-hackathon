from langchain_core.messages import SystemMessage
from langchain_core.tools import Tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent
from agents.base_agent import BaseAgent


class DataAccessAgent(BaseAgent):
    def __init__(self):
        super().__init__()

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
        memory = MemorySaver()

        system_message = SystemMessage(content="You are a helpful assistant.")

        # Initialize the LLM
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

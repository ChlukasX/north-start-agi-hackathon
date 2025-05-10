from langchain_openai import ChatOpenAI
from base_agent import BaseAgent
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent


class ExampleAgent(BaseAgent):
    def __init__(self):
        super().__init__()

    def get_tools(self):
        base_tools = super().get_tools()

        # Make more tools from based tools specific to the agent

    def llm(self, query):
        memory = MemorySaver()

        # Create a system message for the LLM
        system_message = SystemMessage(content="You are a helpful assistant.")

        # Initialize the LLM
        llm = ChatOpenAI()

        agent_executor = create_react_agent(
            llm,
            self.get_tools(),
            checkpoint=memory,
        )

        config = {"configurable": {"thread_id": "example_agent"}}

        return agent_executor.stream(
            {"messages": [system_message, HumanMessage(content=query)]},
            config,
            stream_mode="values",
        )

    def llm_run(self, query):
        for step in self.llm(query):
            step["messages"][-1].pretty_print()

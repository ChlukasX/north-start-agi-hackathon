from langchain_core.tools import Tool
from langchain_openai import ChatOpenAI
from .base_agent import BaseAgent
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent


class ExampleAgent(BaseAgent):
    def __init__(self):
        super().__init__()

    def hello(self, query):
        return f"Hello, you asked me the fun question: {query}"

    def answer_question(self, query):
        """Tool to provide a simple answer to a question."""
        return f"The answer to '{query}' is: This is a simple response from the answer_question tool."

    def get_tools(self):
        """Return all tools this agent can use."""
        base_tools = super().get_tools()

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

        if isinstance(base_tools, list):
            return base_tools + [hello_tool, answer_tool]
        else:
            return [base_tools, hello_tool, answer_tool]

    def llm(self, query):
        memory = MemorySaver()

        # Create a system message for the LLM
        system_message = SystemMessage(content="You are a helpful assistant.")

        # Initialize the LLM
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

    def llm_run(self, query):
        for step in self.llm(query):
            step["messages"][-1].pretty_print()

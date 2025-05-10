from abc import ABC, abstractmethod


class BaseAgent(ABC):
    def __init__(self) -> None:
        self._initialize_environment()

    def _initialize_environment(self):
        """Initialize any environment variables or configurations needed for the agent."""
        pass

    @abstractmethod
    def get_tools(self):
        """
        Return a list of tools this agent can use.
        This method should be implemented by subclasses.
        """
        return []

    @abstractmethod
    def llm(self, query):
        """
        Process a query using this agent's LLM.
        This method should be implemented by subclasses.

        Args:
            query: The user's query as a string

        Returns:
            The response from the LLM
        """
        pass

    def llm_run(self, query):
        """
        Run the LLM agent and print each step's messages.

        Args:
            query: The user's query as a string
        """
        for step in self.llm(query):
            if "messages" in step and len(step["messages"]) > 0:
                step["messages"][-1].pretty_print()

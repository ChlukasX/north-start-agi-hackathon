from abc import ABC, abstractmethod


class BaseAgent(ABC):
    def __init__(self) -> None:
        self._initialize_enviroment()

    def _initialize_enviroment(self):
        pass

    @abstractmethod
    def get_tools(self):
        pass

    def llm_agent(self, query):
        pass

    def llm_agent_run(self, query):
        for step in self.llm_agent(query):
            step["messages"][-1].pretty_print()

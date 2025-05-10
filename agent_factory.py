from agents import ExampleAgent, DataAccessAgent


class AgentFactory:
    @staticmethod
    def create_agent(agent_type):
        if agent_type.lower == "example":
            return ExampleAgent
        elif agent_type.lower() == "data access":
            return DataAccessAgent
        else:
            return ValueError(f"Unknown agent type: {agent_type}")

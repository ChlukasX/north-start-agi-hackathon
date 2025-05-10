from agents import ExampleAgent


class AgentFactory:
    @staticmethod
    def create_agent(agent_type):
        if agent_type.lower == "example":
            return ExampleAgent
        else:
            return ValueError(f"Unknown agent type: {agent_type}")

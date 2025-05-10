from base_agent import BaseAgent


class ExampleAgent(BaseAgent):
    def __init__(self):
        super().__init__()

        self._initialize_maps_api()

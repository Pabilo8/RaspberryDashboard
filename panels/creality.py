# panels/creality.py
from panels.base_panel import BasePanel


class CrealityPanel(BasePanel):
    def __init__(self):
        super().__init__('creality', '/creality')

    def get_data(self):
        return {
            'model_name': "device",
            'done': 5,
            'remaining': 13,
            'progress': round(5.0 / (5 + 13), 1)
        }

    def set_config(self, data):
        pass

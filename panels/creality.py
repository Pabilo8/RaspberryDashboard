from flask import Response, stream_with_context
from panels.base_panel import BasePanel, ActivityState
import requests


class CrealityPanel(BasePanel):
    def __init__(self):
        super().__init__('creality', '/creality')
        self.name = "Ender 3"
        self.ip = None
        self.state = ActivityState.OFF

    def get_data(self):
        if not self.ip:
            self.log("Printer IP address not set in configuration")
            return {
                'model_name': "Unknown",
                'done': 0,
                'remaining': 0,
                'progress': 0.0,
                'temperatures': {}
            }

        url = f'http://{self.ip}:7125/printer/objects/query'
        payload = {
            "objects": {
                "print_stats": ["state", "message", "filename", "total_duration", "print_duration"],
                "heater_bed": ["temperature", "target"],
                "extruder": ["temperature", "target"]
            }
        }

        try:
            response = requests.post(url, json=payload, timeout=0.5)
            response.raise_for_status()
            data = response.json().get('result', {}).get('status', {})
            self.log(str(data))

            progress = data.get('print_stats', {}).get('print_duration', 0.0)
            remaining = data.get('print_stats', {}).get('total_duration', 0.0)

            self.map_moonraker_state_to_activity_state(data.get('print_stats', {}).get('state', 'off'))
            state_message = data.get('print_stats', {}).get('message', '')
            state_filename = data.get('print_stats', {}).get('filename', '')
            temperatures = data.get('temperatures', {})

            return {
                'model_name': self.name,
                'done': self.format_time(progress),
                'remaining': self.format_time(remaining),
                'progress': round(progress / remaining * 100, 0) if remaining > 0 else 0,
                'state': self.state.value,
                'state_message': state_message,
                'state_filename': state_filename,
                'temperatures': temperatures
            }
        except requests.RequestException as e:
            self.log(f"Error: {e}")
            return {
                'model_name': self.name,
                'done': 0,
                'remaining': 0,
                'progress': 0.0,
                'state': ActivityState.OFF.value,
                'state_message': '',
                'state_filename': '',
                'temperatures': {}
            }

    def set_config(self, data):
        self.ip = data.get('ip')
        self.name = data.get('name')
        self.bp.add_url_rule('/webcam', 'webcam', self.webcam_stream, methods=['GET'])

    def format_time(self, seconds):
        intervals = (
            ('weeks', 604800),
            ('days', 86400),
            ('hours', 3600),
            ('minutes', 60),
            ('seconds', 1),
        )
        result = []
        for name, count in intervals:
            value = seconds // count
            if value:
                seconds -= value * count
                result.append(f"{value} {name}")
        return ', '.join(result)

    def map_moonraker_state_to_activity_state(self, moonraker_state: str):
        state_mapping = {
            'printing': ActivityState.WORKING,
            'paused': ActivityState.IDLE,
            'complete': ActivityState.COMPLETE,
            'error': ActivityState.ERROR,
            'standby': ActivityState.IDLE,
            'off': ActivityState.OFF,
            'on': ActivityState.ON
        }
        # Default to OFF if state is not recognized
        self.state = state_mapping.get(moonraker_state, ActivityState.OFF)
        return self.state

    def webcam_stream(self):
        if not self.ip:
            return "Webcam Stream: Printer IP address not set in configuration", 500

        url = f'http://{self.ip}:8080/?action=stream'
        try:
            response = requests.get(url, stream=True, timeout=0.5)
            response.raise_for_status()
            return Response(stream_with_context(response.iter_content(chunk_size=1024)),
                            content_type=response.headers['Content-Type'])
        except requests.RequestException as e:
            return f"Error: {e}", 500

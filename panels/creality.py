import json
import logging

from flask import Response, stream_with_context
from flask_sock import Sock
from panels.base_panel import BasePanel, ActivityState
from threading import Thread
import requests
import websocket


class CrealityPanel(BasePanel):
    def __init__(self, sock: Sock):
        super().__init__('creality', '/creality', sock)
        self.name = "Ender 3"
        self.ip = None
        self.state = ActivityState.OFF
        self.printer_data = {
            'model_name': self.name,
            'done': 0,
            'remaining': 0,
            'progress': 0.0,
            'state': self.state.value,
            'state_message': '',
            'state_filename': '',
            'temperatures': {}
        }
        self.ws = None
        self.sock.route('/ws', bp=self.bp)(self.update_route)
        self.dirty = False

    def on_open(self, ws):
        self.log("WebSocket connection opened")
        subscribe_message = json.dumps({
            "jsonrpc": "2.0",
            "method": "printer.objects.subscribe",
            "params": {
                "objects": {
                    "print_stats": ["state", "message", "filename", "print_duration"],
                    "heater_bed": ["temperature", "target"],
                    "extruder": ["temperature", "target"]
                }
            },
            "id": 1
        })
        ws.send(subscribe_message)

    def on_message(self, ws, message):
        parsed = json.loads(message)
        method = parsed.get("method", "")

        # Check if the message is a notify_history_changed update
        if method == "notify_history_changed":
            # Get the first notification update
            data = parsed.get("params", [])[0]
            self.logger.debug(f"Received notify_history_changed: {message}")
            action = data.get("action", "").lower()
            job = data.get("job", {})
            job_status = job.get("status", "").lower()

            # Deduce the current printer state from the notification.
            # You can expand this mapping as needed.
            logging.log(data)
            if action == "finished" or job_status == "completed":
                self.state = ActivityState.COMPLETE
            elif job_status == "in_progress" or job_status == "printing":
                self.state = ActivityState.WORKING
            elif action == "paused" or job_status == "paused":
                self.state = ActivityState.IDLE
            elif action == "error" or job_status == "error":
                self.state = ActivityState.ERROR
            else:
                deduced_state = ActivityState.ON

            # Update the printer state accordingly.
            self.map_moonraker_state_to_activity_state(deduced_state)
            # Optionally update printer_data if needed based on the job details
            self.printer_data.update({
                'state': self.state.value,
                'state_message': f"Job {job.get('job_id', '')} {deduced_state}",
                'state_filename': job.get('filename', ''),
                'total_duration': job.get('total_duration', 0.0)
            })
            self.dirty = True
        else:
            # Process regular messages from printer.objects.subscribe
            data = parsed.get('params', [])[0]
            if not data:
                return

            progress = data.get('print_stats', {}).get('print_duration', 0.0)
            remaining = self.printer_data.get('total_duration', 0)

            #self.map_moonraker_state_to_activity_state(data.get('print_stats', {}).get('state', 'off'))
            state_message = data.get('print_stats', {}).get('message', '')
            state_filename = data.get('print_stats', {}).get('filename', '')
            temperatures = data.get('heater_bed', {}).get('temperature', {})

            self.printer_data.update({
                'done': self.format_time(progress) if 'print_duration' in data.get('print_stats', {}) else
                self.printer_data['done'],
                'remaining': self.format_time(remaining) if 'total_duration' in data.get('print_stats', {}) else
                self.printer_data['remaining'],
                'progress': round(progress / remaining * 100, 0) if remaining > 0 else self.printer_data['progress'],
                'state': self.state.value,
                'state_message': state_message if 'message' in data.get('print_stats', {}) else self.printer_data[
                    'state_message'],
                'state_filename': state_filename if 'filename' in data.get('print_stats', {}) else self.printer_data[
                    'state_filename'],
                'temperatures': temperatures if 'temperatures' in data else self.printer_data['temperatures']
            })

            self.dirty = True

    def on_error(self, ws, error):
        self.log(f"WebSocket error: {error}")

    def on_close(self, ws, close_status_code, close_msg):
        self.log(f"WebSocket connection closed: {close_status_code} - {close_msg}")

    def connect_websocket(self):
        if not self.ip:
            self.log("Printer IP address not set in configuration")
            return

        websocket_url = f"ws://{self.ip}:7125/websocket"
        self.ws = websocket.WebSocketApp(
            websocket_url,
            on_open=self.on_open,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close
        )
        self.ws_thread = Thread(target=self.ws.run_forever)
        self.ws_thread.daemon = True
        self.ws_thread.start()

    def request_printer_status(self):
        if not self.ip:
            self.log("Printer IP address not set in configuration")
            pass

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

            self.printer_data = {
                'model_name': self.name,
                'done': self.format_time(progress),
                'remaining': self.format_time(remaining),
                'progress': round(progress / remaining * 100, 0) if remaining > 0 else 0,
                'state': self.state,
                'state_message': state_message,
                'state_filename': state_filename,
                'temperatures': temperatures
            }
        except requests.RequestException as e:
            self.log(f"Error requesting printer status: {e}")

    def get_data(self):
        return self.printer_data

    def set_config(self, data):
        self.ip = data.get('ip')
        self.name = data.get('name')
        self.bp.add_url_rule('/webcam', 'webcam', self.webcam_stream, methods=['GET'])
        self.request_printer_status()
        self.connect_websocket()

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

    def update_route(self, ws):
        while True:
            if self.dirty:
                self.log("Sending update")
                ws.send(json.dumps(self.printer_data))
                self.dirty = False

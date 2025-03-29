# panels/tailscale.py
import logging
import subprocess
import json

from flask import jsonify

from panels.base_panel import BasePanel, ActivityState


class TailscalePanel(BasePanel):
    def __init__(self):
        super().__init__('tailscale', '/tailscale')
        self.logger = logging.getLogger(__name__)
        self.bp.add_url_rule('/status', 'status', self.get_status_route, methods=['GET'])

    def get_status_format(self, status: str):
        if status == 'offline':
            return ActivityState.OFF
        elif status == '-' or status == 'online':
            return ActivityState.ON
        elif status.startswith('idle'):
            return ActivityState.IDLE
        return ActivityState.IDLE

    def get_tailscale_status(self):
        try:
            result = subprocess.check_output(['tailscale', 'status']).decode('utf-8')
            lines = result.split('\n')
            devices = []
            for line in lines:
                columns = line.split(maxsplit=4)
                self.logger.info(columns)
                if len(columns) >= 5:
                    device_info = {
                        'ip_address': columns[0],
                        'device_name': columns[1],
                        'owner': columns[2].removesuffix('@'),
                        'os': columns[3],
                        'status': self.get_status_format(columns[4]).value
                    }
                    devices.append(device_info)
            return devices
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Error running tailscale status: {e}")
            return []

    def get_tailnet_info(self):
        try:
            result = json.loads(subprocess.check_output(['tailscale', 'status', '--json']).decode('utf-8'))
            ct = result["CurrentTailnet"]
            return ct['Name'], ct['MagicDNSSuffix']
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Error getting tailscale network name: {e}")
            return 'Unknown', 'Unknown'

    def get_data(self):
        info = self.get_tailnet_info()
        return {'devices': self.get_tailscale_status(), 'tailnet_name': info[0], 'tailnet_link': info[1]}

    def set_config(self, data):
        pass

    def get_status_route(self):
        return jsonify(self.get_data())

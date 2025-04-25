import os
import subprocess
from flask import Response, request, jsonify

from panels.base_panel import BasePanel, ActivityState

class CameraPanel(BasePanel):
    def __init__(self):
        super().__init__('camera', '/camera')
        self.name = "Monitoring"
        self.state = ActivityState.ON
        self.stream_base_port = 5001
        self.processes = []
        self.available_cameras = self.detect_cameras()

        self.bp.add_url_rule('/webcam', 'webcam', self.webcam_stream, methods=['GET'])
        self.bp.add_url_rule('/set_camera_settings', 'set_camera_settings', self.set_camera_settings, methods=['POST'])

        self.start_streams()

    def detect_cameras(self):
        return [f"/dev/video{i}" for i in range(4) if os.path.exists(f"/dev/video{i}")]

    def start_streams(self):
        # Kill old processes first, if any
        self.stop_streams()

        for i, cam in enumerate(self.available_cameras):
            port = self.stream_base_port + i
            cmd = [
                'mjpg_streamer',
                '-i', f'input_uvc.so -d {cam} -r 640x480 -f 25',
                '-o', f'output_http.so -p {port} -w /usr/local/www'
            ]
            proc = subprocess.Popen(cmd)
            self.processes.append(proc)

    def stop_streams(self):
        for proc in self.processes:
            if proc.poll() is None:
                proc.terminate()
        self.processes = []

    def get_data(self):
        return {
            'name': self.name,
            'state': self.state.value,
            'cameras': self.available_cameras
        }

    def set_config(self, data):
        # Required by base class, returns empty as requested
        return {}

    def webcam_stream(self):
        index = request.args.get('camera', type=int)
        if self.state != ActivityState.ON:
            return Response(status=403)
        if index is None or index >= len(self.available_cameras):
            return Response(status=404)
        port = self.stream_base_port + index
        stream_url = f":{port}/?action=stream"
        return jsonify({'url': stream_url})

    def set_camera_settings(self):
        data = request.get_json()
        self.state = ActivityState.ON if data.get('enabled', True) else ActivityState.OFF
        self.save_config({
            'enabled': self.state.isReady()
        })
        return jsonify({
            "status": "success",
            "enabled": self.state.isReady()
        })


import subprocess
import time

from flask import Response, request, jsonify

from base_panel import ActivityState
from panels.base_panel import BasePanel

# Path for the temporary image that fswebcam will capture
IMAGE_PATH = '/tmp/webcam.jpg'


class CameraPanel(BasePanel):
    def __init__(self):
        super().__init__('camera', '/camera')
        self.name = "Monitoring"
        self.state = ActivityState.ON
        self.brightness = "60%"
        self.contrast = "15%"
        self.saturation = "50%"
        self.bp.add_url_rule('/webcam', 'webcam', self.webcam_stream, methods=['GET'])
        self.bp.add_url_rule('/set_camera_settings', 'set_camera_settings', self.set_camera_settings, methods=['POST'])

    def get_data(self):
        return {
            'name': self.name,
            'state': self.state.value,
            'brightness': int(self.brightness),
            'contrast': int(self.contrast),
            'saturation': int(self.saturation)
        }

    def set_config(self, data):
        self.name = data.get('name', self.name)
        self.state = ActivityState.ON if data.get('enabled', True) else ActivityState.OFF
        self.brightness = data.get('brightness', self.brightness)
        self.contrast = data.get('contrast', self.contrast)
        self.saturation = data.get('saturation', self.saturation)

    def image_stream(self):
        while True:
            if self.state.isInactive():
                break
            try:
                # Capture an image using fswebcam
                subprocess.run(
                    ['fswebcam', '-r', '1280x720', '--jpeg', '100', '--no-banner', '-s',
                     f'brightness={self.brightness}%', '-s',
                     f'Contrast={self.contrast}%', '-s', f'Gamma={self.saturation}%', IMAGE_PATH], check=True)
                # Open the captured image file
                with open(IMAGE_PATH, 'rb') as f:
                    img_data = f.read()
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + img_data + b'\r\n')
                time.sleep(0.1)
            except subprocess.CalledProcessError:
                self.state = ActivityState.ERROR
                self.log("Error: Failed to capture image.")
                break
            except FileNotFoundError:
                self.state = ActivityState.ERROR
                self.log("Error: Image path not found.")
                break

    def webcam_stream(self):
        return Response(self.image_stream(), mimetype='multipart/x-mixed-replace; boundary=frame')

    def set_camera_settings(self):
        data = request.get_json()
        self.brightness = data.get('brightness', self.brightness)
        self.contrast = data.get('contrast', self.contrast)
        self.saturation = data.get('saturation', self.saturation)
        self.state = ActivityState.ON if data.get('enabled', True) else ActivityState.OFF
        self.save_config({
            'brightness': self.brightness,
            'contrast': self.contrast,
            'saturation': self.saturation,
            'enabled': self.state.isReady()
        })
        return jsonify({"status": "success", "brightness": self.brightness, "contrast": self.contrast,
                        "saturation": self.saturation, "enabled": self.state.isReady()})

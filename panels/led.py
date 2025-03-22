# panels/led.py
import logging
import threading
import time
from flask import request, jsonify
from rpi_ws281x import PixelStrip, Color
from panels.base_panel import BasePanel

class LEDPanel(BasePanel):
    LED_COUNT = 150
    LED_PIN = 18
    LED_FREQ_HZ = 800000
    LED_DMA = 10
    LED_INVERT = False
    LED_CHANNEL = 0

    def __init__(self):
        super().__init__('led', '/led')
        self.r = 127
        self.g = 127
        self.b = 127
        self.brightness = 69
        self.presets = {}
        self.animation_thread = None
        self.animation_running = False

        self.strip = PixelStrip(self.LED_COUNT, self.LED_PIN, self.LED_FREQ_HZ, self.LED_DMA, self.LED_INVERT,
                                self.brightness, self.LED_CHANNEL)
        self.strip.begin()
        self.bp.add_url_rule('/set_color', 'set_color', self.set_color_route, methods=['POST'])
        self.bp.add_url_rule('/start_animation', 'start_animation', self.start_animation_route, methods=['POST'])
        self.bp.add_url_rule('/stop_animation', 'stop_animation', self.stop_animation_route, methods=['POST'])

    def set_color(self, r, g, b, brightness):
        self.r = r
        self.g = g
        self.b = b
        self.brightness = brightness
        self.strip.setBrightness(self.brightness)

        for i in range(self.LED_COUNT):
            self.strip.setPixelColor(i, Color(self.r, self.g, self.b))
        self.strip.show()

    def set_color_route(self):
        data = request.get_json()
        self.stop_animation()
        self.set_color(data.get('r', self.r),
                       data.get('g', self.g),
                       data.get('b', self.b),
                       data.get('brightness', self.brightness))
        self.save_config(
            {'r': self.r, 'g': self.g, 'b': self.b, 'brightness': self.brightness, 'presets': self.presets})

        return jsonify({"status": "success", "r": self.r, "g": self.g, "b": self.b, "brightness": self.brightness})

    def get_data(self):
        return {
            'r': self.r,
            'g': self.g,
            'b': self.b,
            'brightness': self.brightness,
            'presets': self.presets
        }

    def set_config(self, data):
        self.set_color(data.get('r', self.r), data.get('g', self.g), data.get('b', self.b),
                       data.get('brightness', self.brightness))
        self.presets = data.get('presets', {})
        pass

    def start_animation(self, colors, interval):
        if self.animation_running:
            self.stop_animation()

        self.animation_running = True
        self.animation_thread = threading.Thread(target=self.run_animation, args=(colors, interval))
        self.animation_thread.start()

    def stop_animation(self):
        self.logger.log(logging.DEBUG, "Stopping animation")
        self.animation_running = False
        if self.animation_thread and self.animation_thread != threading.current_thread():
            self.animation_thread.join()

    def run_animation(self, colors, interval):
        self.logger.log(logging.DEBUG, f"Running animation with colors {colors} and interval {interval}")
        while self.animation_running:
            for color in colors:
                if not self.animation_running:
                    break
                self.set_color(color[0], color[1], color[2], self.brightness)
                time.sleep(interval*0.001)

    def start_animation_route(self):
        data = request.get_json()
        selected = data.get('preset', None)

        if selected is None:
            return jsonify({"status": "error", "message": "No animation selected"})
        animation = self.presets.get(selected, None)
        if animation is None:
            return jsonify({"status": "error", "message": "Animation not found"})

        colors = animation.get('animation', [])
        interval = animation.get('interval', 1000)
        self.start_animation(colors, interval)
        return jsonify({"status": "animation started"})

    def stop_animation_route(self):
        self.stop_animation()
        return jsonify({"status": "animation stopped"})
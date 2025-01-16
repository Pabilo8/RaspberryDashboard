# panels/led.py
from panels.base_panel import BasePanel
from flask import request, jsonify
from rpi_ws281x import PixelStrip, Color


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

        self.strip = PixelStrip(self.LED_COUNT, self.LED_PIN, self.LED_FREQ_HZ, self.LED_DMA, self.LED_INVERT,
                                self.brightness, self.LED_CHANNEL)
        self.strip.begin()
        self.bp.add_url_rule('/set_color', 'set_color', self.set_color_route, methods=['POST'])

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
        self.set_color(data.get('r', self.r),
                       data.get('g', self.g),
                       data.get('b', self.b),
                       data.get('brightness', self.brightness))
        self.save_config({'r': self.r, 'g': self.g, 'b': self.b, 'brightness': self.brightness})

        return jsonify({"status": "success", "r": self.r, "g": self.g, "b": self.b, "brightness": self.brightness})

    def get_data(self):
        return {
            'r': self.r,
            'g': self.g,
            'b': self.b,
            'brightness': self.brightness
        }

    def set_config(self, data):
        self.set_color(data.get('r', self.r), data.get('g', self.g), data.get('b', self.b),
                       data.get('brightness', self.brightness))
        pass

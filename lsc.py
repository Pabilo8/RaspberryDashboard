from flask import Flask, render_template, request, jsonify
from rpi_ws281x import PixelStrip, Color

# LED strip configuration
LED_COUNT = 150       # Number of LED pixels
LED_PIN = 18         # GPIO pin connected to the pixels (must support PWM)
LED_FREQ_HZ = 800000 # LED signal frequency in hertz (usually 800kHz)
LED_DMA = 10         # DMA channel to use for generating signal (try 10)
LED_BRIGHTNESS = 69  # Default brightness level (0 to 255)
LED_INVERT = False   # True to invert the signal (when using NPN transistor level shift)
LED_CHANNEL = 0      # Set to 1 for GPIOs 13, 19, 41, 45, or 53

# Initialize Flask app and LED strip
app = Flask(__name__)
strip = PixelStrip(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA, LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL)
strip.begin()

# Helper function to set LED color with brightness
def set_color(r, g, b, brightness):
    strip.setBrightness(brightness)
    color = Color(r, g, b)
    for i in range(LED_COUNT):
        strip.setPixelColor(i, color)
    strip.show()

# Define routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/set_color', methods=['POST'])
def set_color_route():
    data = request.get_json()
    r = data.get('r', 0)
    g = data.get('g', 0)
    b = data.get('b', 0)
    brightness = data.get('brightness', LED_BRIGHTNESS)
    set_color(r, g, b, brightness)
    return jsonify({"status": "success", "r": r, "g": g, "b": b, "brightness": brightness})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

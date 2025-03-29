import logging

from flask import Flask, render_template
from flask_sock import Sock
from markupsafe import Markup

from panels import led, weather, creality, tailscale, lan, fridge, camera
from panels.base_panel import BasePanel

registered_panels = []
app = Flask(__name__)
sock = Sock(app)

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,  # Set the logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    format='%(asctime)s - %(levelname)s - %(message)s',  # Set the format for the logs
)
logger = logging.getLogger(__name__)


def register_panel(panel: BasePanel):
    panel.config()
    app.register_blueprint(panel.bp)
    registered_panels.append({
        'blueprint': panel.bp,
        'name': panel.bp.name,
        'data_provider': panel.get_data,
        'index': len(registered_panels)
    })
    logger.info("Registering panel:  " + panel.bp.name)


# Registration
register_panel(led.LEDPanel())
register_panel(weather.WeatherPanel())
register_panel(creality.CrealityPanel())
register_panel(tailscale.TailscalePanel())
register_panel(lan.LANPanel(sock))
register_panel(fridge.FridgePanel(sock))
register_panel(camera.CameraPanel())

@app.template_filter('icon')
def icon(icon_name):
    return Markup(f'<i class="fa-solid fa-{icon_name}"></i>')
@app.route('/')
def index():
    panel_data = {}
    panel_list = {}
    for registered_panel in registered_panels:
        panel_list[str(registered_panel['index'])] = registered_panel['name']
    panel_data["panel_list"] = panel_list

    for panel in registered_panels:
        name = panel['name']
        data_provider = panel['data_provider']
        panel_data[name] = data_provider()

    for i in range(len(registered_panels), 8):
        panel_list[str(i)] = ""

    print(panel_data)
    print(panel_list)
    return render_template('index.html', panel_data=panel_data, panel_list=panel_list)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
    app.jinja_env.filters['icon'] = icon

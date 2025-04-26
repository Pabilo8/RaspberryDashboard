import json
import logging

from flask import Flask, render_template
from flask_sock import Sock
from markupsafe import Markup

from panels import led, weather, creality, tailscale, lan, fridge, camera
from panels.base_panel import BasePanel, ActivityState

search_bar = True
registered_panels = []
panel_list = {}

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
def load_config():
    logger.info("Loading settings")
    try:
        with open('settings.json', 'r') as f:
            data = json.load(f)
            set_config(data['main'])
    except json.JSONDecodeError:
        logger.log("Invalid JSON value", level=logging.ERROR)
        set_config({})
    except FileNotFoundError:
        logger.log("No settings file found", level=logging.WARNING)
        with open('settings.json', 'w') as f:
            f.write("{}")
            f.close()
        pass
    except KeyError:
        pass


def set_config(data: dict):
    logger.info("Setting config")
    global search_bar, panel_list
    search_bar = data.get('search_bar', False)
    panel_list = data.get('panels', {})


load_config()
register_panel(led.LEDPanel())
register_panel(weather.WeatherPanel())
register_panel(creality.CrealityPanel(sock))
register_panel(tailscale.TailscalePanel())
register_panel(lan.LANPanel(sock))
register_panel(fridge.FridgePanel(sock))
register_panel(camera.CameraPanel())
register_panel(chatbot.ChatbotPanel())


@app.template_filter('icon')
def icon(icon_name):
    return Markup(f'<i class="icon icon-{icon_name}"></i>')


@app.template_filter('status_dot')
def status_dot(current_state: str):
    return icon(
        {
            ActivityState.ON: 'circle',
            ActivityState.WORKING: 'circle-ellipsis',
            ActivityState.OFF: 'circle-x',
            ActivityState.COMPLETE: 'circle-check-big',
            ActivityState.IDLE: 'circle-pause',
            ActivityState.ERROR: 'circle-alert'
        }[ActivityState(current_state)]
    )


@app.route('/')
def index():
    global panel_list
    panel_data = {}

    if panel_list == {}:
        for registered_panel in registered_panels:
            panel_list[str(registered_panel['index'])] = registered_panel['name']

    for panel in registered_panels:
        name = panel['name']
        data_provider = panel['data_provider']
        panel_data[name] = data_provider()

    for i in range(0, 8):
        if str(i) not in panel_list:
            panel_list[str(i)] = ''

    # may python be cursed for its dictionary implementation
    panel_list = {str(k): v for k, v in sorted(panel_list.items(), key=lambda item: int(item[0]))}

    logger.debug(panel_data)
    logger.debug(panel_list)
    return render_template('index.html', panel_data=panel_data, panel_list=panel_list, search_bar=search_bar)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
    app.jinja_env.filters['icon'] = icon
    app.jinja_env.filters['status_dot'] = status_dot

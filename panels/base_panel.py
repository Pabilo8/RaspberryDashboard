# base_panel.py
import json
import logging
import os

from flask import Blueprint
from flask_sock import Sock

class BasePanel:
    def __init__(self, name, url_prefix, sock:Sock=None):
        self.bp = Blueprint(name, __name__, url_prefix=url_prefix)
        self.sock = sock
        self.logger = logging.getLogger(name)

    def log(self, message, level=logging.INFO):
        self.logger.log(level, message)

    def config(self):
        try:
            with open('settings.json', 'r') as f:
                data = json.load(f)
                if data[self.bp.name]:
                    self.set_config(data[self.bp.name])
        except json.JSONDecodeError:
            self.log("Invalid JSON value", level=logging.ERROR)
            self.set_config({})
        except FileNotFoundError:
            self.log("No settings file found", level=logging.WARNING)
            with open('settings.json', 'w') as f:
                f.write("{}")
                f.close()
            pass
        except KeyError:
            pass

    def save_config(self, data: dict):
        try:
            if not os.path.exists('settings.json'):
                self.log("Creating a new settings file", level=logging.INFO)
                with open('settings.json', 'w') as f:
                    json.dump({}, f)

            with open('settings.json', 'r') as f:
                settings = json.load(f)
            settings[self.bp.name] = data
            with open('settings.json', 'w') as f:
                json.dump(settings, f, indent=4)
            self.log("Configuration saved successfully")
        except json.JSONDecodeError:
            self.log("Invalid JSON value", level=logging.ERROR)
        except Exception as e:
            self.log(f"Error saving configuration: {e}", level=logging.ERROR)


    def get_data(self):
        raise NotImplementedError("Subclasses should implement this method!")

    def set_config(self, data):
        raise NotImplementedError("Subclasses should implement this method!")


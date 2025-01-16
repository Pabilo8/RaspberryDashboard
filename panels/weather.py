# panels/weather.py
from panels.base_panel import BasePanel
import requests


class WeatherPanel(BasePanel):
    def __init__(self):
        super().__init__('weather', '/weather')
        self.api_key = None
        self.city = None

    def get_icon(self, code: str):
        day = code[2] == 'd'
        match code[0:2]:
            case '01':
                return 'fa-sun' if day else 'fa-moon'
            case '02':
                return 'fa-cloud-sun' if day else 'fa-cloud-moon'
            case '03' | '04':
                return 'fa-cloud'
            case '09':
                return 'fa-cloud-rain'
            case '10':
                return 'fa-cloud-showers-heavy'
            case '11':
                return 'fa-cloud-bolt'
            case '13':
                return 'fa-snowflake'
            case '50':
                return 'fa-smog'
        return code

    def get_openweather(self):

        if self.city is None or self.api_key is None:
            self.save_config({'api_key': 'your_api_key', 'city': 'your_city'})
            return {
                'outside_temp': '-1',
                'description': 'Error: Missing API key or city',
                'icon': 'fa-exclamation-triangle'
            }

        url = f'http://api.openweathermap.org/data/2.5/weather?q={self.city}&appid={self.api_key}&units=metric'

        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            weather = {
                'outside_temp': data['main']['temp'],
                'description': data['weather'][0]['description'].title(),
                'icon': self.get_icon(data['weather'][0]['icon'])
            }
            return weather
        except requests.RequestException as e:
            self.log(f"Error: {e}")
            return {
                'outside_temp': '-1',
                'description': 'Error ' + str(e)
            }

    def get_cpu_temperature(self):
        try:
            with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
                temp_str = f.readline()
                return float(temp_str) / 1000.0
        except FileNotFoundError:
            return -1

    def get_data(self):
        w = self.get_openweather()
        return {
            'weather_desc': w['description'],
            'outside_temp': w['outside_temp'],
            'icon': w['icon'],
            'room_temp': 21,
            'cpu_temp': self.get_cpu_temperature(),
        }

    def set_config(self, data):
        self.api_key = data.get('api_key')
        self.city = data.get('city')

import json
import telnetlib
import threading
import time

from flask import render_template
from flask_sock import Sock

from panels.base_panel import BasePanel


class LANPanel(BasePanel):
    def __init__(self, sock: Sock):
        super().__init__('lan', '/lan', sock)
        self.host = None
        self.user = None
        self.password = None
        self.users = {}
        self.roles = {}
        self.update_interval = 60  # default to 1 minute
        self.dirty_devices = False
        self.dirty_users = False
        self.last_data = None
        self.start_periodic_updates()
        self.sock.route('/ws', bp=self.bp)(self.update_route)

    def update_route(self, ws):
        while True:
            if self.dirty_devices:
                data = ("".join(
                    render_template('lan_entry.html', device=device) for device in self.new_data['devices']).replace(
                    "\n", "").encode("utf-8"))
                # data = render_template('lan_devices.html', panel=self).replace("\n", "").encode("utf-8")
                ws.send(json.dumps({'type': 'devices', 'data': data}))
                self.dirty_devices = False
            if self.dirty_users:
                data = render_template('lan_users.html', panel=self).replace("\n", "").encode("utf-8")
                ws.send(json.dumps({'type': 'users', 'data': data}))
                self.dirty_users = False

    def start_periodic_updates(self):
        def update_task():
            while True:
                time.sleep(self.update_interval)
                self.check_for_updates()

        thread = threading.Thread(target=update_task)
        thread.daemon = True
        thread.start()

    def check_for_updates(self):
        new_data = self.get_data()
        if self.last_data['devices'] is None or new_data['devices'] != self.last_data['devices']:
            self.dirty_devices = True
        if new_data['users'] != self.last_data['users']:
            self.dirty_users = True
        self.last_data = new_data

    def get_lan_devices(self):
        if self.host is None or self.user is None or self.password is None:
            self.save_config({
                'host': '0.0.0.0',
                'user': 'admin',
                'password': 'password'
            })

        try:
            with telnetlib.Telnet(self.host) as tn:
                tn.read_until(b"login: ")
                tn.write(self.user.encode('ascii') + b"\n")

                tn.read_until(b"Password: ")
                tn.write(self.password.encode('ascii') + b"\n")

                tn.read_until(b"# ")
                tn.write(b"arp -a\n")
                tn.write(b"wl_atheros assoclist\n")
                tn.write(b"exit\n")

                output = tn.read_all().decode('ascii')
                devices = []
                wireless_macs = set()

                for line in output.splitlines():
                    if line.startswith("assoclist"):
                        parts = line.split()
                        if len(parts) > 1:
                            wireless_macs.add(parts[1].lower())

                for line in output.splitlines():
                    if '(' in line and ')' in line:
                        parts = line.split()
                        if len(parts) >= 4:
                            hostname = parts[0] if parts[0] != '?' else 'Unknown'
                            ip_address = parts[1].strip('()')
                            mac_address = parts[3].lower()
                            conn = "wifi" if mac_address in wireless_macs else "ethernet-port"
                            devices.append({'hostname': hostname, 'ip_address': ip_address, 'mac_address': mac_address,
                                            'conn': conn})

                devices.append({
                    'hostname': "Router",
                    'ip_address': self.host,
                    'mac_address': "",
                    'conn': 'router'
                })

                # Update device names and icons
                for role in self.roles.values():
                    for device in devices:
                        if ('name' in role and device['ip_address'] == role['address']) or ('hostname' in role and device['hostname'] == role['hostname']):
                            if role.get('name') is not None:
                                device['hostname'] = role['name']
                            if role.get('icon') is not None:
                                device['conn'] = role['icon']

                return devices
        except Exception as e:
            self.log(f"Error: {e}")
            return []

    def get_user_presence(self, devices):
        user_presence = {user: False for user in self.users}
        for device in devices:
            for user, user_devices in self.users.items():
                if device['hostname'] in user_devices:
                    user_presence[user] = True
        return user_presence

    def get_data(self):
        devices = self.get_lan_devices()
        user_presence = self.get_user_presence(devices)
        users = {user.split(':')[0]: {'display_name': user.split(':')[1], 'present': present} for user, present in
                 user_presence.items()}
        return {'devices': devices, 'users': users}

    def set_config(self, data):
        self.host = data.get('host', self.host)
        self.user = data.get('user', self.user)
        self.password = data.get('password', self.password)
        self.users = data.get('users', self.users)
        self.roles = data.get('roles', self.roles)
        self.update_interval = data.get('update_interval', self.update_interval)
        pass

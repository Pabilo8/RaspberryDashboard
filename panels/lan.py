import json
import telnetlib

from panels.base_panel import BasePanel


class LANPanel(BasePanel):
    def __init__(self):
        super().__init__('lan', '/lan')
        self.host = None
        self.user = None
        self.password = None
        self.users = self.load_users()

    def load_users(self):
        with open('settings.json', 'r') as f:
            settings = json.load(f)
        return settings.get('lan', {}).get('users', {})

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
                            conn = "wifi" if mac_address in wireless_macs else "ethernet"
                            devices.append({'hostname': hostname, 'ip_address': ip_address, 'mac_address': mac_address,
                                            'conn': conn})

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
        users = {user.split(':')[0]: {'display_name': user.split(':')[1], 'present': present} for user, present in user_presence.items()}
        return {'devices': devices, 'users': users}

    def set_config(self, data):
        self.host = data.get('host', self.host)
        self.user = data.get('user', self.user)
        self.password = data.get('password', self.password)
        pass
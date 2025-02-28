# panels/fridge.py
import logging

import requests
from flask import request, jsonify, render_template
from flask_sock import Sock
from tinydb import TinyDB, Query
from tinydb.operations import increment, decrement

from panels.base_panel import BasePanel


class FridgePanel(BasePanel):
    def __init__(self, sock: Sock):
        super().__init__('fridge', '/fridge', sock)
        self.logger = logging.getLogger(__name__)
        self.db = TinyDB('fridge_db.json')
        self.table = self.db.table('products')
        self.bp.add_url_rule('/add_product', 'add_product', self.add_product_route, methods=['POST'])
        self.bp.add_url_rule('/remove_product', 'remove_product', self.remove_product_route, methods=['POST'])
        self.sock.route('/ws', bp=self.bp)(self.update_route)
        self.dirty = False

    def add_product(self, barcode):
        url = f"https://world.openfoodfacts.org/api/v0/product/{barcode}.json?fields=product_name,image_url,product_name_pl,product_name_en"
        data = requests.get(url).json()
        if (data["status"] == 0):
            self.logger.error(f"Product with barcode {barcode} not found")
            return
        if (self.table.search(Query().code == barcode)):
            self.table.update(increment('quantity'), Query().code == barcode)
            return
        prod = data['product']
        if 'product_name_pl' in prod:
            pname = prod['product_name_pl']
        elif 'product_name' in prod:
            pname = prod['product_name']
        else:
            pname = prod['product_name_en']

        self.table.insert({"code": barcode,
                           "name": pname,
                           "quantity": 1,
                           "image_url": data['product']['image_url']})

    def add_product_route(self):
        data = request.get_json()
        self.add_product(data.get('barcode'))
        self.dirty = True
        return jsonify({"status": "success"})

    def remove_product_route(self):
        data = request.get_json()
        if not self.table.search(Query().code == data.get('barcode')):
            return jsonify({"status": "error", "message": "Product not found"})
        self.table.update(decrement("quantity"), Query().code == data.get('barcode'))
        if self.table.get(Query().code == data.get('barcode'))['quantity'] < 1:
            self.table.remove(Query().code == data.get('barcode'))
        self.dirty = True
        return jsonify({"status": "success"})

    def update_route(self, ws):
        while True:
            if self.dirty:
                print("Sending update")
                data = ("".join(render_template('product_row.html', product=product) for product in self.table.all()).replace("\n", "").encode("utf-8"))
                ws.send(data)
                self.dirty = False

    def get_data(self):
        self.logger.info("Found products:")
        self.logger.info(self.table.all())
        return {'products': self.table.all()}

    def set_config(self, data):
        pass

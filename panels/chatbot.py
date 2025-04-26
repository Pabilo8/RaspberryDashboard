import os
from flask import request, jsonify
from mistralai import Mistral
import markdown2

from panels.base_panel import BasePanel, ActivityState


class ChatbotPanel(BasePanel):
    def __init__(self):
        super().__init__('chatbot', '/chatbot')
        self.name = "ChatBot"
        self.state = ActivityState.ON
        self.api_key = ''
        self.agent_id = ''
        self.icon = 'bot'
        self.client = None

        self.bp.add_url_rule('/send', 'send_message', self.send_message, methods=['POST'])
        self.bp.add_url_rule('/name', 'get_name', self.get_name, methods=['GET'])

    def set_config(self, data):
        self.name = data.get('name', "Chat")
        self.api_key = data.get('api_key', '')
        self.agent_id = data.get('agent', '')
        self.icon = data.get('icon', 'bot')

        self.state = ActivityState.ON if self.api_key and self.agent_id else ActivityState.ERROR
        self.client = Mistral(api_key=self.api_key)

    def get_data(self):
        return {
            'name': self.name,
            'icon': self.icon,
            'state': self.state.value
        }

    def get_name(self):
        return jsonify({"name": self.name})

    def send_message(self):
        if self.state != ActivityState.ON:
            return jsonify({"error": "Chat is disabled."}), 403

        user_input = request.json.get('message')
        if not user_input:
            return jsonify({"error": "No message provided."}), 400

        try:
            response = self.client.agents.complete(
                agent_id=self.agent_id,
                messages=[
                    {"role": "user", "content": user_input}
                ])
            reply = response.choices[0].message.content
        except Exception as e:
            return jsonify({"error": str(e)}), 500

        return jsonify({"reply": markdown2.markdown(reply)})

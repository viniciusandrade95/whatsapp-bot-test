import os
from flask import Flask, request
import requests

app = Flask(__name__)

VERIFY_TOKEN = os.environ.get("WHATSAPP_VERIFY_TOKEN", "my_verify_token")
WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN")  # required
PHONE_NUMBER_ID = os.environ.get("WHATSAPP_PHONE_NUMBER_ID")  # required


@app.route("/", methods=["GET"])
def healthcheck():
    return "OK", 200


@app.route("/webhook", methods=["GET"])
def verify():
    """
    This is called by Meta when you press 'Verify and Save' in the Webhooks UI.
    It sends hub.mode, hub.verify_token, and hub.challenge.
    """
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        return challenge, 200
    else:
        return "Verification failed", 403


@app.route("/webhook", methods=["POST"])
def webhook():
    """
    This receives incoming WhatsApp messages. We echo back any text message.
    """
    data = request.get_json()
    if not data:
        return "no json", 200

    try:
        entry = data["entry"][0]
        changes = entry["changes"][0]
        value = changes["value"]
        messages = value.get("messages", [])
    except (KeyError, IndexError, TypeError):
        # Not a message (could be status update, etc.)
        return "ignored", 200

    for message in messages:
        if message.get("type") == "text":
            text = message["text"]["body"]
            sender = message["from"]  # WhatsApp number in international format
            send_whatsapp_message(sender, text)  # echo same text

    return "ok", 200


def send_whatsapp_message(to_number: str, text: str):
    """
    Send a text message using WhatsApp Cloud API.
    """
    if not WHATSAPP_TOKEN or not PHONE_NUMBER_ID:
        print("Missing WHATSAPP_TOKEN or PHONE_NUMBER_ID")
        return

    url = f"https://graph.facebook.com/v22.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to_number,
        "type": "text",
        "text": {"body": text}
    }

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=10)
        print("WhatsApp API response:", resp.status_code, resp.text)
    except Exception as e:
        print("Error calling WhatsApp API:", e)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)

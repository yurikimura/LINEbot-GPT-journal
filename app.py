
from datetime import datetime, timedelta, timezone
import json
import os

from flask import Flask, abort, request
import requests

from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
)

app = Flask(__name__)

line_token = os.environ.get("TOKEN")
line_secret = os.environ.get("SECRET")
notion_token = os.environ.get("NOTION_TOKEN")
notion_database_id = os.environ.get("NOTION_DATABASE_ID")
gpt_seerver_url = os.environ.get("GPT_SERVER_URL")

line_bot_api = LineBotApi(line_token)
handler = WebhookHandler(line_secret)

@app.route("/callback", methods=("GET", "POST"))
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        print("Invalid signature. Please check your channel access token/channel secret.")
        abort(400)

    return 'OK'


@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    
    notion_dump(event.message.text)
    
    line_bot_api.reply_message(
        event.reply_token,
        [TextSendMessage(text=chat_reply(event.message.text))]
    )

def notion_dump(text):
    JST = timezone(timedelta(hours=+9), 'JST')
    jp_time = datetime.now(JST)

    notion_headers = {"Authorization": f"Bearer {notion_token}",
            "Content-Type": "application/json","Notion-Version": "2021-05-13"}
    notion_body = {"parent": { "database_id": notion_database_id},
        "properties": {
            "Name": {"title": [{"text": {"content": f"{text}"}}]},
            "Created": {"date": {"start": jp_time.isoformat()}}
        }}
    requests.request('POST', url='https://api.notion.com/v1/pages',\
        headers=notion_headers, data=json.dumps(notion_body))
    return
    
def chat_reply(text):
    
    if "返信不要" in text:
      return

    gpt_headers = {
        "Content-Type": "application/json",
    }
    gpt_data = f'{{"content":"{text}"}}'

    gpt_response = requests.post(gpt_seerver_url, headers=gpt_headers, data=gpt_data.encode("utf-8"))
    gpt_result = gpt_response.json()
    return gpt_result["reply"]

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

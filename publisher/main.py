import logging
import json
import uvicorn
from fastapi import FastAPI
from core.rabitmq_publisher import get_rabbit_mq_publisher

app = FastAPI()

# Creating logger
dev_logger = logging.getLogger("websocket_publisher")
dev_logger.setLevel(logging.INFO)
# Create a handler and associate the formatter with it
formatter = logging.Formatter(
    "%(asctime)s  | %(levelname)s | %(filename)s | %(message)s"
)
handler = logging.StreamHandler()
handler.setFormatter(formatter)
dev_logger.addHandler(handler)
logger = logging.getLogger("websocket_publisher")

@app.get('/')
async def home():
    return {'message': 'Hello👋 Developers💻'}



@app.post('/publish_message/')
async def publish_message(data:dict):
    channel_name = data.get('channel_name')
    event_name = data.get("event_name")
    payload = data.get("payload")
    publisher = get_rabbit_mq_publisher()
    if not publisher.connection_success:
        return {"status":False,"message":"event publish failed"}

    data = {
        "channel_name":channel_name,
        "payload":payload,
        "event_name":event_name
    }
    # Publish data to fastapi service
    encoded_company_critarea = json.dumps(
        data
    ).encode("utf-8")
    publisher.publish_message(encoded_company_critarea, ttl=5000)
    if not publisher.publish_status:
        return {
                "status": False,
                "message": "Something went wrong when publishing data to fastapi service",
            }
    
    return {"status":True,"message":"event publish successfully"}


    




if __name__ == '__main__':
    uvicorn.run('main:app', host='0.0.0.0', port=5008, reload=True)


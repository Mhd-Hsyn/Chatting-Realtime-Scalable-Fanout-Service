import asyncio
import threading
import logging
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sockets import sio_app, sio_server
# from core.rabitmq_consumer import consume_messages
from core import rabitmq_consumer


app = FastAPI()



# Creating logger
dev_logger = logging.getLogger("socktet_server_1")
dev_logger.setLevel(logging.INFO)
# Create a handler and associate the formatter with it
formatter = logging.Formatter(
    "%(asctime)s  | %(levelname)s | %(filename)s | %(message)s"
)
handler = logging.StreamHandler()
handler.setFormatter(formatter)
dev_logger.addHandler(handler)
logger = logging.getLogger("socktet_server_1")



app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get('/home')
async def home():
    return {'message': 'Hello👋 Developers💻'}

@app.post('/join_channel/')
async def join_channel(data: dict):
    """
    Endpoint to let a user join a channel and notify others in the channel.
    """
    channel_name = data.get('channel_name')
    user_data = data.get('user_data')
    if not channel_name or not user_data:
        return {"error": "channel_name and user_data are required"}

    # Notify other users in the channel
    await sio_server.emit('user_joined', {'user_data': user_data}, room=channel_name)
    return {"message": f"User {user_data} joined channel {channel_name}"}

@app.post('/leave_channel/')
async def leave_channel(data: dict):
    """
    Endpoint to let a user leave a channel and notify others in the channel.
    """
    channel_name = data.get('channel_name')
    user_data = data.get('user_data')
    if not channel_name or not user_data:
        return {"error": "channel_name and user_data are required"}

    # Notify other users in the channel
    await sio_server.emit('user_left', {'user_data': user_data}, room=channel_name)
    return {"message": f"User {user_data} left channel {channel_name}"}


@app.post('/send_message/')
async def send_message(data: dict):
    """
    Endpoint to send a message to all users in a channel.
    """
    channel_name = data.get('channel_name')
    user_data = data.get('user_data')
    message = data.get('message')

    if not channel_name or not user_data or not message:
        return {"error": "channel_name, user_data, and message are required"}

    # Broadcast message to the channel
    await sio_server.emit('new_message', {'user_data': user_data, 'message': message}, room=channel_name)
    return {"message": f"Message sent to channel {channel_name}"}

app.mount('/', app=sio_app)

@app.on_event("startup")
async def startup_event():
    # uvicorn ka running loop capture karke consumer ko pass kar do
    rabitmq_consumer.event_loop = asyncio.get_running_loop()

    # consumer thread start karo
    consumer_thread = threading.Thread(
        target=rabitmq_consumer.consume_messages,
        daemon=True
    )
    consumer_thread.start()

if __name__ == '__main__':
    uvicorn.run('main:app', host='0.0.0.0', port=5009, reload=True)


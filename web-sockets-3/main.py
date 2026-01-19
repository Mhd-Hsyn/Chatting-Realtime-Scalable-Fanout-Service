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
    uvicorn.run('main:app', host='0.0.0.0', port=9009, reload=True)


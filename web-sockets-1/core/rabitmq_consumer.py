import asyncio
import json
import time
import logging
import pika
from .config import (
    rabbitmq_username,
    rabbitmq_password,
    rabbitmq_host,
    rabbitmq_port,
    rabbitmq_document_process_exchange,
    rabbitmq_document_process_quee,
    rabbitmq_document_process_routing_key,
)
from sockets import  sio_server
from .choices import (
    RealtimeEventChoices
)
from redis_utils import get_user_active_room



event_loop = None

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)


logger = logging.getLogger("socktet_server_1")
SUCCESS = True
FAILURE = False


#pylint: disable=broad-exception-caught
def continous_consuming_rabitmq_messages(loop_behavior:str)->None:
    """Consume messages from a RabbitMQ queue and process them based on the user's role"""
    sleep_time = 10
    try:
        credentials = pika.PlainCredentials(rabbitmq_username, rabbitmq_password)
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                rabbitmq_host, rabbitmq_port, "/", credentials
            )
        )
        channel = connection.channel()
        channel.exchange_declare(
            exchange=rabbitmq_document_process_exchange, exchange_type="fanout"
        )
        channel.queue_declare(queue=rabbitmq_document_process_quee)
        channel.queue_bind(
            exchange=rabbitmq_document_process_exchange,
            queue=rabbitmq_document_process_quee,
            routing_key=rabbitmq_document_process_routing_key,
        )
        logger.info("Document Process Subscriber Consumer Service RabbitMQ Connection Channel: %s", rabbitmq_document_process_quee)
        channel.basic_consume(
            queue=rabbitmq_document_process_quee,
            on_message_callback=rabitmq_consumer_callback,
            auto_ack=False,
        )
        channel.start_consuming()

    except pika.exceptions.AMQPConnectionError as rabitmq_exception:
        logger.info("Connection error. Retrying in 5 seconds...")
        time.sleep(sleep_time)
        if loop_behavior != "1":
            continous_consuming_rabitmq_messages(loop_behavior)
    except Exception as swr:
        logger.info("An error occurred: %s", swr)
        time.sleep(sleep_time)
        if loop_behavior != "1":
            continous_consuming_rabitmq_messages(loop_behavior)

# pylint: disable=unused-argument
# def rabitmq_consumer_callback(ch, method, properties, body)->bool:
#     try:
#         message = body.decode()
#         user_payload = json.loads(message)
#         logging.info(f"Received message: {user_payload}")
#         print("Received message: ___________", user_payload)
        
#         channel_name = user_payload["channel_name"]  # room-id
#         payload = user_payload["payload"]
#         event_name = user_payload["event_name"]  # new_message
        
#         # Ensure loop is available
#         if event_loop and event_loop.is_running():
#             future = asyncio.run_coroutine_threadsafe(
#                 sio_server.emit(
#                     event_name,
#                     payload,
#                     room=channel_name
#                 ),
#                 event_loop
#             )
#             try:
#                 future.result(timeout=5)
#                 logger.info("Socket.IO event sent ✅")
#             except Exception as e:
#                 logger.error(f"Emit failed ❌: {e}")
#         else:
#             logger.warning("No running event loop found")
        
#         ch.basic_ack(delivery_tag=method.delivery_tag)
#         return SUCCESS

#     except json.JSONDecodeError as json_error:
#         logger.info("Error decoding JSON: %s", str(json_error))
#         return FAILURE
#     except Exception as swr:
#         logger.info("error processing message: %s", str(swr))
#         return FAILURE



def rabitmq_consumer_callback(ch, method, properties, body)->bool:
    try:
        message = body.decode()
        user_payload = json.loads(message)
        logging.info(f"Received message: {user_payload}")
        print("Received message: ___________ WEBSOCKET SERVER 1", user_payload)
        
        channel_name = user_payload["channel_name"]  # room-id
        payload = user_payload["payload"]
        event_name = user_payload["event_name"]  # new_message
        
        # --- 🚀 SMART FILTERING (REDIS VERSION) ---
        notification_events = [
            RealtimeEventChoices.UNREAD_MESSAGE_COUNT_UPDATE,
            RealtimeEventChoices.NEW_MESSAGE_NOTIFICATION
        ]
        should_emit = True

        if event_name in notification_events:
            target_chat_room_id = payload.get('room_id') 
            
            # Channel name se user_id nikalo ('user_55' -> '55')
            try:
                target_user_id = channel_name.split('_')[1]
            except IndexError:
                target_user_id = None

            if target_chat_room_id and target_user_id:
                if event_loop and event_loop.is_running():
                    
                    # Async check via Redis
                    async def check_redis_presence():
                        # Direct Redis se poocho: Ye user abhi kis room me h?
                        active_room = await get_user_active_room(target_user_id)
                        return active_room

                    future_check = asyncio.run_coroutine_threadsafe(check_redis_presence(), event_loop)
                    
                    try:
                        # Redis returns String or None
                        current_user_room = future_check.result(timeout=2)
                        
                        # Comparison: Agar User ka Current Room == Notification wala Room
                        if current_user_room == str(target_chat_room_id):
                            print(f"🚫 BLOCKING NOTIFICATION: User {target_user_id} is already inside Room {target_chat_room_id}")
                            should_emit = False
                            
                    except Exception as e:
                        logger.error(f"Redis check failed: {e}")


        # --- 🏁 SMART FILTERING LOGIC END ---

        if should_emit:
            # Ensure loop is available
            if event_loop and event_loop.is_running():
                future = asyncio.run_coroutine_threadsafe(
                    sio_server.emit(
                        event_name,
                        payload,
                        room=channel_name
                    ),
                    event_loop
                )
                try:
                    future.result(timeout=5)
                    logger.info("Socket.IO event sent ✅")
                except Exception as e:
                    logger.error(f"Emit failed ❌: {e}")
            else:
                logger.warning("No running event loop found")
        
        ch.basic_ack(delivery_tag=method.delivery_tag)
        return SUCCESS

    except json.JSONDecodeError as json_error:
        logger.info("Error decoding JSON: %s", str(json_error))
        return FAILURE
    except Exception as swr:
        logger.info("error processing message: %s", str(swr))
        return FAILURE


def consume_messages(loop_behavior:str="infinite_running")->None:
    """Continously run rabitmq consumer"""
    while True:
        if loop_behavior != "1":
            continous_consuming_rabitmq_messages(loop_behavior)
        else:
            continous_consuming_rabitmq_messages(loop_behavior)
            break
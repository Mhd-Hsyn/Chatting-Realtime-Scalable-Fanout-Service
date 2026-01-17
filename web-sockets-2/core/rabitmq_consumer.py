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
def rabitmq_consumer_callback(ch, method, properties, body)->bool:
    try:
        message = body.decode()
        user_payload = json.loads(message)
        logging.info(f"Received message: {user_payload}")
        
        channel_name = user_payload["channel_name"]
        payload = user_payload["payload"]
        event_name = user_payload["event_name"]
        
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
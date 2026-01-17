"""This module defines a message queue client class for RabbitMQ"""

import logging
import socket
import time
from abc import ABC, abstractmethod
from .constant import RetryConstants
import pika
from decouple import config


# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)


logger = logging.getLogger("socktet_server_1")


rabbitmq_host = config("RABBITMQ_HOST")
rabbitmq_port = config("RABBITMQ_PORT")
rabbitmq_username = config("RABBITMQ_USER")
rabbitmq_password = config("RABBITMQ_PASSWORD")
rabbitmq_quees = config("RABBITMQ_QUEES")
rabbitmq_exchange = config("RABBITMQ_EXCHANGE")
rabbitmq_routing_key = config("RABBITMQ_ROUTING_KEY")


class MessageQueueClient(ABC):
    """
    Abstract base class for message queue clients.

    This class defines the interface for interacting with a message queue service.
    Subclasses must implement the abstract methods to connect to the message queue,
    publish messages, and close the connection gracefully.
    """

    @abstractmethod
    def _connect(self):
        """
        Connect to the message queue service.

        This method should be implemented by subclasses to establish a connection
        to the message queue service (e.g., RabbitMQ, Kafka, etc.).

        """
        raise NotImplementedError

    @abstractmethod
    def publish_message(self, message: bytes, ttl: int):
        """
        Publish a message to the message queue.

        This method should be implemented by subclasses to publish a message
        to the message queue.

        Args:
            message (str): The message to be published.
            ttl (int): Time-to-live for the message in milliseconds.
        raise NotImplementedError

        """

    @abstractmethod
    def close_connection(self):
        """
        Close the connection to the message queue service.

        This method should be implemented by subclasses to gracefully close the
        connection to the message queue service.
        """
        raise NotImplementedError


class RabbitMQPublisher(MessageQueueClient):
    """
    RabbitMQ-based message publisher.

    This class implements the 'MessageQueueClient' interface for publishing messages
    to a RabbitMQ message queue.
    """

    def __init__(
        self,
        username,
        password,
        host,
        port,
        rabbitmq_quees,
        rabbitmq_exchange,
        rabbitmq_routing_key,
        max_retries,
        retry_delay,
        connection_success,
        publish_status,
    ):
        self.rabbitmq_username = username
        self.rabbitmq_password = password
        self.rabbitmq_host = host
        self.rabbitmq_port = port
        self.rabbitmq_quees = rabbitmq_quees
        self.rabbitmq_exchange = rabbitmq_exchange
        self.rabbitmq_routing_key = rabbitmq_routing_key
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.connection_success = connection_success
        self.publish_status = publish_status
        self.connection = None
        self._connect()

    def _connect(self):
        try:
            credentials = pika.PlainCredentials(
                self.rabbitmq_username, self.rabbitmq_password
            )
            connection_params = pika.ConnectionParameters(
                host=self.rabbitmq_host,
                port=self.rabbitmq_port,
                credentials=credentials,
            )
        except pika.exceptions.AMQPError as amqp_error:
            logger.error("AMQP error in connection parameters: %s", amqp_error)

        for retry_attempt in range(self.max_retries):
            try:
                self.connection = pika.BlockingConnection(connection_params)
                self.channel = self.connection.channel()
                self.channel.exchange_declare(
                    exchange=self.rabbitmq_exchange, exchange_type="fanout"
                )

                for queue in self.rabbitmq_quees.split(","):
                    print("queue __________________ ", queue)
                    self.channel.queue_declare(queue=queue)
                    self.channel.queue_bind(exchange=self.rabbitmq_exchange, queue=queue)
                
                logger.info("connection established")
                self.connection_success = True
                break

            except pika.exceptions.AMQPConnectionError as connection_error:
                if retry_attempt < self.max_retries - 1:
                    logger.error(
                        "AMQP connection error (retry %d): %s while connecting rabbitmq. Retrying in %d seconds...",
                        retry_attempt + 1,
                        connection_error,
                        self.retry_delay,
                    )
                    time.sleep(self.retry_delay)
                else:
                    logger.error("Max retries reached. Unable to connect to RabbitMQ")
                    break

            except pika.exceptions.AMQPChannelError as channel_error:
                logger.error(
                    "AMQP channel error: %s while connecting rabbitmq", channel_error
                )

            except socket.gaierror:
                logger.error(
                    "DNS resolution error: Unable to resolve the host '%s",
                    self.rabbitmq_host,
                )

    def publish_message(self, message: bytes, ttl: int):
        try:
            self.channel.basic_publish(
                exchange=self.rabbitmq_exchange,
                routing_key=self.rabbitmq_routing_key,
                body=message,
                properties=pika.BasicProperties(
                    delivery_mode=2, expiration=str(ttl * 1000)
                ),
            )
            logger.info("Message sent successfully")
            self.close_connection()
            self.publish_status = True

        except pika.exceptions.ConnectionClosedByBroker as broker_closed_error:
            logger.error(
                "Connection closed by broker while publishing message : %s",
                broker_closed_error,
            )
            self.close_connection()

        except pika.exceptions.AMQPError as amqp_error:
            logger.error("AMQP error while publishing message: %s", amqp_error)
            self.close_connection()

    def close_connection(self):
        if self.connection is not None:
            self.connection.close()
            logger.info("connection closed")


def get_rabbit_mq_publisher(
    rabbitmq_username: str = rabbitmq_username,
    rabbitmq_password: str = rabbitmq_password,
    rabbitmq_host: str = rabbitmq_host,
    rabbitmq_port: str = rabbitmq_port,
    rabbitmq_quees: str = rabbitmq_quees,
    rabbitmq_exchange: str = rabbitmq_exchange,
    rabbitmq_routing_key: str = rabbitmq_routing_key,
    max_retries: str = RetryConstants.MAX_RETRIES.value,
    retry_delay: str = RetryConstants.RETRY_DELAY.value,
) -> RabbitMQPublisher:
    """Get a RabbitMQPublisher instance with the specified configuration"""
    publisher_args = {
        "username": rabbitmq_username,
        "password": rabbitmq_password,
        "host": rabbitmq_host,
        "port": rabbitmq_port,
        "rabbitmq_quees": rabbitmq_quees,
        "rabbitmq_exchange": rabbitmq_exchange,
        "rabbitmq_routing_key": rabbitmq_routing_key,
        "max_retries": max_retries,
        "retry_delay": retry_delay,
        "connection_success": False,
        "publish_status": False,
    }
    return RabbitMQPublisher(**publisher_args)




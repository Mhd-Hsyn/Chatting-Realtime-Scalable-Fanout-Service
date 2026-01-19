from decouple import config
import urllib.parse

rabbitmq_host = config("RABBITMQ_HOST")
rabbitmq_port = config("RABBITMQ_PORT")
rabbitmq_username = config("RABBITMQ_USER")
rabbitmq_password = config("RABBITMQ_PASSWORD")
rabbitmq_document_process_quee = config("RABBITMQ_QUEE")
rabbitmq_document_process_exchange = config("RABBITMQ_EXCHANGE")
rabbitmq_document_process_routing_key = config("RABBITMQ_ROUTING_KEY")


redis_host= config("REDIS_HOST")
redis_port= config("REDIS_PORT")
redis_password= config("REDIS_PASSWORD")
redis_realtime_socket_db= config("REDIS_REALTIME_SOCKET_DB")

redis_password = urllib.parse.quote(redis_password)

redis_url = f'redis://:{redis_password}@{redis_host}:{redis_port}/{redis_realtime_socket_db}'

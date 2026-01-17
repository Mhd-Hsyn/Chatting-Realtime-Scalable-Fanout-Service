from decouple import config


rabbitmq_host = config("RABBITMQ_HOST")
rabbitmq_port = config("RABBITMQ_PORT")
rabbitmq_username = config("RABBITMQ_USER")
rabbitmq_password = config("RABBITMQ_PASSWORD")
rabbitmq_document_process_quee = config("RABBITMQ_QUEE")
rabbitmq_document_process_exchange = config("RABBITMQ_EXCHANGE")
rabbitmq_document_process_routing_key = config("RABBITMQ_ROUTING_KEY")

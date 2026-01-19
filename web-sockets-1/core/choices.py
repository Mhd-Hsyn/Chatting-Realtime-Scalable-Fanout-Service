from enum import Enum

class RealtimeEventChoices(str, Enum):
    """
    Registry of all Socket.IO / RabbitMQ Events.
    Value = The actual event string sent to socket/rabbitMQ
    """

    # 📡 PUBLIC ROOM EVENTS
    NEW_MESSAGE_ROOM = 'new_message'                           # 'New Message (Room)'

    # 🔔 PRIVATE USER EVENTS
    UNREAD_MESSAGE_COUNT_UPDATE = 'new_unread_message_count'   # 'Unread Count Update'
    NEW_MESSAGE_NOTIFICATION = 'new_message_notification'      # 'New Message Notification'



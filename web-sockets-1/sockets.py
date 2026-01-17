import logging
import socketio
from helpers import verify_jwt_token

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)


logger = logging.getLogger("socktet_server_1")

# Initialize Socket.IO server
sio_server = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins=[],
    logger=True,
    engineio_logger=True
)

# Wrap the server with an ASGI app
sio_app = socketio.ASGIApp(
    socketio_server=sio_server,
    socketio_path='socket.io'
)


# @sio_server.event
# async def connect(sid, environ, auth):
#     logger.info("connect is running")

#     print(f'{sid}: connected')
#     await sio_server.emit('connection_success', {'sid': sid})


# @sio_server.event
# async def join_channel(sid, data):
#     logger.info("join_channel is running")

    
#     if not isinstance(data, dict):
#         print(f"Invalid data format received: {data}")
#         return

#     # Log the received data for debugging
#     print(f"Received join_channel data: {data}")

#     channel_name = data.get('channel_name')
#     user_data = data.get('user_data')

#     if not channel_name or not user_data:
#         print(f"Missing channel_name or user_data in: {data}")
#         return

#     session_data = {'channel_name': channel_name, 'user_data': user_data}
#     await sio_server.save_session(sid, session_data)

#     if channel_name:
#         sio_server.enter_room(sid, channel_name)
#         await sio_server.emit('user_joined', {'user_data': user_data}, room=channel_name, skip_sid=sid)
#         print(f"\n\n JOIN SUCCESSFULLY ------- {user_data} \n\n")
#     else:
#         print(f"Error: Channel name is None. Cannot join room.")



@sio_server.event
async def connect(sid, environ, auth):
    """
    Robust Connect Handler
    Supports both Standard Auth (Frontend) and Headers (Postman)
    """
    print(f"\n--- New Connection Request: {sid} ---")
    
    # Debugging: Dekho k Headers me kia aa raha h
    # print(f"Headers (Environ): {environ}") 

    token = None

    # -----------------------------------------------------
    # Priority 1: Check Standard Auth (React/Frontend Style)
    # -----------------------------------------------------
    if auth:
        token = auth.get('token')
    
    # -----------------------------------------------------
    # Priority 2: Check Headers (Postman/Test Tool Style)
    # -----------------------------------------------------
    if not token:
        # Python 'environ' me headers usually 'HTTP_' prefix aur UPPERCASE k sath hotay hain
        # Agar tumne Postman me 'token' bheja h, to yahan 'HTTP_TOKEN' milega
        token = environ.get('HTTP_TOKEN')
        
        # Agar tumne 'Authorization' header use kia h
        if not token:
            auth_header = environ.get('HTTP_AUTHORIZATION')
            if auth_header:
                # 'Bearer xyz...' me se sirf token nikalo
                token = auth_header.split(' ')[1] if ' ' in auth_header else auth_header

    # -----------------------------------------------------
    # Verification Logic
    # -----------------------------------------------------
    if not token:
        print("❌ Rejecting: No Token Found")
        raise ConnectionRefusedError('Authentication failed: Token missing')

    # Verify Token (Apni JWT logic yahan call kro)
    user_payload = verify_jwt_token(token) # <--- Tumhara verify function
    
    if not user_payload:
        print("❌ Rejecting: Invalid Token")
        raise ConnectionRefusedError('Authentication failed: Invalid Token')

    # Success Flow
    user_id = user_payload.get('id') or user_payload.get('email')

    print("user_id ______________ ", user_id)
    
    await sio_server.save_session(sid, {
        'user_id': user_id,
        'user_data': user_payload
    })
    
    # Auto-join Personal Room
    user_room = f"user_{user_id}"
    sio_server.enter_room(sid, user_room)
    
    print(f"✅ User {user_id} Connected via {'Auth Dict' if auth else 'Headers'}")
    await sio_server.emit('connection_success', {'sid': sid})




@sio_server.event
async def join_channel(sid, data):
    # 1. Session data uthao
    session = await sio_server.get_session(sid)
    user_id = session.get('user_id')
    old_room = session.get('active_room')
    print("old_room __________ ", old_room)
    
    new_room = data.get('channel_name') # e.g., 'chat_55'
    print("new_room __________ ", new_room)

    if not new_room:
        return

    # 2. PURANA ROOM CHORO (Cleanup)
    # Agar user pehlay 'chat_44' me tha, usay wahan se nikalo
    if old_room and (old_room != new_room):
        sio_server.leave_room(sid, old_room)
        logger.info(f"User {user_id} left {old_room}")

    # 3. NAYA ROOM JOIN KRO
    sio_server.enter_room(sid, new_room)
    
    # 4. Session Update kro
    # Note: Hum poora session overwrite nhi kr rahay, sirf update kr rahay hain
    await sio_server.save_session(sid, {**session, 'active_room': new_room})

    logger.info(f"User {user_id} switched to {new_room}")
    
    # Optional: Notify others in that room
    # await sio_server.emit('user_status', {'id': user_id, 'status': 'online'}, room=new_room)



@sio_server.event
async def send_message(sid, data):
    """
    Handle messages sent by a user to a channel.
    """
    session = await sio_server.get_session(sid)
    channel_name = session.get('channel_name')
    user_data = session.get('user_data')

    message = data.get('message')
    if not message or not channel_name:
        return

    # Broadcast the message to the channel
    await sio_server.emit('new_message', {'user_data': user_data, 'message': message}, room=channel_name)
    print(f'Message from {user_data} in channel {channel_name}: {message}')




@sio_server.event
async def leave_channel(sid, data):
    logger.info("leave_channel is running")

    """
    Allow a user to leave a channel and notify other members.
    """
    try:
        # Retrieve session data
        session = await sio_server.get_session(sid)
    except KeyError:
        print(f"Session not found for SID {sid}")
        return

    # Extract channel name and user data from the session
    channel_name = session.get('channel_name')
    user_data = session.get('user_data')
    if not channel_name:
        channel_name = data.get('channel_name')
    if channel_name:
        # Notify other users in the room and leave the room
        sio_server.leave_room(sid, channel_name)
        await sio_server.emit('user_left', {'user_data': user_data}, room=channel_name)
        print(f'User {user_data} left channel {channel_name}')
        print(f"\n\n LEFT SUCCESSFULLY ------- {user_data} \n\n")
    else:
        print(f"No channel found for SID {sid}")


@sio_server.event
async def disconnect(sid):
    """
    Handle disconnection and notify the channel.
    """
    session = await sio_server.get_session(sid)
    channel_name = session.get('channel_name')
    user_data = session.get('user_data')

    if channel_name:
        sio_server.leave_room(sid, channel_name)
        await sio_server.emit('user_left', {'user_data': user_data}, room=channel_name)
    print(f'{sid} disconnected')



###########################################################################



async def send_notification_to_user(user_id: str, notification_data: dict):
    """
    Ye function tumhari FastAPI ki API route se call hoga.
    Is waqt tumhare paas 'sid' nahi hota, sirf 'user_id' hoti h.
    """
    if not user_id:
        return

    target_room = f"user_{user_id}"

    # Hum direct ROOM me bhej rahay hain, SID ki zaroorat nahi
    await sio_server.emit(
        event='new_user_primary_notification', 
        data=notification_data, 
        room=target_room
    )
    print(f"Push Notification sent to {target_room}")


async def send_unread_notification_count_to_user(user_id: str, notification_data: dict):
    """
    Ye function tumhari FastAPI ki API route se call hoga.
    Is waqt tumhare paas 'sid' nahi hota, sirf 'user_id' hoti h.
    """
    if not user_id:
        return

    target_room = f"user_{user_id}"
    
    # Hum direct ROOM me bhej rahay hain, SID ki zaroorat nahi
    await sio_server.emit(
        event='new_user_unread_notification_count', 
        data=notification_data, 
        room=target_room
    )
    print(f"Push Notification sent to {target_room}")




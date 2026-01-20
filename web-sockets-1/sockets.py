import logging
import socketio
from helpers import verify_jwt_token
from core.config import (
    redis_url
)
from redis_utils import (
    set_user_active_chat_room,
    remove_user_active_chat_room
)

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)


logger = logging.getLogger("socktet_server_1")


# =========================================================
# 1. REDIS MANAGER SETUP (The Magic Line)
# =========================================================
# Ye manager tumhare sessions aur rooms ko Redis me handle karega
# 'write_only=False' ka matlab h ye server Redis se read b karega
print(f"Connecting to: {redis_url}")
mgr = socketio.AsyncRedisManager(redis_url,write_only=False)

# =========================================================
# 2. SERVER INITIALIZATION WITH MANAGER
# =========================================================
sio_server = socketio.AsyncServer(
    client_manager=mgr,
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




##################### JWT websockets #####################


@sio_server.event
async def connect(sid, environ, auth):
    """
    Robust Connect Handler
    Supports both Standard Auth (Frontend) and Headers (Postman)

    server_sockets = {
    "sid_xyz_123": {  # <--- Ye SID hai
        "session": {  # <--- Ye wo data h jo tumne save_session se dala
            "user_id": 101,
            "user_data": {"name": "Ali", "role": "admin"},
            "active_chat_room": "case_555"
        },
        "rooms": ["user_101", "case_555"] # <--- User kin rooms me h
    },

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



# @sio_server.event
# async def join_channel(sid, data):

# OLD

#     # 1. Session uthao (Jo Connect k waqt bana tha)
#     session = await sio_server.get_session(sid)
#     user_id = session.get('user_id') 
    
#     # 2. Check kro user pehlay kis channel me tha
#     # (Ab hum 'channel_name' use kr rahay hain taake send_message k sath match ho)
#     old_channel = session.get('channel_name') 
    
#     new_channel = data.get('channel_name')

#     if not new_channel:
#         return

#     # 3. CONTEXT SWITCHING (Purana choro, Naya pakro)
#     if old_channel and old_channel != new_channel:
#         sio_server.leave_room(sid, old_channel)
#         logger.info(f"User {user_id} left {old_channel}")

#     # 4. Enter New Room
#     sio_server.enter_room(sid, new_channel)
    
#     # 5. UPDATE SESSION (Securely)
#     # **session ka matlab h purana data (user_id etc) retain kro
#     await sio_server.save_session(sid, {**session, 'channel_name': new_channel})

#     logger.info(f"User {user_id} switched context to {new_channel}")




@sio_server.event
async def join_channel(sid, data):
    session = await sio_server.get_session(sid)
    user_id = session.get('user_id') # User ID zaroori h
    new_room = data.get('channel_name')
    
    if not new_room: return

    # 1. Old Room handling (Slot 1)
    old_room = session.get('active_chat_room') 
    if old_room and old_room != new_room:
        sio_server.leave_room(sid, old_room)

    # 2. Join New Room
    sio_server.enter_room(sid, new_room)
    
    # 3. Session Update (RAM)
    await sio_server.save_session(sid, {
        **session, 
        'active_chat_room': new_room 
    })

    # 4. --- 🔥 REDIS PRESENCE UPDATE (THE FIX) ---
    if user_id:
        await set_user_active_chat_room(user_id, new_room)
        print(f"✅ Redis Updated: User {user_id} is watching {new_room}")

    print(f"Joined Slot 1: {new_room}")


@sio_server.event
async def join_channel2(sid, data):
    """
    Any other channel
    {
        'user_id': 101,
        'user_data': {...},
        
        # KEY (Naam)           # VALUE (Asli Room ID)
        'active_chat_room':    'case_555',
        
        'active_alert_room':   None
    }
    """
    session = await sio_server.get_session(sid)
    new_room = data.get('channel_name')
    
    if not new_room: return

    # --- SLOT 2 LOGIC ---
    # Sirf Slot 2 wala purana room check kro
    old_room = session.get('active_alert_room') 

    # Logic bilkul same h, bas variable alag h
    if old_room and old_room != new_room:
        sio_server.leave_room(sid, old_room)
        print(f"Switched Slot 2: Left {old_room}")

    sio_server.enter_room(sid, new_room)
    
    # Session update (Save specifically to 'active_alert_room')
    await sio_server.save_session(sid, {
        **session, 
        'active_alert_room': new_room 
    })

    print("session _____________________ ", session)
    
    print(f"Joined Slot 2: {new_room}")



@sio_server.event
async def send_message(sid, data):
    """
    Handle messages sent by a user to a channel.
    {
        'user_id': 101,
        'user_data': {...},
        
        # KEY (Naam)           # VALUE (Asli Room ID)
        'active_chat_room':    'case_555',
        
        'active_alert_room':   None
    }
    """
    session = await sio_server.get_session(sid)

    # --- BUG FIX HERE ---
    # Humne key ka naam 'active_chat_room' rakha tha, 'channel_name' nahi.
    # Usually user message "Chat Slot" me bhejta hai, Alerts slot me nahi.
    current_room = session.get('active_chat_room') 

    user_data = session.get('user_data')
    message = data.get('message')

    if not message:
        return

    if not current_room:
        await sio_server.emit('error', {'msg': 'Please join a chat room first'}, to=sid)
        return

    # Broadcast the message to the channel
    # Yahan ham wahi data bhej rahay hain jo frontend ko chahiye
    response_payload = {
        'user_data': user_data, 
        'message': message,
        'channel_name': current_room # Frontend ko pata chalay ye kis room ka msg h
    }
    await sio_server.emit('new_message', response_payload, room=current_room)
    # Logs for debugging
    print(f'Message sent to {current_room}: {message}')



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
    # 1. Session uthao
    try:
        session = await sio_server.get_session(sid)
    except:
        return # Agar session hi nahi h to kuch krne ki zaroorat nahi

    user_data = session.get('user_data')
    user_id = session.get('user_id')

    # Tumhare join_channel me 'active_chat_room' use ho raha h
    # Aur join_channel2 me 'active_alert_room' use ho raha h
    
    chat_room = session.get('active_chat_room')
    alert_room = session.get('active_alert_room')

    # 1. Redis Presence Clean kro (Sab se Zaroori)
    if user_id:
        await remove_user_active_chat_room(user_id)
        print(f"🧹 Redis Cleaned: User {user_id} presence removed")

    # 2. Chat Room se nikalo & Notify kro
    if chat_room:
        sio_server.leave_room(sid, chat_room)
        # Optional: Agar tum chahte ho k dosto ko pata chale wo offline ho gaya
        # await sio_server.emit('user_left', {'user_data': user_data}, room=chat_room)
        print(f"User left Chat Room: {chat_room}")

    # 3. Alert Room se nikalo
    if alert_room:
        sio_server.leave_room(sid, alert_room)
        print(f"User left Alert Room: {alert_room}")

    print(f'❌ {sid} disconnected fully')



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




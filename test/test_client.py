import socketio
from config import CHANNEL_NAME
from helpers import generate_jwt_token

# 1. Token Generate kro (Make sure Secret Key matches Server's .env)
print("🔑 Generating Token...")
YOUR_JWT_TOKEN_HERE = generate_jwt_token() 
print(f"Token: {YOUR_JWT_TOKEN_HERE[:15]}... (Truncated)")

# 2. Client Setup (No MsgPack for now)
sio = socketio.Client()

# --- EVENTS ---

@sio.event
def connect():
    print("✅ Connected to Server!")
    
    # Connection bantay hi Channel Join ki request bhejo
    channel_to_join = CHANNEL_NAME
    print(f"➡️ Joining Channel: {channel_to_join}...")
    
    sio.emit('join_channel', {'channel_name': channel_to_join})
    print(f"✅ Successfully Joined Channel: {channel_to_join}")


@sio.event
def new_message(data):
    # Jab koi message ayega to yahan print hoga
    print("\n📩 New Message Received:")
    print(f"   Room: {data.get('room_id')}")
    print(f"   Message: {data.get('message', {}).get('text')}")
    print(f"   Message: {data.get('message')}")
    print("-" * 30)


@sio.event
def new_message_notification(data):
    print("\n🔔 Notification Popup Received:")
    print(f"   Room: {data.get('room_id')}")
    print(f"   Data: {data.get('message')}")
    print("-" * 30)

@sio.event
def new_unread_message_count(data):
    print("\n🔴 Unread Count Update:")
    print(f"   New Count: {data.get('unread_count')}")
    print("-" * 30)


@sio.event
def connect_error(data):
    print(f"❌ Connection Failed: {data}")

@sio.event
def disconnect():
    print("⚠️ Disconnected from server")

# --- EXECUTION ---

try:
    print("⏳ Connecting to localhost:9009...")
    sio.connect(
        'http://localhost:9009', 
        auth={'token': YOUR_JWT_TOKEN_HERE}
    )
    
    # Script ko zinda rakhne k liye wait kro
    sio.wait()

except KeyboardInterrupt:
    print("\n🛑 Stopping Client...")
    sio.disconnect()
    
except Exception as e:
    print(f"💥 Error: {e}")
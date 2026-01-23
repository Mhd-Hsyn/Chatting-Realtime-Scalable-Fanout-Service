import redis.asyncio as redis

from core.config import (
    redis_url
)
redis_client = redis.from_url(redis_url, decode_responses=True)

async def set_user_active_chat_room(user_id, room_id):
    """Redis me likho: User 101 abhi Room 555 me h"""
    key = f"active_chat_room_presence:{user_id}"
    await redis_client.set(key, str(room_id))

async def get_user_active_chat_room(user_id):
    """Redis se poocho: User 101 abhi kahan h?"""
    key = f"active_chat_room_presence:{user_id}"
    return await redis_client.get(key)

async def remove_user_active_chat_room(user_id):
    """Jab user disconnect ho ya room chore"""
    key = f"active_chat_room_presence:{user_id}"
    await redis_client.delete(key)

# Tumhara purana function bhi update krna pary ga taake wo bhi expire ho
# async def refresh_user_chat_presence(user_id):
#     """Agar wo kisi chat room me h to usay b refresh kro"""
#     key = f"active_presence:{user_id}"
#     # Check kro agr key exist krti h tabhi refresh kro
#     if await redis_client.exists(key):
#         await redis_client.expire(key, ONLINE_TTL)


ONLINE_TTL = 100 # Seconds

async def mark_user_online(user_id):
    """
    Ye function Create b karega aur Update b.
    Connect pr b yehi call kro, Heartbeat pr b yehi call kro.
    """
    key = f"online_user:{user_id}"
    
    # "1" ka matlab: Hamein value se garz nahi, bas key honi chahiye.
    # ex=ONLINE_TTL: Ye expiry set/reset kar dega.
    await redis_client.set(key, "1", ex=ONLINE_TTL)


async def remove_user_online(user_id):
    """Disconnect pr foran offline kro"""
    key = f"online_user:{user_id}"
    await redis_client.delete(key)



SECTION_TTL = 100 # Seconds

async def set_user_ui_section(user_id, section_name):
    """Redis me save kro k user abhi kis Tab pr h"""
    key = f"ui_section:{user_id}"
    await redis_client.set(key, section_name, ex=SECTION_TTL)

async def get_user_ui_section(user_id):
    """Django (Publisher) k liye: Pata kro user kis Tab pr h"""
    key = f"ui_section:{user_id}"
    return await redis_client.get(key)


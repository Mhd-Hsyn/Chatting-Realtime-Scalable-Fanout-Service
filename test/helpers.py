import jwt
from config import (
    EMAIL,
    USER_ID,
    JWT_SECRET_KEY,
    ALGORITHM
)


def generate_jwt_token(
    user_id= USER_ID, 
    email=EMAIL
):
    payload = {
        'id': user_id, 
        'email': email
    }
    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=ALGORITHM)
    return token

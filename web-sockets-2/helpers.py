import jwt
from decouple import config

# Secret key wahi honi chahiye jo Login API me use ki thi
JWT_SECRET_KEY = config("JWT_SECRET_KEY") 
ALGORITHM = "HS256"

def verify_jwt_token(token):
    try:
        # 1. Agar 'Bearer ' prefix hai to hata do
        if token.startswith('Bearer '):
            token = token.split(' ')[1]
            
        # 2. Decode Token
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[ALGORITHM])
        return payload # Isme usually {'user_id': 1, 'email': '...'} hota h
        
    except jwt.ExpiredSignatureError:
        print("Token expired")
        return None
    except jwt.InvalidTokenError:
        print("Invalid token")
        return None


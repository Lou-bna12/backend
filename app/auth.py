# app/auth.py
from datetime import datetime, timedelta
from typing import Optional
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
import os

# Configuration (à déplacer dans .env en production)
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

security = HTTPBearer()

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Créer un token JWT (compatible avec votre système existant)"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Vérifier un token JWT"""
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Token invalide")
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Token invalide ou expiré")

# Compatibilité avec votre système existant
def get_current_user_email(token: str = Depends(verify_token)):
    """Récupérer l'email de l'utilisateur depuis le token"""
    return token.get("email")

def create_login_response(user_data: dict, use_jwt: bool = True):
    """Créer une réponse de login compatible avec les deux systèmes"""
    response = {
        "success": True,
        "message": "Connexion réussie",
        "user_id": user_data.get("id"),
        "email": user_data.get("email"),
        "full_name": user_data.get("full_name"),
        "role": user_data.get("role")
    }
    
    if use_jwt:
        # Ajouter le token JWT
        token_data = {"sub": str(user_data.get("id")), "email": user_data.get("email")}
        access_token = create_access_token(data=token_data)
        response["access_token"] = access_token
        response["token_type"] = "bearer"
    
    return response
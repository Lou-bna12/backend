# app/utils.py
import hashlib
import random
import string
import logging
from datetime import datetime, timedelta
from typing import Optional
import json

# Configuration du logging
logger = logging.getLogger(__name__)

def hash_password(password: str) -> str:
    """Hash simple pour développement - Compatible avec votre ancien code"""
    return hashlib.sha256(password.encode()).hexdigest()

def generate_order_number() -> str:
    """Génère un numéro de commande unique"""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"CMD-{timestamp}-{random_str}"

def validate_phone_number(phone: Optional[str]) -> bool:
    """Valider un numéro de téléphone algérien"""
    if not phone:
        return True
    # Format: +213XXXXXXXXX ou 0XXXXXXXXX
    phone = phone.strip()
    if phone.startswith('+213'):
        return len(phone) == 13 and phone[4:].isdigit()
    elif phone.startswith('0'):
        return len(phone) == 10 and phone[1:].isdigit()
    return False

def row_to_dict(row):
    """Convertir une row SQLite en dictionnaire - Compatibilité"""
    if hasattr(row, '_asdict'):  # Pour les objets SQLAlchemy
        return row._asdict()
    elif hasattr(row, '__dict__'):  # Pour les objets ORM
        return {k: v for k, v in row.__dict__.items() if not k.startswith('_')}
    elif row:  # Pour les résultats SQLite
        return dict(row)
    return None

def create_response(success: bool, message: str, **kwargs):
    """Créer une réponse standardisée"""
    response = {
        "success": success,
        "message": message,
        "timestamp": datetime.now().isoformat()
    }
    response.update(kwargs)
    return response
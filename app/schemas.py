# app/schemas.py
from pydantic import BaseModel, EmailStr, validator, Field
from typing import Optional, List, Dict
from datetime import datetime
from app.utils import validate_phone_number

# ==================== SCHÉMAS UTILISATEUR ====================
class UserBase(BaseModel):
    email: EmailStr
    phone: Optional[str] = None
    full_name: str = Field(..., min_length=2, max_length=100)
    role: str = "customer"

    @validator('phone')
    def validate_phone(cls, v):
        if v and not validate_phone_number(v):
            raise ValueError("Numéro de téléphone algérien invalide. Format: +213XXXXXXXXX ou 0XXXXXXXXX")
        return v

    @validator('role')
    def validate_role(cls, v):
        if v not in ["customer", "shop", "admin"]:
            raise ValueError("Rôle invalide. Doit être: customer, shop ou admin")
        return v

class UserCreate(UserBase):
    password: str = Field(..., min_length=6, max_length=100)

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(UserBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

# ==================== SCHÉMAS PRODUIT ====================
class ProductBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=200)
    description: Optional[str] = None
    price: float = Field(..., gt=0)
    stock: int = Field(0, ge=0)
    category: str = "general"

class ProductCreate(ProductBase):
    pass

class ProductResponse(ProductBase):
    id: int
    shop_id: int
    
    class Config:
        from_attributes = True

# ==================== SCHÉMAS COMMANDE ====================
class OrderItemCreate(BaseModel):
    product_id: int
    quantity: int = Field(..., gt=0, le=100)

class MultiOrderCreate(BaseModel):
    items: List[OrderItemCreate]
    customer_phone: str
    customer_email: Optional[EmailStr] = None
    delivery_address: str = Field(..., min_length=5)
    notes: Optional[str] = None

    @validator('customer_phone')
    def validate_customer_phone(cls, v):
        if not validate_phone_number(v):
            raise ValueError("Numéro de téléphone algérien invalide. Format: +213XXXXXXXXX ou 0XXXXXXXXX")
        return v

class OrderStatusUpdate(BaseModel):
    status: str
    
    @validator('status')
    def validate_status(cls, v):
        valid_statuses = ["pending", "confirmed", "shipped", "delivered", "cancelled"]
        if v not in valid_statuses:
            raise ValueError(f"Statut invalide. Doit être l'un de: {', '.join(valid_statuses)}")
        return v

# ==================== SCHÉMAS NOTIFICATION ====================
class NotificationBase(BaseModel):
    user_id: int
    type: str = "system"
    title: str = Field(..., min_length=1)
    message: str = Field(..., min_length=1)
    link: Optional[str] = ""
    icon: Optional[str] = "bell"
    data: Optional[Dict] = {}

class NotificationCreate(NotificationBase):
    pass

class NotificationResponse(NotificationBase):
    id: int
    read: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

# ==================== SCHÉMAS RÉPONSE STANDARD ====================
class SuccessResponse(BaseModel):
    success: bool
    message: str
    timestamp: str
    
class ErrorResponse(BaseModel):
    success: bool
    message: str
    error: Optional[str] = None
    timestamp: str
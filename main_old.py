from fastapi import FastAPI, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import uvicorn
import hashlib  # Utiliser hashlib au lieu de bcrypt pour simplifier

from app.database import engine, get_db
from app import models

# Créer les tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Marketplace Alger API")

# Modèles Pydantic
class UserCreate(BaseModel):
    email: str
    password: str
    full_name: str

class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str
    
    class Config:
        from_attributes = True  # Remplace orm_mode dans Pydantic V2

class ProductCreate(BaseModel):
    name: str
    description: Optional[str] = None
    price: float
    stock: int = 0

class ProductResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    price: float
    stock: int
    shop_id: int
    
    class Config:
        from_attributes = True

# Fonction de hachage simple (pour développement seulement)
def hash_password(password: str) -> str:
    """Hachage simple avec SHA256 - À remplacer par bcrypt en production"""
    return hashlib.sha256(password.encode()).hexdigest()

# Routes
@app.get("/")
def read_root():
    return {"message": "Marketplace Alger API is running!", "version": "3.0"}

@app.post("/register", response_model=UserResponse)
def register(user: UserCreate, db: Session = Depends(get_db)):
    # Vérifier si l'email existe
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email déjà utilisé")
    
    # Créer l'utilisateur avec mot de passe haché
    hashed_password = hash_password(user.password)
    db_user = models.User(
        email=user.email,
        password=hashed_password,  # Stocker le hash
        full_name=user.full_name
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    # Créer automatiquement un shop
    shop = models.Shop(name=f"Boutique de {user.full_name}", owner_id=db_user.id)
    db.add(shop)
    db.commit()
    
    return db_user

@app.post("/login")
def login(email: str, password: str, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.email == email).first()
    if not db_user:
        raise HTTPException(status_code=401, detail="Email ou mot de passe incorrect")
    
    # Vérifier le mot de passe
    hashed_input = hash_password(password)
    if hashed_input != db_user.password:
        raise HTTPException(status_code=401, detail="Email ou mot de passe incorrect")
    
    return {"message": "Connexion réussie", "user_id": db_user.id}

@app.post("/products", response_model=ProductResponse)
def create_product(
    product: ProductCreate,
    db: Session = Depends(get_db)
):
    # Pour simplifier, prendre le premier shop
    shop = db.query(models.Shop).first()
    if not shop:
        raise HTTPException(status_code=404, detail="Aucun shop trouvé")
    
    db_product = models.Product(
        name=product.name,
        description=product.description,
        price=product.price,
        stock=product.stock,
        shop_id=shop.id
    )
    
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product

@app.get("/products", response_model=list[ProductResponse])
def get_products(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    products = db.query(models.Product).offset(skip).limit(limit).all()
    return products

@app.get("/products/{product_id}", response_model=ProductResponse)
def get_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Produit non trouvé")
    return product

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

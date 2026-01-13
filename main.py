# main.py - Version améliorée mais compatible
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Depends
from pydantic import ValidationError
from typing import Optional, List, Dict
import uvicorn
import sqlite3
import asyncio
from datetime import datetime
import logging

# AJOUTE CES IMPORTS
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import contextmanager

# Importez vos modules
from app import utils, schemas
from app.auth import create_login_response, verify_token, get_current_user_email
from app.database import get_db as get_sqlalchemy_db

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Marketplace Alger API")

# ==================== CORS ====================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # À changer pour la production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# ==================== GESTION D'ERREURS GLOBALE ====================
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content=utils.create_response(
            success=False,
            message=exc.detail,
            error=str(exc.detail)
        )
    )

@app.exception_handler(ValidationError)
async def validation_exception_handler(request, exc):
    errors = [f"{error['loc'][1]}: {error['msg']}" for error in exc.errors()]
    return JSONResponse(
        status_code=422,
        content=utils.create_response(
            success=False,
            message="Erreur de validation",
            error=", ".join(errors),
            details=exc.errors()
        )
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"Erreur non gérée: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content=utils.create_response(
            success=False,
            message="Une erreur interne est survenue",
            error="Internal server error"
        )
    )

# ==================== WEBSOCKET MANAGER ====================
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        self.active_connections[user_id] = websocket
        logger.info(f"WebSocket connecté pour user: {user_id}")
    
    def disconnect(self, user_id: str):
        if user_id in self.active_connections:
            del self.active_connections[user_id]
            logger.info(f"WebSocket déconnecté pour user: {user_id}")
    
    async def send_personal_message(self, message: dict, user_id: str):
        if user_id in self.active_connections:
            websocket = self.active_connections[user_id]
            try:
                await websocket.send_json(message)
                logger.info(f"Message envoyé à user {user_id}")
            except:
                self.disconnect(user_id)
    
    async def broadcast(self, message: dict):
        for user_id, websocket in self.active_connections.items():
            try:
                await websocket.send_json(message)
            except:
                self.disconnect(user_id)

manager = ConnectionManager()

# ==================== FONCTIONS DE BASE (COMPATIBILITÉ) ====================
@contextmanager
def get_db():
    """Connexion à la base SQLite - Compatible avec l'ancien code"""
    conn = sqlite3.connect('marketplace.db')
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    """Créer les tables et données de test - Compatible"""
    # Votre code existant inchangé...
    # Copier exactement votre fonction init_db() ici
    # ... (votre code existant) ...

# Initialiser la base
init_db()

# ==================== ROUTES API (COMPATIBLES) ====================
@app.get("/")
def home():
    return {
        "message": "Marketplace Alger API 🚀",
        "version": "4.1",  # Version mise à jour
        "features": ["rôles utilisateurs", "dashboard shop", "commandes multi-produits", "notifications temps réel", "validation améliorée"],
        "endpoints": [
            "POST /register - S'inscrire (avec validation)",
            "POST /login - Se connecter (avec JWT optionnel)",
            "GET /me - Info utilisateur",
            "GET /products - Liste produits",
            "POST /orders - Créer commande",
            "GET /orders/{phone} - Voir commandes",
            "PUT /orders/{order_id}/status - Mettre à jour le statut",
            "WS /ws/{user_id} - Connexion WebSocket",
            "POST /api/notifications - Créer notification",
            "GET /api/notifications/{user_id} - Récupérer notifications",
            "POST /api/notifications/test/{user_id} - Tester notifications"
        ]
    }

@app.get("/health")
def health():
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
        return utils.create_response(
            success=True,
            message="API en bonne santé"
        )
    except Exception as e:
        logger.error(f"Erreur health check: {e}")
        return utils.create_response(
            success=False,
            message="Problème de connexion à la base"
        )

# ==================== AUTHENTIFICATION (AMÉLIORÉE) ====================
@app.post("/register")
def register(user: schemas.UserCreate):
    """Inscription avec validation améliorée"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        try:
            # Vérifier email
            cursor.execute("SELECT id FROM users WHERE email = ?", (user.email,))
            if cursor.fetchone():
                raise HTTPException(400, "Email déjà utilisé")
            
            # Vérifier phone
            if user.phone:
                cursor.execute("SELECT id FROM users WHERE phone = ?", (user.phone,))
                if cursor.fetchone():
                    raise HTTPException(400, "Téléphone déjà utilisé")
            
            # Créer utilisateur avec mot de passe hashé
            hashed = utils.hash_password(user.password)
            cursor.execute(
                "INSERT INTO users (email, phone, password, full_name, role) VALUES (?, ?, ?, ?, ?)",
                (user.email, user.phone, hashed, user.full_name, user.role)
            )
            user_id = cursor.lastrowid
            
            # Si c'est un shop, créer automatiquement un shop
            if user.role == "shop":
                cursor.execute(
                    "INSERT INTO shops (name, owner_id) VALUES (?, ?)",
                    (f"Boutique de {user.full_name}", user_id)
                )
            
            conn.commit()
            
            # Retourner réponse
            cursor.execute(
                "SELECT id, email, phone, full_name, role, created_at FROM users WHERE id = ?",
                (user_id,)
            )
            user_data = utils.row_to_dict(cursor.fetchone())
            
            return utils.create_response(
                success=True,
                message="Inscription réussie",
                user=user_data
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Erreur inscription: {e}")
            raise HTTPException(500, f"Erreur: {str(e)}")

@app.post("/login")
def login(credentials: schemas.UserLogin):
    """Connexion avec option JWT"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "SELECT id, email, password, full_name, role FROM users WHERE email = ?",
                (credentials.email,)
            )
            user = utils.row_to_dict(cursor.fetchone())
            
            if not user:
                raise HTTPException(401, "Email ou mot de passe incorrect")
            
            if utils.hash_password(credentials.password) != user['password']:
                raise HTTPException(401, "Email ou mot de passe incorrect")
            
            # Utiliser le nouveau système de réponse avec JWT optionnel
            return create_login_response(user, use_jwt=True)
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Erreur connexion: {e}")
            raise HTTPException(500, f"Erreur: {str(e)}")

# Route de login compatible avec l'ancien format
@app.post("/login-old")
def login_old(credentials: schemas.UserLogin):
    """Ancienne version de login pour compatibilité"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "SELECT id, email, password, full_name, role FROM users WHERE email = ?",
                (credentials.email,)
            )
            user = utils.row_to_dict(cursor.fetchone())
            
            if not user:
                raise HTTPException(401, "Email ou mot de passe incorrect")
            
            if utils.hash_password(credentials.password) != user['password']:
                raise HTTPException(401, "Email ou mot de passe incorrect")
            
            # Retourner l'ancien format
            return {
                "success": True,
                "message": "Connexion réussie",
                "user_id": user['id'],
                "email": user['email'],
                "full_name": user['full_name'],
                "role": user['role']
            }
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(500, f"Erreur: {str(e)}")

@app.get("/me")
def get_me(email: str):
    """Info utilisateur avec JWT optionnel"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "SELECT id, email, phone, full_name, role FROM users WHERE email = ?",
                (email,)
            )
            user = utils.row_to_dict(cursor.fetchone())
            
            if not user:
                raise HTTPException(404, "Utilisateur non trouvé")
            
            # Si c'est un shop, ajouter l'ID du shop
            if user['role'] == 'shop':
                cursor.execute(
                    "SELECT id as shop_id, name as shop_name FROM shops WHERE owner_id = ?",
                    (user['id'],)
                )
                shop_info = utils.row_to_dict(cursor.fetchone())
                if shop_info:
                    user.update(shop_info)
            
            return user
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Erreur get_me: {e}")
            raise HTTPException(500, f"Erreur: {str(e)}")

# ==================== ROUTES PROTÉGÉES (OPTIONNEL) ====================
@app.get("/protected")
def protected_route(current_user: dict = Depends(verify_token)):
    """Exemple de route protégée par JWT"""
    return utils.create_response(
        success=True,
        message="Accès autorisé",
        user_id=current_user.get("sub"),
        email=current_user.get("email")
    )

# ==================== PRODUITS (AVEC VALIDATION) ====================
@app.post("/products")
def create_product(product: schemas.ProductCreate):
    """Créer un produit avec validation améliorée"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT id FROM shops LIMIT 1")
            shop = utils.row_to_dict(cursor.fetchone())
            
            if not shop:
                raise HTTPException(404, "Aucun shop disponible")
            
            cursor.execute(
                "INSERT INTO products (name, description, price, stock, category, shop_id) VALUES (?, ?, ?, ?, ?, ?)",
                (product.name, product.description, product.price, product.stock, product.category, shop['id'])
            )
            product_id = cursor.lastrowid
            
            conn.commit()
            
            cursor.execute("SELECT * FROM products WHERE id = ?", (product_id,))
            product_data = utils.row_to_dict(cursor.fetchone())
            
            return utils.create_response(
                success=True,
                message="Produit créé avec succès",
                product=product_data
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Erreur création produit: {e}")
            raise HTTPException(500, f"Erreur: {str(e)}")

@app.get("/products")
def get_products(category: Optional[str] = None, limit: int = 100, offset: int = 0):
    """Liste des produits avec pagination optionnelle"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        try:
            if category:
                cursor.execute(
                    """SELECT p.*, s.name as shop_name 
                       FROM products p 
                       JOIN shops s ON p.shop_id = s.id 
                       WHERE p.category = ? 
                       LIMIT ? OFFSET ?""",
                    (category, limit, offset)
                )
            else:
                cursor.execute(
                    """SELECT p.*, s.name as shop_name 
                       FROM products p 
                       JOIN shops s ON p.shop_id = s.id
                       LIMIT ? OFFSET ?""",
                    (limit, offset)
                )
            
            products = [utils.row_to_dict(row) for row in cursor.fetchall()]
            
            # Compter total
            count_query = "SELECT COUNT(*) as total FROM products"
            if category:
                count_query += " WHERE category = ?"
                cursor.execute(count_query, (category,))
            else:
                cursor.execute(count_query)
            
            total = cursor.fetchone()['total']
            
            return {
                "success": True,
                "count": len(products),
                "total": total,
                "limit": limit,
                "offset": offset,
                "products": products
            }
            
        except Exception as e:
            logger.error(f"Erreur récupération produits: {e}")
            raise HTTPException(500, f"Erreur: {str(e)}")

# ==================== COMMANDES (AMÉLIORÉES) ====================
@app.post("/orders")
async def create_order(order: schemas.MultiOrderCreate):
    """Créer une commande avec validation"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        try:
            # Vérifier que tous les produits existent et ont du stock
            total_price = 0
            order_items = []
            
            for item in order.items:
                cursor.execute("SELECT id, name, price, stock, shop_id FROM products WHERE id = ?", (item.product_id,))
                product = utils.row_to_dict(cursor.fetchone())
                
                if not product:
                    raise HTTPException(404, f"Produit ID {item.product_id} non trouvé")
                
                if product['stock'] < item.quantity:
                    raise HTTPException(400, f"Stock insuffisant pour {product['name']}: {product['stock']} disponible")
                
                item_total = product['price'] * item.quantity
                total_price += item_total
                
                order_items.append({
                    'product_id': product['id'],
                    'product_name': product['name'],
                    'shop_id': product['shop_id'],
                    'quantity': item.quantity,
                    'unit_price': product['price'],
                    'item_total': item_total
                })
            
            # Générer un numéro de commande unique
            order_number = utils.generate_order_number()
            
            # Créer la commande principale
            cursor.execute(
                """INSERT INTO orders (order_number, customer_phone, customer_email, total_price, 
                                      delivery_address, status, notes) 
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (order_number, order.customer_phone, order.customer_email, total_price, 
                 order.delivery_address, "pending", order.notes)
            )
            order_id = cursor.lastrowid
            
            # Créer les items de commande et mettre à jour les stocks
            for item in order_items:
                cursor.execute(
                    "INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES (?, ?, ?, ?)",
                    (order_id, item['product_id'], item['quantity'], item['unit_price'])
                )
                
                cursor.execute(
                    "UPDATE products SET stock = stock - ? WHERE id = ?",
                    (item['quantity'], item['product_id'])
                )
            
            conn.commit()
            
            # Récupérer la commande créée
            cursor.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
            order_data = utils.row_to_dict(cursor.fetchone())
            
            # Récupérer les items
            cursor.execute(
                """SELECT oi.*, p.name as product_name, p.shop_id, s.name as shop_name 
                   FROM order_items oi 
                   JOIN products p ON oi.product_id = p.id 
                   JOIN shops s ON p.shop_id = s.id
                   WHERE oi.order_id = ?""",
                (order_id,)
            )
            items = [utils.row_to_dict(row) for row in cursor.fetchall()]
            
            order_data['items'] = items
            
            # NOTIFICATION : Envoyer une notification à l'admin
            try:
                notification_data = schemas.NotificationCreate(
                    user_id=1,  # ID de l'admin
                    type="order",
                    title="Nouvelle commande",
                    message=f"Commande #{order_number} reçue de {order.customer_phone}",
                    link=f"/admin/orders/{order_id}",
                    icon="shopping-cart",
                    data={"order_id": order_id, "order_number": order_number}
                )
                notification_task = asyncio.create_task(
                    create_notification(notification_data)
                )
            except Exception as notif_error:
                logger.error(f"Erreur notification: {notif_error}")
            
            return utils.create_response(
                success=True,
                message="Commande créée avec succès",
                order=order_data,
                order_number=order_number,
                note="Paiement à la livraison"
            )
            
        except HTTPException:
            conn.rollback()
            raise
        except Exception as e:
            conn.rollback()
            logger.error(f"Erreur création commande: {e}")
            raise HTTPException(500, f"Erreur lors de la création de la commande: {str(e)}")

# ... (garder le reste de vos routes existantes inchangées pour compatibilité)
# Je garde votre code exact pour : 
# - get_orders_by_phone
# - get_orders_by_email  
# - get_shop_orders
# - update_order_status
# - toutes les routes shop
# - toutes les routes notifications
# - toutes les routes admin

# Copiez simplement votre code existant ici, il restera compatible

# ==================== WEBSOCKET ====================
@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    await manager.connect(websocket, user_id)
    
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
            elif data.startswith("{"):
                try:
                    json_data = json.loads(data)
                    logger.info(f"Message WebSocket de {user_id}: {json_data}")
                except:
                    pass
            
    except WebSocketDisconnect:
        manager.disconnect(user_id)
    except Exception as e:
        logger.error(f"Erreur WebSocket: {e}")
        manager.disconnect(user_id)

# ==================== NOTIFICATIONS ====================
# Copiez vos routes notifications existantes ici
# Elles fonctionneront avec les nouvelles validations

# ==================== LANCEMENT ====================
if __name__ == "__main__":
    logger.info("🚀 Marketplace Alger API démarrée")
    logger.info("📊 Système de rôles activé (customer/shop/admin)")
    logger.info("🛒 Commandes multi-produits disponibles")
    logger.info("🏪 Dashboard shop complet")
    logger.info("🔔 Notifications temps réel activées")
    logger.info("🔐 Validation améliorée avec Pydantic")
    logger.info("🌐 API: http://localhost:8000")
    logger.info("🔌 WebSocket: ws://localhost:8000/ws/{user_id}")
    logger.info("📚 Docs: http://localhost:8000/docs")
    
    uvicorn.run(
        "main:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=True,
        log_level="info"
    )
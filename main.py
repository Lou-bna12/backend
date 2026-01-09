from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from typing import Optional, List, Dict
import uvicorn
import sqlite3
import hashlib
import random
import string
import json
import asyncio
from datetime import datetime

# AJOUTE CET IMPORT
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Marketplace Alger API")

# ==================== AJOUTE CE BLOC CORS ====================
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",    # Frontend Vite
        "http://127.0.0.1:5173",    # Alternative
        "http://localhost:3000",     # React par défaut
        "http://127.0.0.1:3000",    # Alternative
    ],
    allow_credentials=True,
    allow_methods=["*"],  # Permet GET, POST, PUT, DELETE, OPTIONS, etc.
    allow_headers=["*"],  # Permet tous les headers
    expose_headers=["*"], # Expose tous les headers au frontend
)
# ==================== FIN DU BLOC CORS ====================

# ==================== WEBSOCKET MANAGER ====================
class ConnectionManager:
    def __init__(self):
        # Stockage: {user_id: websocket}
        self.active_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        self.active_connections[user_id] = websocket
        print(f"🔌 WebSocket connecté pour user: {user_id}")
    
    def disconnect(self, user_id: str):
        if user_id in self.active_connections:
            del self.active_connections[user_id]
            print(f"👋 WebSocket déconnecté pour user: {user_id}")
    
    async def send_personal_message(self, message: dict, user_id: str):
        if user_id in self.active_connections:
            websocket = self.active_connections[user_id]
            try:
                await websocket.send_json(message)
                print(f"📤 Message envoyé à user {user_id}")
            except:
                self.disconnect(user_id)
    
    async def broadcast(self, message: dict):
        for user_id, websocket in self.active_connections.items():
            try:
                await websocket.send_json(message)
            except:
                self.disconnect(user_id)

# Instance globale
manager = ConnectionManager()

# === FONCTIONS DE BASE ===
def hash_password(password: str) -> str:
    """Hash simple pour développement"""
    return hashlib.sha256(password.encode()).hexdigest()

def get_db():
    """Connexion à la base SQLite"""
    conn = sqlite3.connect('marketplace.db')
    conn.row_factory = sqlite3.Row
    return conn

def row_to_dict(row):
    """Convertir une row SQLite en dictionnaire"""
    return dict(row) if row else None

def generate_order_number():
    """Génère un numéro de commande unique"""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"CMD-{timestamp}-{random_str}"

# === MODÈLES PYDANTIC ===
class UserCreate(BaseModel):
    email: str
    phone: Optional[str] = None
    password: str
    full_name: str
    role: str = "customer"

class UserLogin(BaseModel):
    email: str
    password: str

class ProductCreate(BaseModel):
    name: str
    description: Optional[str] = None
    price: float
    stock: int = 0
    category: str = "general"

class ShopProductCreate(BaseModel):
    name: str
    description: Optional[str] = None
    price: float
    stock: int = 0
    category: str = "general"

class OrderCreate(BaseModel):
    product_id: int
    customer_phone: str
    quantity: int
    delivery_address: str

# NOUVEAUX MODÈLES POUR COMMANDES MULTI-PRODUITS
class OrderItem(BaseModel):
    product_id: int
    quantity: int

class MultiOrderCreate(BaseModel):
    items: List[OrderItem]
    customer_phone: str
    customer_email: Optional[str] = None
    delivery_address: str
    notes: Optional[str] = None

class OrderStatusUpdate(BaseModel):
    status: str

# MODÈLES POUR NOTIFICATIONS
class NotificationBase(BaseModel):
    user_id: int
    type: str = "system"
    title: str
    message: str
    link: Optional[str] = ""
    icon: Optional[str] = "bell"
    data: Optional[dict] = {}

class NotificationCreate(NotificationBase):
    pass

class NotificationResponse(NotificationBase):
    id: int
    read: bool
    created_at: str
    
    class Config:
        from_attributes = True

# === INITIALISATION BASE DE DONNÉES ===
def init_db():
    """Créer les tables et données de test"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Supprimer tables existantes
    tables = ["order_items", "orders", "products", "shops", "users", "notifications"]
    for table in tables:
        cursor.execute(f"DROP TABLE IF EXISTS {table}")
    
    # Créer table users AVEC colonne role
    cursor.execute('''
    CREATE TABLE users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        phone TEXT UNIQUE,
        password TEXT NOT NULL,
        full_name TEXT NOT NULL,
        role TEXT DEFAULT 'customer',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Créer table shops
    cursor.execute('''
    CREATE TABLE shops (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        owner_id INTEGER NOT NULL,
        FOREIGN KEY (owner_id) REFERENCES users (id)
    )
    ''')
    
    # Créer table products
    cursor.execute('''
    CREATE TABLE products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT,
        price REAL NOT NULL,
        stock INTEGER DEFAULT 0,
        category TEXT DEFAULT 'general',
        shop_id INTEGER NOT NULL,
        FOREIGN KEY (shop_id) REFERENCES shops (id)
    )
    ''')
    
    # Créer table orders (NOUVELLE VERSION POUR MULTI-PRODUITS)
    cursor.execute('''
    CREATE TABLE orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_number TEXT UNIQUE NOT NULL,
        customer_phone TEXT NOT NULL,
        customer_email TEXT,
        total_price REAL NOT NULL,
        delivery_address TEXT NOT NULL,
        status TEXT DEFAULT 'pending',
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Créer table order_items
    cursor.execute('''
    CREATE TABLE order_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER NOT NULL,
        product_id INTEGER NOT NULL,
        quantity INTEGER NOT NULL,
        unit_price REAL NOT NULL,
        FOREIGN KEY (order_id) REFERENCES orders (id),
        FOREIGN KEY (product_id) REFERENCES products (id)
    )
    ''')
    
    # Créer table notifications
    cursor.execute('''
    CREATE TABLE notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        type TEXT DEFAULT 'system',
        title TEXT NOT NULL,
        message TEXT NOT NULL,
        link TEXT DEFAULT '',
        icon TEXT DEFAULT 'bell',
        read BOOLEAN DEFAULT 0,
        data TEXT DEFAULT '{}',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    ''')
    
    conn.commit()
    
    # Ajouter admin de test
    cursor.execute(
        "INSERT INTO users (email, phone, password, full_name, role) VALUES (?, ?, ?, ?, ?)",
        ("admin@marketplace.dz", "+213123456789", hash_password("admin123"), "Admin Test", "admin")
    )
    admin_id = cursor.lastrowid
    
    # Ajouter shop de test
    cursor.execute(
        "INSERT INTO shops (name, owner_id) VALUES (?, ?)",
        ("Shop de Test", admin_id)
    )
    shop_id = cursor.lastrowid
    
    # Produits de test
    test_products = [
        ("Tomates Algériennes", "Tomates fraîches", 180.5, 50, "légumes", shop_id),
        ("Pommes Golden", "Pommes sucrées", 250.0, 30, "fruits", shop_id),
        ("Lait NCA", "Lait frais 1L", 120.0, 100, "produits laitiers", shop_id),
        ("Pain Traditionnel", "Pain algérien", 25.0, 200, "boulangerie", shop_id),
    ]
    
    for prod in test_products:
        cursor.execute(
            "INSERT INTO products (name, description, price, stock, category, shop_id) VALUES (?, ?, ?, ?, ?, ?)",
            prod
        )
    
    # Créer une commande de test
    order_number = generate_order_number()
    cursor.execute(
        "INSERT INTO orders (order_number, customer_phone, customer_email, total_price, delivery_address, status) VALUES (?, ?, ?, ?, ?, ?)",
        (order_number, "+213123456789", "test@example.com", 605.5, "123 Rue Test, Alger", "pending")
    )
    order_id = cursor.lastrowid
    
    # Ajouter des items à la commande test
    cursor.execute("SELECT id, price FROM products LIMIT 2")
    test_products = cursor.fetchall()
    
    if len(test_products) >= 2:
        cursor.execute(
            "INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES (?, ?, ?, ?)",
            (order_id, test_products[0]['id'], 2, test_products[0]['price'])
        )
        cursor.execute(
            "INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES (?, ?, ?, ?)",
            (order_id, test_products[1]['id'], 1, test_products[1]['price'])
        )
    
    # Ajouter une notification de test
    cursor.execute(
        """INSERT INTO notifications 
           (user_id, type, title, message, link, icon, data) 
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (admin_id, "system", "Bienvenue sur Marketplace", 
         "Votre compte administrateur a été créé avec succès.", 
         "/dashboard", "bell", '{"welcome": true}')
    )
    
    conn.commit()
    conn.close()
    print("✅ Base de données initialisée avec notifications")

# Lancer l'initialisation
init_db()

# === ROUTES API ===
@app.get("/")
def home():
    return {
        "message": "Marketplace Alger API 🚀",
        "version": "4.0",
        "features": ["rôles utilisateurs", "dashboard shop", "commandes multi-produits", "notifications temps réel"],
        "endpoints": [
            "POST /register - S'inscrire",
            "POST /login - Se connecter",
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
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        conn.close()
        return {"status": "healthy"}
    except:
        return {"status": "unhealthy"}

# === AUTHENTIFICATION ===
@app.post("/register")
def register(user: UserCreate):
    conn = get_db()
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
        
        # Vérifier le rôle
        if user.role not in ["customer", "shop", "admin"]:
            raise HTTPException(400, "Rôle invalide")
        
        # Créer utilisateur
        hashed = hash_password(user.password)
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
            "SELECT id, email, phone, full_name, role FROM users WHERE id = ?",
            (user_id,)
        )
        user_data = row_to_dict(cursor.fetchone())
        
        return {
            "success": True,
            "message": "Inscription réussie",
            "user": user_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Erreur: {str(e)}")
    finally:
        conn.close()

@app.post("/login")
def login(credentials: UserLogin):
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "SELECT id, email, password, full_name, role FROM users WHERE email = ?",
            (credentials.email,)
        )
        user = row_to_dict(cursor.fetchone())
        
        if not user:
            raise HTTPException(401, "Email ou mot de passe incorrect")
        
        if hash_password(credentials.password) != user['password']:
            raise HTTPException(401, "Email ou mot de passe incorrect")
        
        return {
            "success": True,
            "message": "Connexion réussie",
            "user_id": user['id'],
            "email": user['email'],
            "full_name": user['full_name'],
            "role": user['role']
        }
        
    finally:
        conn.close()

@app.get("/me")
def get_me(email: str):
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "SELECT id, email, phone, full_name, role FROM users WHERE email = ?",
            (email,)
        )
        user = row_to_dict(cursor.fetchone())
        
        if not user:
            raise HTTPException(404, "Utilisateur non trouvé")
        
        # Si c'est un shop, ajouter l'ID du shop
        if user['role'] == 'shop':
            cursor.execute(
                "SELECT id as shop_id, name as shop_name FROM shops WHERE owner_id = ?",
                (user['id'],)
            )
            shop_info = row_to_dict(cursor.fetchone())
            if shop_info:
                user.update(shop_info)
        
        return user
        
    finally:
        conn.close()

# === PRODUITS ===
@app.post("/products")
def create_product(product: ProductCreate):
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT id FROM shops LIMIT 1")
        shop = row_to_dict(cursor.fetchone())
        
        if not shop:
            raise HTTPException(404, "Aucun shop disponible")
        
        cursor.execute(
            "INSERT INTO products (name, description, price, stock, category, shop_id) VALUES (?, ?, ?, ?, ?, ?)",
            (product.name, product.description, product.price, product.stock, product.category, shop['id'])
        )
        product_id = cursor.lastrowid
        
        conn.commit()
        
        cursor.execute("SELECT * FROM products WHERE id = ?", (product_id,))
        product_data = row_to_dict(cursor.fetchone())
        
        return {
            "success": True,
            "message": "Produit créé",
            "product": product_data
        }
        
    finally:
        conn.close()

@app.get("/products")
def get_products(category: Optional[str] = None):
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        if category:
            cursor.execute(
                "SELECT p.*, s.name as shop_name FROM products p JOIN shops s ON p.shop_id = s.id WHERE p.category = ?",
                (category,)
            )
        else:
            cursor.execute(
                "SELECT p.*, s.name as shop_name FROM products p JOIN shops s ON p.shop_id = s.id"
            )
        
        products = [row_to_dict(row) for row in cursor.fetchall()]
        
        return {
            "count": len(products),
            "products": products
        }
        
    finally:
        conn.close()

# === ROUTES SHOP ===
@app.get("/shop/products")
def get_shop_products(owner_email: str):
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            """SELECT s.id as shop_id 
               FROM users u 
               JOIN shops s ON u.id = s.owner_id 
               WHERE u.email = ? AND u.role = 'shop'""",
            (owner_email,)
        )
        shop = row_to_dict(cursor.fetchone())
        
        if not shop:
            raise HTTPException(403, "Accès réservé aux fournisseurs")
        
        cursor.execute(
            "SELECT * FROM products WHERE shop_id = ? ORDER BY id DESC",
            (shop['shop_id'],)
        )
        products = [row_to_dict(row) for row in cursor.fetchall()]
        
        return {
            "shop_id": shop['shop_id'],
            "count": len(products),
            "products": products
        }
        
    finally:
        conn.close()

@app.post("/shop/products")
def create_shop_product(product: ShopProductCreate, owner_email: str):
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            """SELECT s.id as shop_id 
               FROM users u 
               JOIN shops s ON u.id = s.owner_id 
               WHERE u.email = ? AND u.role = 'shop'""",
            (owner_email,)
        )
        shop = row_to_dict(cursor.fetchone())
        
        if not shop:
            raise HTTPException(403, "Accès réservé aux fournisseurs")
        
        cursor.execute(
            """INSERT INTO products (name, description, price, stock, category, shop_id) 
               VALUES (?, ?, ?, ?, ?, ?)""",
            (product.name, product.description, product.price, product.stock, product.category, shop['shop_id'])
        )
        product_id = cursor.lastrowid
        
        conn.commit()
        
        cursor.execute("SELECT * FROM products WHERE id = ?", (product_id,))
        product_data = row_to_dict(cursor.fetchone())
        
        return {
            "success": True,
            "message": "Produit créé avec succès",
            "product": product_data
        }
        
    finally:
        conn.close()

# === COMMANDES ===
@app.post("/orders")
async def create_order(order: MultiOrderCreate):
    """Créer une commande avec plusieurs produits"""
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        # Vérifier que tous les produits existent et ont du stock
        total_price = 0
        order_items = []
        
        for item in order.items:
            cursor.execute("SELECT id, name, price, stock, shop_id FROM products WHERE id = ?", (item.product_id,))
            product = row_to_dict(cursor.fetchone())
            
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
        order_number = generate_order_number()
        
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
        cursor.execute(
            """SELECT o.* FROM orders o WHERE o.id = ?""",
            (order_id,)
        )
        order_data = row_to_dict(cursor.fetchone())
        
        # Récupérer les items
        cursor.execute(
            """SELECT oi.*, p.name as product_name, p.shop_id, s.name as shop_name 
               FROM order_items oi 
               JOIN products p ON oi.product_id = p.id 
               JOIN shops s ON p.shop_id = s.id
               WHERE oi.order_id = ?""",
            (order_id,)
        )
        items = [row_to_dict(row) for row in cursor.fetchall()]
        
        order_data['items'] = items
        
        # NOTIFICATION : Envoyer une notification à l'admin (user_id = 1)
        notification_task = asyncio.create_task(
            create_notification(NotificationCreate(
                user_id=1,  # ID de l'admin
                type="order",
                title="Nouvelle commande",
                message=f"Commande #{order_number} reçue de {order.customer_phone}",
                link=f"/admin/orders/{order_id}",
                icon="shopping-cart",
                data={"order_id": order_id, "order_number": order_number}
            ))
        )
        
        return {
            "success": True,
            "message": "Commande créée avec succès",
            "order": order_data,
            "order_number": order_number,
            "note": "Paiement à la livraison"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(500, f"Erreur lors de la création de la commande: {str(e)}")
    finally:
        conn.close()

@app.get("/orders/{phone}")
def get_orders_by_phone(phone: str):
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "SELECT * FROM orders WHERE customer_phone = ? ORDER BY created_at DESC",
            (phone,)
        )
        orders = [row_to_dict(row) for row in cursor.fetchall()]
        
        for order in orders:
            cursor.execute(
                """SELECT oi.*, p.name as product_name 
                   FROM order_items oi 
                   JOIN products p ON oi.product_id = p.id 
                   WHERE oi.order_id = ?""",
                (order['id'],)
            )
            order['items'] = [row_to_dict(row) for row in cursor.fetchall()]
        
        return {
            "count": len(orders),
            "orders": orders
        }
        
    finally:
        conn.close()

@app.get("/orders/user/{email}")
def get_orders_by_email(email: str):
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "SELECT * FROM orders WHERE customer_email = ? ORDER BY created_at DESC",
            (email,)
        )
        orders = [row_to_dict(row) for row in cursor.fetchall()]
        
        for order in orders:
            cursor.execute(
                """SELECT oi.*, p.name as product_name 
                   FROM order_items oi 
                   JOIN products p ON oi.product_id = p.id 
                   WHERE oi.order_id = ?""",
                (order['id'],)
            )
            order['items'] = [row_to_dict(row) for row in cursor.fetchall()]
        
        return {
            "count": len(orders),
            "orders": orders
        }
        
    finally:
        conn.close()

@app.get("/orders/shop/{owner_email}")
def get_shop_orders(owner_email: str):
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            """SELECT s.id as shop_id 
               FROM users u 
               JOIN shops s ON u.id = s.owner_id 
               WHERE u.email = ? AND u.role = 'shop'""",
            (owner_email,)
        )
        shop = row_to_dict(cursor.fetchone())
        
        if not shop:
            raise HTTPException(403, "Accès réservé aux fournisseurs")
        
        cursor.execute(
            """SELECT DISTINCT o.* 
               FROM orders o
               JOIN order_items oi ON o.id = oi.order_id
               JOIN products p ON oi.product_id = p.id
               WHERE p.shop_id = ?
               ORDER BY o.created_at DESC""",
            (shop['shop_id'],)
        )
        orders = [row_to_dict(row) for row in cursor.fetchall()]
        
        for order in orders:
            cursor.execute(
                """SELECT oi.*, p.name as product_name, p.shop_id 
                   FROM order_items oi 
                   JOIN products p ON oi.product_id = p.id 
                   WHERE oi.order_id = ? AND p.shop_id = ?""",
                (order['id'], shop['shop_id'])
            )
            order['items'] = [row_to_dict(row) for row in cursor.fetchall()]
        
        return {
            "shop_id": shop['shop_id'],
            "count": len(orders),
            "orders": orders
        }
        
    finally:
        conn.close()

@app.put("/orders/{order_id}/status")
async def update_order_status(order_id: int, status_update: OrderStatusUpdate):
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT id FROM orders WHERE id = ?", (order_id,))
        if not cursor.fetchone():
            raise HTTPException(404, "Commande non trouvée")
        
        cursor.execute(
            "UPDATE orders SET status = ? WHERE id = ?",
            (status_update.status, order_id)
        )
        
        conn.commit()
        
        cursor.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
        order = row_to_dict(cursor.fetchone())
        
        # NOTIFICATION : Envoyer une notification au client si son user_id est connu
        # Ici on envoie à l'admin pour l'exemple
        notification_task = asyncio.create_task(
            create_notification(NotificationCreate(
                user_id=1,
                type="order",
                title="Statut de commande mis à jour",
                message=f"Commande #{order['order_number']} est maintenant {status_update.status}",
                link=f"/orders/{order_id}",
                icon="package",
                data={"order_id": order_id, "status": status_update.status}
            ))
        )
        
        return {
            "success": True,
            "message": f"Statut de la commande mis à jour: {status_update.status}",
            "order": order
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Erreur: {str(e)}")
    finally:
        conn.close()

# ==================== WEBSOCKET ENDPOINT ====================
@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    await manager.connect(websocket, user_id)
    
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
            
    except WebSocketDisconnect:
        manager.disconnect(user_id)

# ==================== NOTIFICATIONS API ====================
@app.post("/api/notifications")
async def create_notification(notification: NotificationCreate):
    """Créer une notification"""
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            """INSERT INTO notifications 
               (user_id, type, title, message, link, icon, data) 
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (notification.user_id, notification.type, notification.title, 
             notification.message, notification.link, notification.icon,
             json.dumps(notification.data or {}))
        )
        notification_id = cursor.lastrowid
        
        conn.commit()
        
        cursor.execute(
            "SELECT * FROM notifications WHERE id = ?",
            (notification_id,)
        )
        notif_data = row_to_dict(cursor.fetchone())
        
        # Convertir data de JSON string à dict
        if notif_data.get('data'):
            notif_data['data'] = json.loads(notif_data['data'])
        
        # Envoyer via WebSocket
        await manager.send_personal_message({
            "type": "new_notification",
            "notification": notif_data
        }, str(notification.user_id))
        
        return {
            "success": True,
            "notification": notif_data
        }
        
    except Exception as e:
        print(f"❌ Erreur création notification: {e}")
        raise HTTPException(500, f"Erreur: {str(e)}")
    finally:
        conn.close()

@app.get("/api/notifications/{user_id}")
def get_user_notifications(user_id: int):
    """Récupérer les notifications d'un utilisateur"""
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            """SELECT * FROM notifications 
               WHERE user_id = ? 
               ORDER BY created_at DESC 
               LIMIT 20""",
            (user_id,)
        )
        notifications = [row_to_dict(row) for row in cursor.fetchall()]
        
        for notif in notifications:
            if notif.get('data'):
                notif['data'] = json.loads(notif['data'])
        
        return {
            "success": True,
            "count": len(notifications),
            "notifications": notifications
        }
    except Exception as e:
        raise HTTPException(500, f"Erreur: {str(e)}")
    finally:
        conn.close()

@app.put("/api/notifications/{notification_id}/read")
def mark_notification_as_read(notification_id: int):
    """Marquer une notification comme lue"""
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "UPDATE notifications SET read = 1 WHERE id = ?",
            (notification_id,)
        )
        conn.commit()
        
        return {"success": True, "message": "Notification marquée comme lue"}
    except Exception as e:
        raise HTTPException(500, f"Erreur: {str(e)}")
    finally:
        conn.close()

@app.put("/api/notifications/user/{user_id}/read-all")
def mark_all_as_read(user_id: int):
    """Marquer toutes les notifications comme lues"""
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "UPDATE notifications SET read = 1 WHERE user_id = ? AND read = 0",
            (user_id,)
        )
        conn.commit()
        
        return {"success": True, "message": "Toutes les notifications marquées comme lues"}
    except Exception as e:
        raise HTTPException(500, f"Erreur: {str(e)}")
    finally:
        conn.close()

@app.delete("/api/notifications/{notification_id}")
def delete_notification(notification_id: int):
    """Supprimer une notification"""
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute("DELETE FROM notifications WHERE id = ?", (notification_id,))
        conn.commit()
        
        return {"success": True, "message": "Notification supprimée"}
    except Exception as e:
        raise HTTPException(500, f"Erreur: {str(e)}")
    finally:
        conn.close()

# Route de test
@app.post("/api/notifications/test/{user_id}")
async def test_notification(user_id: int):
    """Tester le système de notifications"""
    test_notif = NotificationCreate(
        user_id=user_id,
        type="system",
        title="Notification de test",
        message="Ceci est une notification de test pour vérifier le système.",
        link="/dashboard",
        icon="bell",
        data={"test": True, "timestamp": datetime.now().isoformat()}
    )
    
    return await create_notification(test_notif)

# === ROUTES ADMIN ===
@app.get("/admin/users")
def get_all_users():
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT id, email, phone, full_name, role, created_at FROM users ORDER BY id")
        users = [row_to_dict(row) for row in cursor.fetchall()]
        
        return {
            "count": len(users),
            "users": users
        }
    finally:
        conn.close()

@app.get("/admin/stats")
def get_admin_stats():
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT role, COUNT(*) as count FROM users GROUP BY role")
        roles_stats = [row_to_dict(row) for row in cursor.fetchall()]
        
        cursor.execute("SELECT COUNT(*) as total_products FROM products")
        total_products = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) as total_orders FROM orders")
        total_orders = cursor.fetchone()[0]
        
        cursor.execute("SELECT SUM(total_price) as total_revenue FROM orders")
        total_revenue = cursor.fetchone()[0] or 0
        
        cursor.execute("SELECT status, COUNT(*) as count FROM orders GROUP BY status")
        orders_by_status = [row_to_dict(row) for row in cursor.fetchall()]
        
        return {
            "roles": roles_stats,
            "total_products": total_products,
            "total_orders": total_orders,
            "total_revenue": total_revenue,
            "orders_by_status": orders_by_status
        }
    finally:
        conn.close()

if __name__ == "__main__":
    print("🚀 Marketplace Alger API démarrée")
    print("📊 Système de rôles activé (customer/shop/admin)")
    print("🛒 Commandes multi-produits disponibles")
    print("🏪 Dashboard shop complet")
    print("🔔 Notifications temps réel activées")
    print("🌐 API: http://localhost:8000")
    print("🔌 WebSocket: ws://localhost:8000/ws/{user_id}")
    print("📚 Docs: http://localhost:8000/docs")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
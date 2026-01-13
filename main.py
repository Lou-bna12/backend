from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
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

app = FastAPI(title="Marketplace Alger API")

# ==================== CORS AMÉLIORÉ ====================
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,
)

# Middleware pour logs et headers supplémentaires
@app.middleware("http")
async def log_requests(request: Request, call_next):
    print(f"🌐 {request.method} {request.url}")
    print(f"   Origin: {request.headers.get('origin')}")
    print(f"   Referer: {request.headers.get('referer')}")
    
    response = await call_next(request)
    
    # Assurer les headers CORS
    origin = request.headers.get("origin")
    if origin in ["http://127.0.0.1:5173", "http://localhost:5173"]:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
    
    print(f"   Status: {response.status_code}")
    return response

# Handler OPTIONS global
@app.options("/{full_path:path}")
async def options_handler(full_path: str):
    return JSONResponse(
        content={"message": "CORS preflight"},
        headers={
            "Access-Control-Allow-Origin": "http://127.0.0.1:5173",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS, PATCH",
            "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Requested-With",
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Max-Age": "3600",
        }
    )

# ==================== WEBSOCKET MANAGER ====================
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.connection_times: Dict[str, datetime] = {}
    
    async def connect(self, websocket: WebSocket, user_id: str):
        # Fermer l'ancienne connexion si elle existe
        if user_id in self.active_connections:
            try:
                await self.active_connections[user_id].close()
            except:
                pass
        
        await websocket.accept()
        self.active_connections[user_id] = websocket
        self.connection_times[user_id] = datetime.now()
        print(f"🔌 WebSocket connecté pour user: {user_id}")
    
    def disconnect(self, user_id: str):
        if user_id in self.active_connections:
            del self.active_connections[user_id]
            if user_id in self.connection_times:
                del self.connection_times[user_id]
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

manager = ConnectionManager()

# === FONCTIONS DE BASE ===
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def get_db():
    conn = sqlite3.connect('marketplace.db')
    conn.row_factory = sqlite3.Row
    return conn

def row_to_dict(row):
    return dict(row) if row else None

def generate_order_number():
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

# === INITIALISATION DB ===
def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    tables = ["order_items", "orders", "products", "shops", "users", "notifications"]
    for table in tables:
        cursor.execute(f"DROP TABLE IF EXISTS {table}")
    
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
    
    cursor.execute('''
    CREATE TABLE shops (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        owner_id INTEGER NOT NULL,
        FOREIGN KEY (owner_id) REFERENCES users (id)
    )
    ''')
    
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
    
    # Admin test
    cursor.execute(
        "INSERT INTO users (email, phone, password, full_name, role) VALUES (?, ?, ?, ?, ?)",
        ("admin@marketplace.dz", "+213123456789", hash_password("admin123"), "Admin Test", "admin")
    )
    admin_id = cursor.lastrowid
    
    # Shop test
    cursor.execute(
        "INSERT INTO shops (name, owner_id) VALUES (?, ?)",
        ("Shop de Test", admin_id)
    )
    shop_id = cursor.lastrowid
    
    # Produits test
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
    
    # Commande test
    order_number = generate_order_number()
    cursor.execute(
        "INSERT INTO orders (order_number, customer_phone, customer_email, total_price, delivery_address, status) VALUES (?, ?, ?, ?, ?, ?)",
        (order_number, "+213123456789", "test@example.com", 605.5, "123 Rue Test, Alger", "pending")
    )
    order_id = cursor.lastrowid
    
    # Items commande
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
    
    # Notification test
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
    print("✅ Base de données initialisée")

init_db()

# === ROUTES API ===
@app.get("/")
def home():
    return {
        "message": "Marketplace Alger API 🚀",
        "version": "4.2",
        "cors": "Enabled for http://127.0.0.1:5173",
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
        return {"status": "healthy", "cors": "enabled"}
    except:
        return {"status": "unhealthy"}

        # === PRODUITS ===
@app.get("/products")
def get_products(category: Optional[str] = None):
    """Lister tous les produits - ROUTE MANQUANTE"""
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
        
    except Exception as e:
        print(f"❌ Erreur récupération produits: {e}")
        raise HTTPException(500, f"Erreur: {str(e)}")
    finally:
        conn.close()

@app.post("/products")
def create_product(product: ProductCreate):
    """Créer un produit"""
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
        
    except Exception as e:
        print(f"❌ Erreur création produit: {e}")
        raise HTTPException(500, f"Erreur: {str(e)}")
    finally:
        conn.close()

# === NOTIFICATIONS API (CORRIGÉES) ===
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
        
        if notif_data.get('data'):
            notif_data['data'] = json.loads(notif_data['data'])
        
        # WebSocket
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

# ... (Gardez le reste de vos routes existantes inchangées)
# Copiez toutes vos autres routes ici...

# === WEBSOCKET ===
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
    except Exception as e:
        print(f"❌ Erreur WebSocket: {e}")
        manager.disconnect(user_id)

if __name__ == "__main__":
    print("🚀 Marketplace Alger API démarrée")
    print("🌐 CORS configuré pour: http://127.0.0.1:5173")
    print("🔗 Frontend: http://127.0.0.1:5173")
    print("🔗 Backend: http://localhost:8000")
    print("🔌 WebSocket: ws://localhost:8000/ws/{user_id}")
    print("📚 Docs: http://localhost:8000/docs")
    
    uvicorn.run(
        "main:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=True
    )
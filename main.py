from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import uvicorn
import sqlite3
import hashlib

app = FastAPI(title="Marketplace Alger API")

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

# === INITIALISATION BASE DE DONNÉES ===
def init_db():
    """Créer les tables et données de test"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Supprimer tables existantes
    tables = ["orders", "products", "shops", "users"]
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
    
    # Créer table orders
    cursor.execute('''
    CREATE TABLE orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER NOT NULL,
        customer_phone TEXT NOT NULL,
        quantity INTEGER NOT NULL,
        total_price REAL NOT NULL,
        delivery_address TEXT NOT NULL,
        status TEXT DEFAULT 'pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (product_id) REFERENCES products (id)
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
    
    conn.commit()
    conn.close()
    print("✅ Base de données initialisée avec rôles")

# Lancer l'initialisation
init_db()

# === ROUTES API ===
@app.get("/")
def home():
    return {
        "message": "Marketplace Alger API 🚀",
        "version": "2.0",
        "features": ["rôles utilisateurs", "dashboard shop", "commandes"],
        "endpoints": [
            "POST /register - S'inscrire (customer/shop/admin)",
            "POST /login - Se connecter",
            "GET /me - Info utilisateur",
            "GET /products - Liste produits",
            "POST /products - Créer produit (public)",
            "GET /shop/products - Produits d'un shop",
            "POST /shop/products - Créer produit (shop)",
            "POST /orders - Créer commande",
            "GET /orders/{phone} - Voir commandes"
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
            raise HTTPException(400, "Rôle invalide: doit être customer, shop ou admin")
        
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
    """Récupérer les informations de l'utilisateur connecté"""
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

# === PRODUITS PUBLICS ===
@app.post("/products")
def create_product(product: ProductCreate):
    """Créer un produit (public - pour tests)"""
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

@app.get("/products/{product_id}")
def get_product(product_id: int):
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "SELECT p.*, s.name as shop_name FROM products p JOIN shops s ON p.shop_id = s.id WHERE p.id = ?",
            (product_id,)
        )
        
        product = row_to_dict(cursor.fetchone())
        
        if not product:
            raise HTTPException(404, "Produit non trouvé")
        
        return product
        
    finally:
        conn.close()

# === ROUTES SHOP (FOURNISSEURS) ===
@app.get("/shop/products")
def get_shop_products(owner_email: str):
    """Récupérer tous les produits d'un shop spécifique"""
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        # Trouver le shop de cet utilisateur
        cursor.execute(
            """SELECT s.id as shop_id 
               FROM users u 
               JOIN shops s ON u.id = s.owner_id 
               WHERE u.email = ? AND u.role = 'shop'""",
            (owner_email,)
        )
        shop = row_to_dict(cursor.fetchone())
        
        if not shop:
            raise HTTPException(403, "Accès réservé aux fournisseurs ou shop non trouvé")
        
        # Récupérer les produits de ce shop
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
    """Créer un produit pour un shop (version JSON corrigée)"""
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        # Vérifier que l'utilisateur est un shop
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
        
        # Créer le produit
        cursor.execute(
            """INSERT INTO products (name, description, price, stock, category, shop_id) 
               VALUES (?, ?, ?, ?, ?, ?)""",
            (product.name, product.description, product.price, product.stock, product.category, shop['shop_id'])
        )
        product_id = cursor.lastrowid
        
        conn.commit()
        
        # Retourner le produit créé
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
def create_order(order: OrderCreate):
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT id, name, price, stock FROM products WHERE id = ?", (order.product_id,))
        product = row_to_dict(cursor.fetchone())
        
        if not product:
            raise HTTPException(404, "Produit non trouvé")
        
        if product['stock'] < order.quantity:
            raise HTTPException(400, f"Stock insuffisant: {product['stock']} disponible")
        
        total = product['price'] * order.quantity
        
        cursor.execute(
            "INSERT INTO orders (product_id, customer_phone, quantity, total_price, delivery_address, status) VALUES (?, ?, ?, ?, ?, ?)",
            (order.product_id, order.customer_phone, order.quantity, total, order.delivery_address, "pending")
        )
        order_id = cursor.lastrowid
        
        # Mettre à jour stock
        new_stock = product['stock'] - order.quantity
        cursor.execute("UPDATE products SET stock = ? WHERE id = ?", (new_stock, order.product_id))
        
        conn.commit()
        
        cursor.execute(
            "SELECT o.*, p.name as product_name FROM orders o JOIN products p ON o.product_id = p.id WHERE o.id = ?",
            (order_id,)
        )
        order_data = row_to_dict(cursor.fetchone())
        
        return {
            "success": True,
            "message": "Commande créée",
            "order": order_data,
            "note": "Paiement à la livraison"
        }
        
    finally:
        conn.close()

@app.get("/orders/{phone}")
def get_orders(phone: str):
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "SELECT o.*, p.name as product_name FROM orders o JOIN products p ON o.product_id = p.id WHERE o.customer_phone = ? ORDER BY o.created_at DESC",
            (phone,)
        )
        
        orders = [row_to_dict(row) for row in cursor.fetchall()]
        
        return {
            "count": len(orders),
            "orders": orders
        }
        
    finally:
        conn.close()

# === ROUTES ADMIN (FACULTATIVES) ===
@app.get("/admin/users")
def get_all_users():
    """Récupérer tous les utilisateurs (admin seulement)"""
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
    """Statistiques pour admin"""
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        # Compter les utilisateurs par rôle
        cursor.execute("SELECT role, COUNT(*) as count FROM users GROUP BY role")
        roles_stats = [row_to_dict(row) for row in cursor.fetchall()]
        
        # Compter les produits
        cursor.execute("SELECT COUNT(*) as total_products FROM products")
        total_products = cursor.fetchone()[0]
        
        # Compter les commandes
        cursor.execute("SELECT COUNT(*) as total_orders FROM orders")
        total_orders = cursor.fetchone()[0]
        
        # Chiffre d'affaires total
        cursor.execute("SELECT SUM(total_price) as total_revenue FROM orders")
        total_revenue = cursor.fetchone()[0] or 0
        
        return {
            "roles": roles_stats,
            "total_products": total_products,
            "total_orders": total_orders,
            "total_revenue": total_revenue
        }
    finally:
        conn.close()

if __name__ == "__main__":
    print("🚀 Marketplace Alger API démarrée")
    print("📊 Système de rôles activé (customer/shop/admin)")
    print("🏪 Dashboard shop disponible")
    print("🌐 API: http://localhost:8000")
    print("📚 Docs: http://localhost:8000/docs")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

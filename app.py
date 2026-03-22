from flask import Flask, jsonify, request, session, render_template
import bcrypt
import mysql.connector
from config import DB_CONFIG
from datetime import timedelta
import hmac
import hashlib
import json

app = Flask(__name__)
app.secret_key = "perkupcafe_secret_key_2025"
app.config["SESSION_PERMANENT"] = True

# ── Razorpay credentials (replace with your actual keys) ──
RAZORPAY_KEY_ID     = "YOUR_KEY_HERE"
RAZORPAY_KEY_SECRET = "YOUR_SECRET_HERE"
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=7)

def get_db_connection():
    return mysql.connector.connect(**DB_CONFIG)


# ===========================
# PAGES
# ===========================

@app.route("/")
def home():
    # Admins → admin panel
    if "user_id" in session and session.get("role") == "admin":
        return render_template("admin.html")
    # Everyone (guest or user) → main page
    return render_template("index.html")

@app.route("/login")
def login_page():
    from flask import redirect, url_for
    return redirect("/")

@app.route("/signup")
def signup_page():
    from flask import redirect
    return redirect("/")

@app.route("/payment")
def payment_page():
    from flask import redirect
    if "user_id" not in session:
        return redirect("/")
    return render_template("payment.html")
    
@app.route("/dashboard")
def dashboard_page():
    from flask import redirect
    return redirect("/")

@app.route("/admin")
def admin_page():
    from flask import redirect
    if "user_id" not in session or session.get("role") != "admin":
        return redirect("/")
    return render_template("admin.html")

@app.route("/test-db")
def test_db():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT DATABASE();")
        db = cursor.fetchone()
        cursor.close()
        conn.close()
        return jsonify({"Connected Database": db[0]})
    except Exception as e:
        return jsonify({"Error": str(e)})


# ===========================
# AUTH
# ===========================

@app.route("/register", methods=["POST"])
def register():
    try:
        data     = request.get_json()
        name     = data["name"]
        email    = data["email"]
        password = data["password"]

        hashed_password = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())

        conn   = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        if cursor.fetchone():
            cursor.close(); conn.close()
            return jsonify({"message": "Email already registered"}), 400

        cursor.execute(
            "INSERT INTO users (name, email, password) VALUES (%s, %s, %s)",
            (name, email, hashed_password.decode("utf-8"))
        )
        conn.commit()
        cursor.close(); conn.close()
        return jsonify({"message": "User registered successfully"}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/login", methods=["POST"])
def login():
    try:
        data     = request.get_json()
        email    = data["email"]
        password = data["password"]

        conn   = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        cursor.close(); conn.close()

        if not user:
            return jsonify({"message": "User not found"}), 404

        if not bcrypt.checkpw(password.encode("utf-8"), user["password"].encode("utf-8")):
            return jsonify({"message": "Invalid password"}), 401

        session.permanent = True
        session["user_id"] = user["id"]
        session["name"]    = user["name"]
        session["email"]   = user["email"]
        session["role"]    = user["role"]

        return jsonify({"message": "Login successful", "role": user["role"]}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/check-session", methods=["GET"])
def check_session():
    if "user_id" in session:
        return jsonify({
            "loggedIn": True,
            "name":  session["name"],
            "email": session["email"],
            "role":  session["role"]
        })
    return jsonify({"loggedIn": False}), 200  # 200 — guests are OK


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"message": "Logged out successfully"})


# ===========================
# PRODUCTS (CUSTOMER)
# ===========================

@app.route("/get-products", methods=["GET"])
def get_products():
    conn   = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT id, name, price, is_available,
               COALESCE(category, 'Hot Coffee') AS category,
               COALESCE(emoji, '☕') AS emoji,
               COALESCE(description, '') AS description
        FROM products
        WHERE is_available = 1
        ORDER BY id
    """)
    products = cursor.fetchall()
    cursor.close(); conn.close()
    return jsonify({"products": products})


# ===========================
# CART
# ===========================

@app.route("/add-to-cart", methods=["POST"])
def add_to_cart():
    if "user_id" not in session:
        return jsonify({"message": "Unauthorized"}), 401

    data       = request.get_json()
    product_id = data["product_id"]
    user_id    = session["user_id"]

    conn   = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM products WHERE id=%s AND is_available=1", (product_id,))
    if not cursor.fetchone():
        cursor.close(); conn.close()
        return jsonify({"message": "Product not available"}), 400

    cursor.execute("SELECT * FROM cart WHERE user_id=%s AND product_id=%s", (user_id, product_id))
    if cursor.fetchone():
        cursor.execute(
            "UPDATE cart SET quantity = quantity + 1 WHERE user_id=%s AND product_id=%s",
            (user_id, product_id)
        )
    else:
        cursor.execute(
            "INSERT INTO cart (user_id, product_id, quantity) VALUES (%s, %s, 1)",
            (user_id, product_id)
        )

    conn.commit()
    cursor.close(); conn.close()
    return jsonify({"message": "Item added"})


@app.route("/update-cart", methods=["POST"])
def update_cart():
    if "user_id" not in session:
        return jsonify({"message": "Not logged in"}), 401

    data       = request.get_json()
    product_id = data.get("product_id")
    delta      = data.get("delta")
    user_id    = session["user_id"]

    conn   = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE cart SET quantity = quantity + %s WHERE user_id=%s AND product_id=%s",
        (delta, user_id, product_id)
    )
    cursor.execute(
        "DELETE FROM cart WHERE user_id=%s AND product_id=%s AND quantity <= 0",
        (user_id, product_id)
    )
    conn.commit()
    cursor.close(); conn.close()
    return jsonify({"message": "Cart updated"})


@app.route("/get-cart", methods=["GET"])
def get_cart():
    if "user_id" not in session:
        return jsonify({"cart": {}})

    user_id = session["user_id"]
    conn    = get_db_connection()
    cursor  = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT cart.product_id, products.name, products.price, cart.quantity
        FROM cart
        JOIN products ON cart.product_id = products.id
        WHERE cart.user_id = %s
    """, (user_id,))
    items = cursor.fetchall()
    cursor.close(); conn.close()

    cart_data = {}
    for item in items:
        cart_data[item["product_id"]] = {
            "product_id": item["product_id"],
            "name":       item["name"],
            "price":      item["price"],
            "qty":        item["quantity"]
        }
    return jsonify({"cart": cart_data})



# ===========================
# RAZORPAY
# ===========================

@app.route("/create-razorpay-order", methods=["POST"])
def create_razorpay_order():
    if "user_id" not in session:
        return jsonify({"message": "Not logged in"}), 401

    user_id = session["user_id"]
    conn    = get_db_connection()
    cursor  = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT cart.product_id, cart.quantity, products.price
        FROM cart JOIN products ON cart.product_id = products.id
        WHERE cart.user_id = %s
    """, (user_id,))
    cart_items = cursor.fetchall()
    cursor.close(); conn.close()

    if not cart_items:
        return jsonify({"message": "Cart is empty"}), 400

    subtotal = sum(int(i["quantity"]) * float(i["price"]) for i in cart_items)
    tax      = round(subtotal * 0.05)
    total    = subtotal + tax
    amount_paise = int(total * 100)   # Razorpay needs paise

    import base64, json as json_lib
    credentials = base64.b64encode(
        f"{RAZORPAY_KEY_ID}:{RAZORPAY_KEY_SECRET}".encode()
    ).decode()

    try:
        import urllib.request, urllib.error
        payload = json_lib.dumps({
            "amount":   amount_paise,
            "currency": "INR",
            "receipt":  f"receipt_user_{user_id}",
            "payment_capture": 1
        }).encode()

        rz_req = urllib.request.Request(
            "https://api.razorpay.com/v1/orders",
            data=payload,
            headers={
                "Content-Type":  "application/json",
                "Authorization": f"Basic {credentials}"
            },
            method="POST"
        )
        with urllib.request.urlopen(rz_req) as resp:
            rz_order = json_lib.loads(resp.read())

        return jsonify({
            "razorpay_order_id": rz_order["id"],
            "amount":            amount_paise,
            "currency":          "INR",
            "key":               RAZORPAY_KEY_ID
        })
    except Exception as e:
        return jsonify({"message": f"Razorpay error: {str(e)}"}), 500


@app.route("/verify-payment", methods=["POST"])
def verify_payment():
    if "user_id" not in session:
        return jsonify({"message": "Not logged in"}), 401

    data               = request.get_json()
    rz_order_id        = data.get("razorpay_order_id", "")
    rz_payment_id      = data.get("razorpay_payment_id", "")
    rz_signature       = data.get("razorpay_signature", "")
    payment_method     = data.get("payment_method", "razorpay")

    # Verify signature
    msg      = f"{rz_order_id}|{rz_payment_id}".encode()
    expected = hmac.new(
        RAZORPAY_KEY_SECRET.encode(), msg, hashlib.sha256
    ).hexdigest()

    if expected != rz_signature:
        return jsonify({"message": "Payment verification failed"}), 400

    # Payment verified — place the order
    user_id = session["user_id"]
    conn    = get_db_connection()
    cursor  = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT cart.product_id, cart.quantity, products.price, products.name
        FROM cart JOIN products ON cart.product_id = products.id
        WHERE cart.user_id = %s
    """, (user_id,))
    cart_items = cursor.fetchall()

    if not cart_items:
        cursor.close(); conn.close()
        return jsonify({"message": "Cart is empty"}), 400

    subtotal = sum(int(i["quantity"]) * float(i["price"]) for i in cart_items)
    tax      = round(subtotal * 0.05)
    total    = subtotal + tax

    cursor2 = conn.cursor()
    try:
        cursor2.execute(
            "INSERT INTO orders (user_id, total_amount, payment_method, payment_id) VALUES (%s,%s,%s,%s)",
            (user_id, total, payment_method, rz_payment_id)
        )
    except Exception:
        # Fallback if payment_method/payment_id columns don't exist yet
        cursor2.execute(
            "INSERT INTO orders (user_id, total_amount) VALUES (%s,%s)",
            (user_id, total)
        )
    order_id = cursor2.lastrowid

    for item in cart_items:
        cursor2.execute(
            "INSERT INTO order_items (order_id, product_id, quantity, price) VALUES (%s,%s,%s,%s)",
            (order_id, item["product_id"], item["quantity"], item["price"])
        )

    cursor2.execute("DELETE FROM cart WHERE user_id = %s", (user_id,))
    conn.commit()
    cursor.close(); cursor2.close(); conn.close()

    return jsonify({"message": "Payment successful!", "order_id": order_id})


@app.route("/checkout", methods=["POST"])
def checkout():
    if "user_id" not in session:
        return jsonify({"message": "Not logged in"}), 401

    user_id = session["user_id"]
    conn    = get_db_connection()
    cursor  = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT cart.product_id, cart.quantity, products.price
        FROM cart
        JOIN products ON cart.product_id = products.id
        WHERE cart.user_id = %s
    """, (user_id,))
    cart_items = cursor.fetchall()

    if not cart_items:
        cursor.close(); conn.close()
        return jsonify({"message": "Cart is empty"}), 400

    total = sum(i["quantity"] * i["price"] for i in cart_items)
    cursor.execute("INSERT INTO orders (user_id, total_amount) VALUES (%s, %s)", (user_id, total))
    order_id = cursor.lastrowid

    for item in cart_items:
        cursor.execute(
            "INSERT INTO order_items (order_id, product_id, quantity, price) VALUES (%s,%s,%s,%s)",
            (order_id, item["product_id"], item["quantity"], item["price"])
        )

    cursor.execute("DELETE FROM cart WHERE user_id = %s", (user_id,))
    conn.commit()
    cursor.close(); conn.close()
    return jsonify({"message": "Order placed successfully!", "order_id": order_id})


# ===========================
# ORDERS (CUSTOMER)
# ===========================

@app.route("/my-orders", methods=["GET"])
def my_orders():
    if "user_id" not in session:
        return jsonify({"message": "Not logged in"}), 401

    user_id = session["user_id"]
    conn    = get_db_connection()
    cursor  = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT * FROM orders WHERE user_id = %s ORDER BY order_date DESC
    """, (user_id,))
    orders = cursor.fetchall()

    result = []
    for order in orders:
        cursor.execute("""
            SELECT products.name, order_items.quantity, order_items.price
            FROM order_items
            JOIN products ON order_items.product_id = products.id
            WHERE order_items.order_id = %s
        """, (order["id"],))
        items = cursor.fetchall()
        result.append({
            "order_id": order["id"],
            "total":    order["total_amount"],
            "date":     order["order_date"].strftime("%d %b %Y, %I:%M %p") if order["order_date"] else "—",
            "status":   order["status"],
            "items":    items
        })

    cursor.close(); conn.close()
    return jsonify({"orders": result})


# ===========================
# ADMIN — ORDERS
# ===========================

@app.route("/cancel-order", methods=["POST"])
def cancel_order():
    if "user_id" not in session:
        return jsonify({"message": "Not logged in"}), 401

    data     = request.get_json()
    order_id = data.get("order_id")
    user_id  = session["user_id"]

    conn   = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Verify order belongs to this user and is still cancellable
    cursor.execute(
        "SELECT id, status FROM orders WHERE id = %s AND user_id = %s",
        (order_id, user_id)
    )
    order = cursor.fetchone()

    if not order:
        cursor.close(); conn.close()
        return jsonify({"message": "Order not found"}), 404

    if order["status"] not in ("Pending", "Preparing"):
        cursor.close(); conn.close()
        return jsonify({"message": f"Cannot cancel order with status: {order['status']}"}), 400

    cursor2 = conn.cursor()
    cursor2.execute(
        "UPDATE orders SET status = 'Cancelled' WHERE id = %s AND user_id = %s",
        (order_id, user_id)
    )
    conn.commit()
    cursor.close(); cursor2.close(); conn.close()
    return jsonify({"message": "Order cancelled successfully"})


@app.route("/admin/orders", methods=["GET"])
def admin_orders():
    if "user_id" not in session or session.get("role") != "admin":
        return jsonify({"message": "Unauthorized"}), 403

    conn   = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT orders.*, users.name AS user_name, users.email AS user_email
        FROM orders
        JOIN users ON orders.user_id = users.id
        ORDER BY order_date DESC
    """)
    orders = cursor.fetchall()

    grouped = {"Pending": [], "Preparing": [], "Out for Delivery": [], "Completed": [], "Cancelled": []}

    for order in orders:
        cursor.execute("""
            SELECT products.name, order_items.quantity
            FROM order_items
            JOIN products ON order_items.product_id = products.id
            WHERE order_items.order_id = %s
        """, (order["id"],))
        items = cursor.fetchall()
        order_data = {
            "order_id":   order["id"],
            "user_name":  order["user_name"],
            "user_email": order["user_email"],
            "date":       order["order_date"].strftime("%d %b %Y, %I:%M %p") if order["order_date"] else "—",
            "total":      order["total_amount"],
            "status":     order["status"],
            "items":      items
        }
        if order["status"] in grouped:
            grouped[order["status"]].append(order_data)

    cursor.close(); conn.close()
    return jsonify({"grouped_orders": grouped})


@app.route("/admin/update-status", methods=["POST"])
def update_order_status():
    if "user_id" not in session or session.get("role") != "admin":
        return jsonify({"message": "Unauthorized"}), 403

    data     = request.get_json()
    order_id = data.get("order_id")
    status   = data.get("status")

    conn   = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE orders SET status=%s WHERE id=%s", (status, order_id))
    conn.commit()
    cursor.close(); conn.close()
    return jsonify({"message": "Status updated"})


# ===========================
# ADMIN — MENU
# ===========================

@app.route("/admin/get-all-products", methods=["GET"])
def get_all_products():
    if "user_id" not in session or session.get("role") != "admin":
        return jsonify({"message": "Unauthorized"}), 403

    conn   = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT id, name, price, is_available,
               COALESCE(category, 'Hot Coffee') AS category,
               COALESCE(emoji, '☕') AS emoji
        FROM products ORDER BY id
    """)
    products = cursor.fetchall()
    cursor.close(); conn.close()
    return jsonify({"products": products})


@app.route("/admin/add-product", methods=["POST"])
def add_product():
    if "user_id" not in session or session.get("role") != "admin":
        return jsonify({"message": "Unauthorized"}), 403

    data     = request.get_json()
    name     = data.get("name")
    price    = data.get("price")
    category = data.get("category", "Hot Coffee")
    emoji    = data.get("emoji", "☕")
    desc     = data.get("description", "")

    conn   = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO products (name, price, is_available, category, emoji, description) VALUES (%s,%s,1,%s,%s,%s)",
        (name, price, category, emoji, desc)
    )
    new_id = cursor.lastrowid
    conn.commit()
    cursor.close(); conn.close()
    return jsonify({"message": "Added", "id": new_id})


@app.route("/admin/toggle-product", methods=["POST"])
def toggle_product():
    if "user_id" not in session or session.get("role") != "admin":
        return jsonify({"message": "Unauthorized"}), 403

    data       = request.get_json()
    product_id = data.get("product_id")

    conn   = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE products SET is_available = CASE WHEN is_available = 1 THEN 0 ELSE 1 END WHERE id=%s", (product_id,))
    conn.commit()
    cursor.close(); conn.close()
    return jsonify({"message": "Toggled"})


@app.route("/admin/remove-product", methods=["POST"])
def remove_product():
    if "user_id" not in session or session.get("role") != "admin":
        return jsonify({"message": "Unauthorized"}), 403

    data       = request.get_json()
    product_id = data.get("product_id")

    conn   = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM products WHERE id=%s", (product_id,))
    conn.commit()
    cursor.close(); conn.close()
    return jsonify({"message": "Removed"})


@app.route("/admin/update-price", methods=["POST"])
def update_price():
    if "user_id" not in session or session.get("role") != "admin":
        return jsonify({"message": "Unauthorized"}), 403

    data       = request.get_json()
    product_id = data.get("product_id")
    price      = data.get("price")

    conn   = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE products SET price=%s WHERE id=%s", (price, product_id))
    conn.commit()
    cursor.close(); conn.close()
    return jsonify({"message": "Price updated"})


# ===========================
# ADMIN — CUSTOMERS
# ===========================

@app.route("/admin/get-customers", methods=["GET"])
def get_customers():
    if "user_id" not in session or session.get("role") != "admin":
        return jsonify({"message": "Unauthorized"}), 403

    conn   = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT
            u.id, u.name, u.email, u.created_at, u.address,
            COUNT(DISTINCT o.id)             AS total_orders,
            COALESCE(SUM(o.total_amount), 0) AS total_spent
        FROM users u
        LEFT JOIN orders o ON u.id = o.user_id
        WHERE u.role = 'user'
        GROUP BY u.id, u.name, u.email, u.created_at, u.address
        ORDER BY total_spent DESC
    """)
    customers = cursor.fetchall()
    cursor.close(); conn.close()

    result = []
    for c in customers:
        result.append({
            "name":    c["name"],
            "email":   c["email"],
            "orders":  c["total_orders"],
            "spent":   float(c["total_spent"]),
            "joined":  c["created_at"].strftime("%b %Y") if c["created_at"] else "—",
            "active":  c["total_orders"] > 0,
            "address": json.loads(c["address"]) if c["address"] else None
        })
    return jsonify({"customers": result})


# ===========================
# PASSWORD RESET
# ===========================
import random, time
reset_codes = {}

@app.route("/forgot-password", methods=["POST"])
def forgot_password():
    data  = request.get_json()
    email = data.get("email", "").strip()

    conn   = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
    user = cursor.fetchone()
    cursor.close(); conn.close()

    if not user:
        return jsonify({"message": "Email not found"}), 404

    code = random.randint(100000, 999999)
    reset_codes[email] = { "code": code, "expires": time.time() + 600 }
    return jsonify({"code": code})


@app.route("/reset-password", methods=["POST"])
def reset_password():
    data     = request.get_json()
    email    = data.get("email", "").strip()
    password = data.get("password", "")

    entry = reset_codes.get(email)
    if not entry or time.time() > entry["expires"]:
        return jsonify({"message": "Reset code expired. Please try again."}), 400

    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
    conn   = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET password = %s WHERE email = %s",
                   (hashed.decode("utf-8"), email))
    conn.commit()
    cursor.close(); conn.close()

    reset_codes.pop(email, None)
    return jsonify({"message": "ok"})



# Address#
@app.route("/save-address", methods=["POST"])
def save_address():
    if "user_id" not in session:
        return jsonify({"message": "unauthorized"}), 401
    data = request.get_json()
    address_json = json.dumps(data)
    conn   = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET address = %s WHERE id = %s",
                   (address_json, session["user_id"]))
    conn.commit()
    cursor.close(); conn.close()
    return jsonify({"message": "ok"})


@app.route("/get-address", methods=["GET"])
def get_address():
    if "user_id" not in session:
        return jsonify({"message": "unauthorized"}), 401
    conn   = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT address FROM users WHERE id = %s", (session["user_id"],))
    user   = cursor.fetchone()
    cursor.close(); conn.close()
    address = json.loads(user["address"]) if user and user["address"] else None
    return jsonify({"address": address})

# ===========================
# RUN SERVER
# ===========================

if __name__ == "__main__":
    app.run(debug=True)

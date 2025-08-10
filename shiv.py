from flask import Flask, render_template_string, request, redirect, url_for, session
import sqlite3

app = Flask(__name__)
app.secret_key = "secret123"

DB = "bbaba.db"

# ---------- HTML Templates ----------
CUSTOMER_SHOP_SELECT_HTML = """
<!DOCTYPE html>
<html>
<head><title>Select Shop</title></head>
<body>
<h2>Select Shop and Enter Your Name</h2>
<form method="post" action="/customer/start_order">
    Shop ID: <input type="text" name="shop_id" required /><br><br>
    Your Name: <input type="text" name="customer_name" required /><br><br>
    <input type="submit" value="Start Order" />
</form>
</body>
</html>
"""

CUSTOMER_ORDER_HTML = """
<!DOCTYPE html>
<html>
<head><title>Customer Order - Shop {{ shop_id }}</title></head>
<body>
<h2>Welcome {{ customer_name }}! Place your order at Shop {{ shop_id }}</h2>
<p><strong>Current order:</strong> {{ ', '.join(order_items) if order_items else 'No items yet' }}</p>

<form method="post" action="/customer/add_item">
    Add item: <input type="text" name="item" required />
    <input type="submit" value="Add" />
</form>

<form method="post" action="/customer/confirm_order">
    <button type="submit" {% if not order_items %} disabled {% endif %}>Confirm Order</button>
</form>

<form method="post" action="/customer/cancel_order">
    <button type="submit">Cancel Order</button>
</form>
</body>
</html>
"""

SHOPKEEPER_LOGIN_HTML = """
<!DOCTYPE html>
<html>
<head><title>Shopkeeper Login</title></head>
<body>
<h2>Shopkeeper Login</h2>
<form method="post" action="/shopkeeper/dashboard">
    Enter your Shop ID: <input type="text" name="shop_id" required />
    <input type="submit" value="Login" />
</form>
</body>
</html>
"""

SHOPKEEPER_DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head><title>Shopkeeper Dashboard - Shop {{ shop_id }}</title></head>
<body>
<h2>Shopkeeper Dashboard for Shop {{ shop_id }}</h2>

<h3>Pending Orders</h3>
{% if pending_orders %}
    {% for order in pending_orders %}
        <div style="border:1px solid #ccc; margin-bottom:10px; padding:10px;">
            <strong>Order ID:</strong> {{ order['id'] }} <br>
            <strong>Customer:</strong> {{ order['customer_name'] }} <br>
            <strong>Items:</strong>
            <ul>
                {% for item in order['items'] %}
                    <li>{{ item }}</li>
                {% endfor %}
            </ul>
            <form method="post" action="/shopkeeper/confirm_order">
                <input type="hidden" name="order_id" value="{{ order['id'] }}" />
                <input type="hidden" name="shop_id" value="{{ shop_id }}" />
                <button type="submit">Confirm Order</button>
            </form>
        </div>
    {% endfor %}
{% else %}
    <p>No pending orders.</p>
{% endif %}

<h3>Confirmed Orders</h3>
{% if confirmed_orders %}
    {% for order in confirmed_orders %}
        <div style="border:1px solid #ccc; margin-bottom:10px; padding:10px; background:#e0ffe0;">
            <strong>Order ID:</strong> {{ order['id'] }} <br>
            <strong>Customer:</strong> {{ order['customer_name'] }} <br>
            <strong>Items:</strong>
            <ul>
                {% for item in order['items'] %}
                    <li>{{ item }}</li>
                {% endfor %}
            </ul>
            <em>Confirmed</em>
        </div>
    {% endfor %}
{% else %}
    <p>No confirmed orders.</p>
{% endif %}

<a href="/shopkeeper/logout">Logout</a>
</body>
</html>
"""

# --------------- DB Setup ----------------

def init_db():
    with sqlite3.connect(DB) as conn:
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                shop_id TEXT NOT NULL,
                customer_name TEXT NOT NULL,
                items TEXT NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('pending','confirmed'))
            )
        ''')
        conn.commit()

init_db()

# --------------- Helper Functions ----------------

def save_order(shop_id, customer_name, items):
    with sqlite3.connect(DB) as conn:
        c = conn.cursor()
        c.execute('INSERT INTO orders (shop_id, customer_name, items, status) VALUES (?, ?, ?, ?)',
                  (shop_id, customer_name, ','.join(items), 'pending'))
        conn.commit()

def get_orders_by_shop(shop_id):
    with sqlite3.connect(DB) as conn:
        c = conn.cursor()
        c.execute('SELECT id, customer_name, items, status FROM orders WHERE shop_id=? ORDER BY id DESC', (shop_id,))
        rows = c.fetchall()
        orders = []
        for r in rows:
            orders.append({
                'id': r[0],
                'customer_name': r[1],
                'items': r[2].split(',') if r[2] else [],
                'status': r[3]
            })
        return orders

def confirm_order(order_id):
    with sqlite3.connect(DB) as conn:
        c = conn.cursor()
        c.execute('UPDATE orders SET status="confirmed" WHERE id=?', (order_id,))
        conn.commit()

# --------------- Routes ----------------

@app.route("/")
def index():
    return "<h1>Welcome to BBABA - Multi Shop Order System</h1><p>Go to /customer or /shopkeeper</p>"

# --- CUSTOMER ROUTES ---

@app.route("/customer", methods=["GET"])
def customer_shop_select():
    return render_template_string(CUSTOMER_SHOP_SELECT_HTML)

@app.route("/customer/start_order", methods=["POST"])
def customer_start_order():
    shop_id = request.form['shop_id'].strip()
    customer_name = request.form['customer_name'].strip()
    if not shop_id or not customer_name:
        return "Shop ID and Customer Name required", 400

    # Save to session
    session['shop_id'] = shop_id
    session['customer_name'] = customer_name
    session['order_items'] = []

    return redirect(url_for("customer_order"))

@app.route("/customer/order", methods=["GET"])
def customer_order():
    if 'shop_id' not in session or 'customer_name' not in session:
        return redirect(url_for("customer_shop_select"))
    return render_template_string(CUSTOMER_ORDER_HTML,
                                  shop_id=session['shop_id'],
                                  customer_name=session['customer_name'],
                                  order_items=session.get('order_items', []))

@app.route("/customer/add_item", methods=["POST"])
def customer_add_item():
    item = request.form.get('item', '').strip()
    if item:
        order_items = session.get('order_items', [])
        order_items.append(item)
        session['order_items'] = order_items
    return redirect(url_for("customer_order"))

@app.route("/customer/confirm_order", methods=["POST"])
def customer_confirm_order():
    if 'shop_id' not in session or 'customer_name' not in session:
        return redirect(url_for("customer_shop_select"))
    order_items = session.get('order_items', [])
    if not order_items:
        return redirect(url_for("customer_order"))
    save_order(session['shop_id'], session['customer_name'], order_items)
    # Clear order from session after saving
    session.pop('order_items', None)
    return f"Thank you {session['customer_name']}! Your order has been placed for Shop {session['shop_id']}."

@app.route("/customer/cancel_order", methods=["POST"])
def customer_cancel_order():
    session.pop('order_items', None)
    return redirect(url_for("customer_order"))

# --- SHOPKEEPER ROUTES ---

@app.route("/shopkeeper", methods=["GET"])
def shopkeeper_login():
    return render_template_string(SHOPKEEPER_LOGIN_HTML)

@app.route("/shopkeeper/dashboard", methods=["POST"])
def shopkeeper_dashboard():
    shop_id = request.form.get('shop_id', '').strip()
    if not shop_id:
        return "Shop ID required", 400
    session['shop_id'] = shop_id
    return redirect(url_for("shopkeeper_view_orders"))

@app.route("/shopkeeper/orders", methods=["GET"])
def shopkeeper_view_orders():
    if 'shop_id' not in session:
        return redirect(url_for("shopkeeper_login"))
    shop_id = session['shop_id']
    orders = get_orders_by_shop(shop_id)
    pending = [o for o in orders if o['status'] == 'pending']
    confirmed = [o for o in orders if o['status'] == 'confirmed']
    return render_template_string(SHOPKEEPER_DASHBOARD_HTML,
                                  shop_id=shop_id,
                                  pending_orders=pending,
                                  confirmed_orders=confirmed)

@app.route("/shopkeeper/confirm_order", methods=["POST"])
def shopkeeper_confirm_order_route():
    order_id = request.form.get('order_id')
    shop_id = request.form.get('shop_id')
    if not order_id or not shop_id:
        return "Missing order or shop id", 400
    if 'shop_id' not in session or session['shop_id'] != shop_id:
        return "Unauthorized", 403
    confirm_order(order_id)
    return redirect(url_for("shopkeeper_view_orders"))

@app.route("/shopkeeper/logout")
def shopkeeper_logout():
    session.pop('shop_id', None)
    return redirect(url_for("shopkeeper_login"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)

from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import os
from werkzeug.utils import secure_filename
from functools import wraps

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# -------------------------
# Login required decorator
# -------------------------
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Debug route to list all registered routes
@app.route('/routes')
def show_routes():
    output = []
    for rule in app.url_map.iter_rules():
        output.append(f"{rule}")
    return '<br>'.join(output)

# Update payment status for orders via AJAX
@app.route('/update_payment_status', methods=['POST'])
@login_required
def update_payment_status_ajax():
    data = request.get_json()
    order_id = data.get('order_id')
    status = data.get('status')
    if status not in ['Paid', 'Credit'] or not order_id:
        return {'success': False, 'error': 'Invalid input'}, 400
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('UPDATE orders SET status = ? WHERE id = ?', (status, order_id))
    conn.commit()
    conn.close()
    return {'success': True}



# Order Details Route (placed after all imports, app, and login_required)
@app.route('/order_details/<int:order_id>')
@login_required
def order_details(order_id):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('''
        SELECT o.id, c.name, c.mobile, c.email, c.address,
               o.service, o.amount, o.payment_mode,
               o.order_date, o.status
        FROM orders o
        JOIN customers c ON o.customer_id = c.id
        WHERE o.id = ?
    ''', (order_id,))
    order = c.fetchone()
    conn.close()
    if not order:
        flash('Order not found', 'error')
        return redirect(url_for('completed_orders'))
    return render_template('order_details.html', order=order)


# -------------------------
# Database initialization
# -------------------------
def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY,
                    username TEXT,
                    password TEXT)''')

    c.execute('''CREATE TABLE IF NOT EXISTS customers (
                    id INTEGER PRIMARY KEY,
                    name TEXT,
                    contact TEXT)''')
    # Add new columns if they don't exist
    try:
        c.execute('ALTER TABLE customers ADD COLUMN mobile TEXT')
    except sqlite3.OperationalError:
        pass
    try:
        c.execute('ALTER TABLE customers ADD COLUMN email TEXT')
    except sqlite3.OperationalError:
        pass
    try:
        c.execute('ALTER TABLE customers ADD COLUMN address TEXT')
    except sqlite3.OperationalError:
        pass

    c.execute('''CREATE TABLE IF NOT EXISTS orders (
                    id INTEGER PRIMARY KEY,
                    customer_id INTEGER,
                    service TEXT,
                    order_date TEXT,
                    amount REAL,
                    payment_mode TEXT,
                    status TEXT)''')

    c.execute('''CREATE TABLE IF NOT EXISTS payments (
                    id INTEGER PRIMARY KEY,
                    amount REAL,
                    paid INTEGER,
                    payment_date TEXT)''')

    c.execute('''CREATE TABLE IF NOT EXISTS employees (
                    id INTEGER PRIMARY KEY,
                    name TEXT,
                    role TEXT)''')
    # Add new columns if they don't exist
    try:
        c.execute('ALTER TABLE employees ADD COLUMN mobile TEXT')
    except sqlite3.OperationalError:
        pass
    try:
        c.execute('ALTER TABLE employees ADD COLUMN email TEXT')
    except sqlite3.OperationalError:
        pass
    try:
        c.execute('ALTER TABLE employees ADD COLUMN address TEXT')
    except sqlite3.OperationalError:
        pass

    c.execute('''CREATE TABLE IF NOT EXISTS expenses (
                    id INTEGER PRIMARY KEY,
                    amount REAL,
                    description TEXT,
                    date TEXT)''')

    # Add default admin user if not exists
    c.execute('SELECT * FROM users WHERE username=?', ('admin',))
    if not c.fetchone():
        c.execute('INSERT INTO users (username, password) VALUES (?, ?)', ('admin', 'admin123'))

    conn.commit()
    conn.close()


# -------------------------
# Auth Routes
# -------------------------
@app.route('/')
def index():
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute('SELECT * FROM users WHERE username=? AND password=?', (username, password))
        user = c.fetchone()
        conn.close()
        if user:
            session['user_id'] = user[0]
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', error='Invalid credentials')
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))


@app.route('/dashboard')
@login_required
def dashboard():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    # Total customers
    c.execute('SELECT COUNT(*) FROM customers')
    total_orders = c.fetchone()[0]
    # Pending orders
    c.execute("SELECT COUNT(*) FROM orders WHERE status = 'pending'")
    pending_orders = c.fetchone()[0]
    # Completed orders
    c.execute("SELECT COUNT(*) FROM orders WHERE status IN ('Completed', 'Paid', 'Credit')")
    completed_orders = c.fetchone()[0]
    # Working orders (number of employees)
    c.execute('SELECT COUNT(*) FROM employees')
    working_orders = c.fetchone()[0]
    # Number of credit customers
    c.execute("SELECT COUNT(DISTINCT customers.id) FROM customers JOIN orders ON customers.id = orders.customer_id WHERE orders.status = 'Credit'")
    credit_customers_count = c.fetchone()[0]
    conn.close()
    return render_template('dashboard.html', total_orders=total_orders, pending_orders=pending_orders, completed_orders=completed_orders, working_orders=working_orders, credit_customers_count=credit_customers_count)


# -------------------------
# Customer Dropdown Routes
# -------------------------
@app.route('/add_order', methods=['GET', 'POST'])
@login_required
def add_order():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    # Get all customers for selection
    c.execute('SELECT id, name FROM customers')
    customers = c.fetchall()
    if request.method == 'POST':
        customer_id = request.form['customer_id']
        services = request.form.getlist('service')
        amount = request.form['amount']
        payment_mode = request.form['payment_mode']
        order_date = request.form['order_date']
        for service in services:
            # Always initialize payment_mode to 'Unpaid' for new orders
            c.execute('INSERT INTO orders (customer_id, service, order_date, amount, payment_mode, status) VALUES (?, ?, ?, ?, ?, ?)', (customer_id, service, order_date, amount, 'Unpaid', 'pending'))
            c.execute('INSERT INTO payments (amount, paid, payment_date) VALUES (?, ?, ?)', (amount, 0, order_date))
        conn.commit()
        conn.close()
        return redirect(url_for('view_order'))
    conn.close()
    return render_template('add_order.html', customers=customers)


@app.route('/view_order')
@login_required
def view_order():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    # Get orders with status 'pending' and join with customer details
    c.execute('''SELECT orders.id, customers.name, customers.contact, customers.mobile, customers.email, customers.address, orders.service, orders.order_date, orders.status
                FROM orders
                JOIN customers ON orders.customer_id = customers.id
                WHERE orders.status = ?''', ('pending',))
    pending_orders = c.fetchall()
    conn.close()
    return render_template('view_order.html', pending_orders=pending_orders)


@app.route('/customer_ledger')
@login_required
def customer_ledger():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    # Find customers with credit orders
    c.execute('''
        SELECT DISTINCT c.id, c.name, c.mobile, c.email, c.address
        FROM customers c
        JOIN orders o ON c.id = o.customer_id
        WHERE o.status = 'Credit'
    ''')
    credit_customers = c.fetchall()
    conn.close()
    return render_template('credit_customers.html', credit_customers=credit_customers)


@app.route('/view_customer', methods=['GET', 'POST'])
@login_required
def view_customer():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    if request.method == 'POST':
        name = request.form['name']
        mobile = request.form['mobile']
        email = request.form['email']
        address = request.form['address']
        c.execute('INSERT INTO customers (name, mobile, email, address) VALUES (?, ?, ?, ?)', (name, mobile, email, address))
        conn.commit()
        conn.close()
        return redirect(url_for('view_customer'))
    c.execute('SELECT id, name, mobile, email, address FROM customers')
    customers = c.fetchall()
    conn.close()
    return render_template('view_customer.html', customers=customers)

@app.route('/payment_voucher')
@login_required
def payment_voucher():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    # Find customers with paid orders
    c.execute('''
        SELECT DISTINCT c.id, c.name, c.mobile, c.email, c.address
        FROM customers c
        JOIN orders o ON c.id = o.customer_id
        WHERE o.status = 'Paid'
    ''')
    paid_customers = c.fetchall()
    conn.close()
    return render_template('paid_customers.html', paid_customers=paid_customers)


# -------------------------
# Expense Management
# -------------------------
@app.route('/expenses', methods=['GET', 'POST'])
@login_required
def expenses():
    import re
    from datetime import datetime
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    search = request.args.get('search', '')
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')

    if request.method == 'POST':
        amount = request.form['amount']
        description = request.form['description']
        date = request.form['date']
        c.execute('INSERT INTO expenses (amount, description, date) VALUES (?, ?, ?)', (amount, description, date))
        conn.commit()

    query = 'SELECT id, amount, description, date FROM expenses WHERE 1=1'
    params = []
    # Check if search is a date in DD/MM/YYYY format
    date_match = re.match(r'^(\d{2})/(\d{2})/(\d{4})$', search)
    if date_match:
        # Convert to YYYY-MM-DD for SQLite
        day, month, year = date_match.groups()
        search_date = f"{year}-{month}-{day}"
        query += ' AND date = ?'
        params.append(search_date)
    elif search:
        query += ' AND description LIKE ?'
        params.append('%' + search + '%')
    if start_date:
        query += ' AND date >= ?'
        params.append(start_date)
    if end_date:
        query += ' AND date <= ?'
        params.append(end_date)
    c.execute(query, params)
    expenses = c.fetchall()
    conn.close()
    return render_template('expenses.html', expenses=expenses)

# Expense History Route
@app.route('/expense_history')
@login_required
def expense_history():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('SELECT id, amount, description, date FROM expenses ORDER BY date DESC')
    expenses = c.fetchall()
    conn.close()
    return render_template('expense_history.html', expenses=expenses)


@app.route('/delete_expense/<int:expense_id>', methods=['POST'])
@login_required
def delete_expense(expense_id):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('DELETE FROM expenses WHERE id=?', (expense_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('expenses'))


# -------------------------
# User Management
# -------------------------
@app.route('/users', methods=['GET', 'POST'])
@login_required
def users():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        c.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, password))
        conn.commit()
    c.execute('SELECT id, username FROM users')
    users = c.fetchall()
    conn.close()
    return render_template('users.html', users=users)


@app.route('/edit_user/<int:user_id>', methods=['GET', 'POST'])
@login_required
def edit_user(user_id):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        c.execute('UPDATE users SET username=?, password=? WHERE id=?', (username, password, user_id))
        conn.commit()
        conn.close()
        return redirect(url_for('users'))
    c.execute('SELECT id, username, password FROM users WHERE id=?', (user_id,))
    user = c.fetchone()
    conn.close()
    return render_template('edit_user.html', user=user)


@app.route('/delete_user/<int:user_id>', methods=['POST'])
@login_required
def delete_user(user_id):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('DELETE FROM users WHERE id=?', (user_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('users'))


# -------------------------
# Customer Management
# -------------------------
@app.route('/customers', methods=['GET', 'POST'])
@login_required
def customers():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    if request.method == 'POST':
        name = request.form['name']
        mobile = request.form['mobile']
        email = request.form['email']
        address = request.form['address']
        c.execute('INSERT INTO customers (name, mobile, email, address) VALUES (?, ?, ?, ?)', (name, mobile, email, address))
        conn.commit()
    c.execute('SELECT id, name, mobile, email, address FROM customers')
    customers = c.fetchall()
    conn.close()
    return render_template('view_customer.html', customers=customers)


    # Removed job completion by job_id


@app.route('/edit_customer/<int:customer_id>', methods=['GET', 'POST'])
@login_required
def edit_customer(customer_id):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    if request.method == 'POST':
        name = request.form['name']
        mobile = request.form['mobile']
        email = request.form['email']
        address = request.form['address']
        c.execute('UPDATE customers SET name=?, mobile=?, email=?, address=? WHERE id=?', (name, mobile, email, address, customer_id))
        conn.commit()
        conn.close()
        return redirect(url_for('view_customer'))
    c.execute('SELECT id, name, contact, mobile, email, address FROM customers WHERE id=?', (customer_id,))
    customer = c.fetchone()
    conn.close()
    return render_template('edit_customer.html', customer=customer)


@app.route('/delete_customer/<int:customer_id>', methods=['POST'])
@login_required
def delete_customer(customer_id):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('DELETE FROM customers WHERE id=?', (customer_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('customers'))


# -------------------------
# Employee Management
# -------------------------
@app.route('/employees', methods=['GET', 'POST'])
@login_required
def employees():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    if request.method == 'POST':
        name = request.form['name']
        role = request.form['role']
        mobile = request.form.get('mobile', '')
        email = request.form.get('email', '')
        address = request.form.get('address', '')
        c.execute('INSERT INTO employees (name, role, mobile, email, address) VALUES (?, ?, ?, ?, ?)', (name, role, mobile, email, address))
        conn.commit()
    c.execute('SELECT id, name, role, mobile, email, address FROM employees')
    employees = c.fetchall()
    conn.close()
    return render_template('employees.html', employees=employees)


@app.route('/edit_employee/<int:employee_id>', methods=['GET', 'POST'])
@login_required
def edit_employee(employee_id):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    if request.method == 'POST':
        name = request.form['name']
        role = request.form['role']
        mobile = request.form.get('mobile', '')
        email = request.form.get('email', '')
        address = request.form.get('address', '')
        c.execute('UPDATE employees SET name=?, role=?, mobile=?, email=?, address=? WHERE id=?', (name, role, mobile, email, address, employee_id))
        conn.commit()
        conn.close()
        return redirect(url_for('employees'))
    c.execute('SELECT id, name, role, mobile, email, address FROM employees WHERE id=?', (employee_id,))
    employee = c.fetchone()
    conn.close()
    return render_template('edit_employee.html', employee=employee)
@app.route('/completed_orders', methods=['GET', 'POST'])
def complete_order():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    if request.method == 'POST':
        order_id = request.form.get('order_id')
        if order_id:
            c.execute("UPDATE orders SET status = 'Completed' WHERE id = ?", (order_id,))
            conn.commit()
    c.execute("SELECT orders.id, customers.name, orders.service, orders.amount, orders.status, orders.order_date FROM orders JOIN customers ON orders.customer_id = customers.id WHERE orders.status IN ('Completed', 'Paid', 'Credit')")
    completed_orders = c.fetchall()
    conn.close()
    # completed_orders columns: 0=id, 1=name, 2=service, 3=amount, 4=status, 5=order_date
    return render_template('completed_orders.html', completed_orders=completed_orders)


@app.route('/delete_employee/<int:employee_id>', methods=['POST'])
@login_required
def delete_employee(employee_id):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('DELETE FROM employees WHERE id=?', (employee_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('employees'))


@app.route('/print_order/<int:order_id>')
@login_required
def print_order(order_id):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    
    # Get complete order details with customer information
    c.execute('''
        SELECT o.id, c.name, c.mobile, c.email, c.address, 
               o.service, o.amount, o.payment_mode, 
               o.order_date, o.status
        FROM orders o
        JOIN customers c ON o.customer_id = c.id
        WHERE o.id = ?
    ''', (order_id,))
    
    order = c.fetchone()
    conn.close()
    
    if not order:
        flash('Order not found', 'error')
        return redirect(url_for('view_order'))
    
    # Load company info from settings
    company_name = 'Bekabe Printing Press'
    company_address = '123 Main Street, Accra, Ghana'
    company_phone = '+233 55 123 4567'
    company_logo = None
    if os.path.exists('company_settings.txt'):
        with open('company_settings.txt', 'r', encoding='utf-8') as f:
            lines = f.read().splitlines()
            if len(lines) >= 3:
                company_name = lines[0]
                company_address = lines[1]
                company_phone = lines[2]
            if len(lines) >= 4:
                company_logo = lines[3]
    return render_template('print_order.html', order=order, company_name=company_name, company_address=company_address, company_phone=company_phone, company_logo=company_logo)


# Service route (must be above main block)
@app.route('/service', methods=['GET', 'POST'])
@login_required
def service():
    sticker_price = None
    dtf_price = None
    banner_price = None
    transparent_price = None
    if request.method == 'POST':
        try:
            service_type = request.form.get('service_type', 'sticker')
            if service_type == 'sticker':
                qty = float(request.form.get('qty', 0))
                height = float(request.form.get('height', 0))
                width = float(request.form.get('width', 0))
                size_unit = request.form.get('size_unit', 'ft')
                if size_unit == 'in':
                    raw_price = 2.2 * qty * (height * width) / 144
                else:
                    raw_price = 2.2 * qty * height * width
                sticker_price = f"GHC {raw_price:,.1f}"
            elif service_type == 'dtf':
                qty = float(request.form.get('dtf_qty', 0))
                dtf_size = request.form.get('dtf_size', 'A4')
                if dtf_size == 'A3':
                    raw_price = 14 * qty
                else:
                    raw_price = 7 * qty
                dtf_price = f"GHC {raw_price:,.1f}"
            elif service_type == 'banner':
                qty = float(request.form.get('banner_qty', 0))
                height = float(request.form.get('banner_height', 0))
                width = float(request.form.get('banner_width', 0))
                size_unit = request.form.get('banner_size_unit', 'ft')
                if size_unit == 'in':
                    raw_price = 2.5 * qty * (height * width) / 144
                else:
                    raw_price = 2.5 * qty * height * width
                banner_price = f"GHC {raw_price:,.1f}"
            elif service_type == 'transparent':
                qty = float(request.form.get('transparent_qty', 0))
                height = float(request.form.get('transparent_height', 0))
                width = float(request.form.get('transparent_width', 0))
                size_unit = request.form.get('transparent_size_unit', 'ft')
                if size_unit == 'in':
                    raw_price = 1.9 * qty * height * width / 144
                else:
                    raw_price = 1.9 * qty * height * width
                transparent_price = f"GHC {raw_price:,.1f}"
            elif service_type == 'onewayvision':
                qty = float(request.form.get('onewayvision_qty', 0))
                height = float(request.form.get('onewayvision_height', 0))
                width = float(request.form.get('onewayvision_width', 0))
                size_unit = request.form.get('onewayvision_size_unit', 'ft')
                if size_unit == 'in':
                    raw_price = 4.2 * qty * (height * width) / 144
                else:
                    raw_price = 4.2 * qty * height * width
                onewayvision_price = f"GHC {raw_price:,.1f}"
        except (TypeError, ValueError):
            sticker_price = 'Invalid input.'
            dtf_price = 'Invalid input.'
            banner_price = 'Invalid input.'
            transparent_price = 'Invalid input.'
    return render_template('service.html', sticker_price=sticker_price, dtf_price=dtf_price, banner_price=banner_price, transparent_price=transparent_price)


# -------------------------
# Settings route
# -------------------------
@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    company_name = 'Bekabe Printing Press'
    company_address = '123 Main Street, Accra, Ghana'
    company_phone = '+233 55 123 4567'
    company_logo = None
    message = None
    # Load saved settings if available
    if os.path.exists('company_settings.txt'):
        with open('company_settings.txt', 'r', encoding='utf-8') as f:
            lines = f.read().splitlines()
            if len(lines) >= 3:
                company_name = lines[0]
                company_address = lines[1]
                company_phone = lines[2]
            if len(lines) >= 4:
                company_logo = lines[3]
    if request.method == 'POST':
        company_name = request.form.get('company_name', company_name)
        company_address = request.form.get('company_address', company_address)
        company_phone = request.form.get('company_phone', company_phone)
        logo_file = request.files.get('company_logo')
        if logo_file and hasattr(logo_file, 'filename') and logo_file.filename:
            filename = secure_filename(logo_file.filename)
            upload_folder = os.path.join('static', 'uploads')
            os.makedirs(upload_folder, exist_ok=True)
            logo_file.save(os.path.join(upload_folder, filename))
            company_logo = filename
        # Save settings
        with open('company_settings.txt', 'w', encoding='utf-8') as f:
            f.write(f"{company_name}\n{company_address}\n{company_phone}\n{company_logo if company_logo else ''}")
        message = 'Settings updated successfully.'
    return render_template('settings.html', company_name=company_name, company_address=company_address, company_phone=company_phone, company_logo=company_logo, message=message)

# -------------------------
# Run app
# -------------------------
if __name__ == '__main__':
    init_db()
    app.run(debug=True)
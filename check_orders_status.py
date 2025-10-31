import sqlite3

conn = sqlite3.connect('database.db')
c = conn.cursor()

# Show all orders and their status
c.execute('SELECT id, service, amount, status FROM orders')
orders = c.fetchall()

print('Order ID | Service | Amount | Status')
for order in orders:
    print(order)

conn.close()

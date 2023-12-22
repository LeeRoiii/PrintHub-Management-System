import sqlite3
import datetime

DATABASE_NAME = 'orders.db'

def create_connection():
    return sqlite3.connect(DATABASE_NAME)
def create_orders_table():
    # Create a new connection and cursor
    conn = create_connection()
    cursor = conn.cursor()

    # Create the 'orders' table if it doesn't exist
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY,
        sender_id TEXT NOT NULL,
        user_name TEXT NOT NULL,
        file_name TEXT NOT NULL,
        copies INTEGER NOT NULL,
        color TEXT NOT NULL,
        instructions TEXT,
        order_status TEXT DEFAULT 'Pending',
        archived TEXT DEFAULT 'No',
        print_cost REAL DEFAULT 'Waiting for Process', 
        date TEXT
    )
    ''')

    conn.commit()
    cursor.close()
    conn.close()

    
def update_order_status(file_name, new_status, print_cost):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE orders SET order_status = ?, print_cost = ? WHERE file_name = ?", (new_status, print_cost, file_name))
    conn.commit()
    cursor.close()
    conn.close()

    


def get_all_orders():
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM orders")
    orders = cursor.fetchall()
    cursor.close()
    conn.close()
    return orders

# Initialize the orders table
create_orders_table()
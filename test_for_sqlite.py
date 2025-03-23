#%%
import sqlite3

# Connect to SQLite database (or create it if it doesn't exist)
conn = sqlite3.connect('example.db')

# Create a cursor object
cur = conn.cursor()

# Create a table
cur.execute('''
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    age INTEGER NOT NULL
)
''')

# Insert some data
cur.execute('''
INSERT INTO users (name, age) VALUES (?, ?)
''', ('Alice', 30))

cur.execute('''
INSERT INTO users (name, age) VALUES (?, ?)
''', ('Bob', 25))

# Commit the changes
conn.commit()

# Query the data
cur.execute('SELECT * FROM users')
rows = cur.fetchall()

# Print the data
for row in rows:
    print(row)

# Close the connection
conn.close()
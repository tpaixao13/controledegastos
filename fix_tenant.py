import sqlite3
conn = sqlite3.connect("instance/gastos.db")
conn.execute("UPDATE tenants SET name='Paixão', code='paixao' WHERE code='default'")
conn.commit()
rows = conn.execute("SELECT id, name, code FROM tenants").fetchall()
print("Tenants:", rows)
conn.close()

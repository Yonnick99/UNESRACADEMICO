import psycopg2

db_name = 'unesr-academico'   # nombre de la BD
db_user = 'postgres'          # usuario
db_password = 'admin'
db_host = 'localhost'         # en tu settings es localhost
db_port = '5432'

print("Intentando conectar a la base de datos...")
print(f"Host: {db_host}:{db_port}")
print(f"BD: {db_name}")
print(f"Usuario: {db_user}\n")

try:
    conexion = psycopg2.connect(
        dbname=db_name,
        user=db_user,
        password=db_password,
        host=db_host,
        port=db_port
    )
    cursor = conexion.cursor()
    cursor.execute("SELECT 1")
    print("✅ ¡Conexión exitosa!", cursor.fetchone())
    cursor.close()
    conexion.close()
except Exception as error:
    print("❌ Error:", error)

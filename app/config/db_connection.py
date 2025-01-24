import mysql.connector
from utils.logger import logger

class DatabaseConnection:
    def __init__(self, host, user, password, database):
        self.host = host
        self.user = user
        self.password = password
        self.database = database

    def ejecutar_query(self, query, params=None):
        try:
            logger.info(f"Iniciando la conexión a la base de datos {self.database}")
            # Attempt to connect to the database
            with mysql.connector.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                database=self.database
            ) as conn:
                if conn.is_connected():
                    logger.info(f"Conexión a la base de datos {self.database} exitosa")

                with conn.cursor(dictionary=True) as cursor:
                    logger.debug(f"Ejecutando la consulta: {query} con parámetros: {params}")
                    cursor.execute(query, params)
                    resultados = cursor.fetchall()
                    logger.info("Consulta ejecutada correctamente")
                    return resultados

        except mysql.connector.Error as err:
            logger.error(f"Error en la consulta a la base de datos: {err}")
            return []

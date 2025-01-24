import mysql.connector
import os
from utils.logger import logger

class DatabaseConnection:
    def __init__(self, host, user, password, database, ssl_ca=None):
        self.host = host
        self.user = user
        self.password = password
        self.database = database
        self.ssl_ca = ssl_ca

    def ejecutar_query(self, query, params=None):
        try:
            logger.info(f"Iniciando la conexión a la base de datos {self.database}")

            # Intentar conectarse a la base de datos usando SSL si se proporciona
            connection_params = {
                "host": self.host,
                "user": self.user,
                "password": self.password,
                "database": self.database
            }

            if self.ssl_ca:
                connection_params["ssl_ca"] = self.ssl_ca

            with mysql.connector.connect(**connection_params) as conn:
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

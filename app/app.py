# app.py

from config.db_connection import DatabaseConnection
from config.settings import HOST, USER, PASSWORD, DATABASE, SERVER_IP
from models.dim_actividades_extractor import DimActividadesExtractor
from models.rol_play_sim_extractor import RolPlaySimExtractor
from utils.logger import logger

from flask import Flask, jsonify, request

app = Flask(__name__)

# Establecer un límite máximo para page_size
MAX_PAGE_SIZE = 50000  # Puedes ajustar este valor según tus necesidades

# Lista de IDs válidos para Bancoppel
BANCOPPEL_IDS = [182, 190, 213, 212, 219, 215, 214, 189, 217, 218, 221, 193, 216]

# --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

# Nuevo endpoint para DimActividadesExtractor
@app.route('/api/dim_actividades', methods=['GET'])
def get_dim_actividades():
    try:
        # Obtener los parámetros de la solicitud
        ids = request.args.getlist('id', type=int)
        fecha_inicio = request.args.get('fecha_inicio', '').strip()
        fecha_fin = request.args.get('fecha_fin', '').strip()
        page = request.args.get('page', default=1, type=int)
        page_size = request.args.get('page_size', default=10000, type=int)

        if not ids:
            return jsonify({"error": "Debes proporcionar al menos un ID."}), 400

        # Asegurar que page_size no exceda el máximo permitido
        if page_size > MAX_PAGE_SIZE:
            page_size = MAX_PAGE_SIZE

        logger.debug(f"Request to /api/dim_actividades received with ids: {ids}, date range: {fecha_inicio} - {fecha_fin}, page: {page}, page_size: {page_size}")

        # Crear una instancia del extractor
        db_conn = DatabaseConnection(HOST, USER, PASSWORD, DATABASE)
        dim_actividades_extractor = DimActividadesExtractor(db_conn)

        # Obtener datos paginados de DimActividadesExtractor
        actividades_data = dim_actividades_extractor.get_data_paginated(
            ids, fecha_inicio=fecha_inicio, fecha_fin=fecha_fin, page=page, page_size=page_size
        )

        # No es necesario cerrar la conexión aquí

        return jsonify(actividades_data), 200

    except Exception as e:
        logger.error(f"Error al obtener las actividades: {e}")
        return jsonify({"error": "Error al obtener las actividades"}), 500

# --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

# Nuevo endpoint para RolPlaySimExtractor
@app.route('/api/rol_play_sim_extractor', methods=['GET'])
def get_rol_play_sim():
    try:
        # Obtener los parámetros de la solicitud
        ids = request.args.getlist('id', type=int)
        fecha_inicio = request.args.get('fecha_inicio', '').strip()
        fecha_fin = request.args.get('fecha_fin', '').strip()
        page = request.args.get('page', default=1, type=int)
        page_size = request.args.get('page_size', default=10000, type=int)

        if not ids:
            return jsonify({"error": "Debes proporcionar al menos un ID."}), 400

        # Asegurar que page_size no exceda el máximo permitido
        if page_size > MAX_PAGE_SIZE:
            page_size = MAX_PAGE_SIZE

        logger.debug(f"Request to /api/rol_play_sim_extractor received with ids: {ids}, date range: {fecha_inicio} - {fecha_fin}, page: {page}, page_size: {page_size}")

        # Crear una instancia del extractor
        db_conn = DatabaseConnection(HOST, USER, PASSWORD, DATABASE)
        rol_play_sim_extractor = RolPlaySimExtractor(db_conn)

        # Obtener datos paginados de RolPlaySimExtractor
        rol_play_sim_data = rol_play_sim_extractor.get_data_paginated(
            ids, fecha_inicio=fecha_inicio, fecha_fin=fecha_fin, page=page, page_size=page_size
        )

        # No es necesario cerrar la conexión aquí

        return jsonify(rol_play_sim_data), 200

    except Exception as e:
        logger.error(f"Error al obtener las actividades: {e}")
        return jsonify({"error": "Error al obtener las actividades"}), 500

if __name__ == '__main__':
    app.run(debug=True, host=SERVER_IP, port=7001)






import json
from utils.functions_la import extract_key_questions_answers
from utils.logger import logger

class BancoppelDashboardModel:
    def __init__(self, db_conn):
        self.db_conn = db_conn

    def get_data_paginated(self, ids, fecha_inicio=None, fecha_fin=None, page=1, page_size=10000):
        """
        Método para obtener una página específica de datos procesados.
        Se ha incrementado el valor predeterminado de page_size a 10000.
        """
        offset = (page - 1) * page_size
        format_strings = ','.join(['%s'] * len(ids))

        # Construir el filtro de fechas si se proporcionan fecha_inicio y fecha_fin
        date_filter = ""
        query_params = list(ids)
        if fecha_inicio and fecha_fin:
            date_filter = "AND saex_DateTime BETWEEN %s AND %s"
            query_params.extend([fecha_inicio, fecha_fin])

        query = f"""
            SELECT 
                saex_id,
                saex_user,
                saex_useCases,
                saex_useCasesTitle,
                saex_username,
                saex_retroContents,
                saex_closingContents,
                saex_DateTime,
                saex_iterations,
                saex_score,
                saex_scoreData,
                saex_sold,
                saex_rp_id,
                saex_rp_email,
                saex_rp_activity,
                saex_rp_client
            FROM 
                sale_exercises
            WHERE 
                saex_useCases IN ({format_strings})
                {date_filter}
            LIMIT %s OFFSET %s
        """

        query_params.extend([page_size, offset])

        resultado = self.db_conn.ejecutar_query(query, tuple(query_params))
        if resultado:
            for fila in resultado:
                self.procesar_fila(fila)
            return resultado
        else:
            return []

    def procesar_fila(self, fila):
        """
        Método para procesar cada fila individual.
        """
        retro_contents = fila.get('saex_retroContents')
        if retro_contents:
            try:
                retro_dict = json.loads(retro_contents)
                for i in range(1, 11):
                    pregunta_key = f'pregunta{i}'
                    respuesta_key = f'respuesta{i}'
                    puntaje_key = f'puntaje{i}'
                    pregunta = retro_dict.get(str(i), {}).get('question', '')
                    fila[pregunta_key] = pregunta
                    respuesta = retro_dict.get(str(i), {}).get('answer', '')
                    fila[respuesta_key] = respuesta
                    puntaje = retro_dict.get(str(i), {}).get('puntos', '0')
                    try:
                        fila[puntaje_key] = float(puntaje)
                    except ValueError:
                        fila[puntaje_key] = 0.0
                if 'puntaje_total' not in fila or not isinstance(fila['puntaje_total'], (int, float)):
                    total_puntaje = sum(fila.get(f'puntaje{i}', 0.0) for i in range(1, 11))
                    fila['puntaje_total'] = total_puntaje
            except json.JSONDecodeError as e:
                logger.error(f"Error al parsear saex_retroContents: {e}")
                for i in range(1, 11):
                    fila[f'pregunta{i}'] = ''
                    fila[f'respuesta{i}'] = ''
                    fila[f'puntaje{i}'] = 0.0
                fila['puntaje_total'] = 0.0
        else:
            for i in range(1, 11):
                fila[f'pregunta{i}'] = ''
                fila[f'respuesta{i}'] = ''
                fila[f'puntaje{i}'] = 0.0
            fila['puntaje_total'] = 0.0

        score_data = fila.get('saex_scoreData')
        if score_data:
            try:
                score_dict = json.loads(score_data)
                fila['saex_scoreData_sum'] = float(score_dict.get('sum', 0))
                fila['saex_scoreData_item'] = int(score_dict.get('item', 0))
                fila['saex_scoreData_avg'] = float(score_dict.get('avg', 0.0))
            except json.JSONDecodeError as e:
                logger.error(f"Error al parsear saex_scoreData: {e}")
                fila['saex_scoreData_sum'] = 0.0
                fila['saex_scoreData_item'] = 0
                fila['saex_scoreData_avg'] = 0.0
        else:
            fila['saex_scoreData_sum'] = 0.0
            fila['saex_scoreData_item'] = 0
            fila['saex_scoreData_avg'] = 0.0

        # Procesar saex_closingContents para extraer preguntas y respuestas clave
        saex_closingContents = fila.get('saex_closingContents')
        if saex_closingContents:
            key_data = extract_key_questions_answers(saex_closingContents)
            fila.update(key_data)
        else:
            fila['veredicto_compra'] = ''
            fila['veredicto_compra_resultado'] = ''
            fila['min_puntos_compra'] = ''
            fila['min_puntos_compra_resultado'] = ''
            fila['puntaje_final_obtenido'] = 0
            fila['max_puntaje'] = 0

        # Remover campos innecesarios
        fila.pop('saex_retroContents', None)
        fila.pop('saex_scoreData', None)
        fila.pop('saex_closingContents', None)





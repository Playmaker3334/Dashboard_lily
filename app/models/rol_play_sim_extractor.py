import re
import json
from datetime import datetime
from utils.logger import logger

class RolPlaySimExtractor:
    def __init__(self, db_conn):
        self.db_conn = db_conn
        self.datos_finales = []

    def get_data_paginated(self, ids, fecha_inicio=None, fecha_fin=None, page=1, page_size=10000):
        """
        Obtiene datos paginados de la tabla sale_exercises filtrados por saex_useCases y opcionalmente por saex_DateTime.
        Luego procesa los resultados y devuelve un JSON.
        """
        self.datos_finales = []

        offset = (page - 1) * page_size
        format_strings = ','.join(['%s'] * len(ids))

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

        try:
            resultado = self.db_conn.ejecutar_query(query, tuple(query_params))
            if resultado:
                self.procesar_resultados(resultado)
                return self.datos_finales
            else:
                logger.info("No se encontraron resultados para los IDs proporcionados.")
                return []
        except Exception as e:
            logger.error(f"Error al obtener datos paginados: {e}")
            return []

    def procesar_resultados(self, resultados):
        """Procesa los resultados proporcionados."""
        for resultado_original in resultados:
            resultado = resultado_original.copy()

            self.convertir_fechas_a_iso(resultado)
            self.extraer_score_data(resultado)
            self.extraer_retro_contents(resultado)
            self.extraer_closing_contents(resultado)

            resultado_final = self.construir_resultado_final(resultado)
            self.datos_finales.append(resultado_final)

    def convertir_fechas_a_iso(self, resultado):
        """Convierte todos los campos datetime en cadenas con formato ISO."""
        for key, value in resultado.items():
            if isinstance(value, datetime):
                resultado[key] = value.isoformat()

    def safe_parse_json(self, json_str, default_value=None):
        """Intenta parsear un JSON, retorna un valor por defecto en caso de error."""
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.error(f"Error al parsear JSON: {e}")
            return default_value or {}

    def extraer_score_data(self, resultado):
        """Extrae y procesa el campo saex_scoreData."""
        score_data_str = resultado.get('saex_scoreData', None)
        if score_data_str:
            score_data = self.safe_parse_json(score_data_str, {})
            resultado['Puntos_Totales'] = score_data.get('sum', "")
            resultado['Calificación'] = score_data.get('avg', "")
        else:
            resultado['Puntos_Totales'] = ""
            resultado['Calificación'] = ""

    def contar_preguntas(self, retro_contents):
        """Cuenta el número de preguntas en el contenido retro de manera más eficiente"""
        if not retro_contents:
            return 0
        numeros = [int(k) for k in retro_contents.keys() if k.isdigit()]
        return max(numeros) if numeros else 0

    def extraer_info_correcta(self, retro_prompt):
        """Extrae si la información fue correcta del retro_prompt"""
        if not retro_prompt:
            return "No aplica"
        
        info_match = re.search(r'<b>¿La información fue correcta\?<\/b>:\s*<span class="uppercase">(.*?)<\/span>', retro_prompt)
        if info_match:
            respuesta = info_match.group(1).strip().lower()
            return respuesta if respuesta in ['si', 'no'] else "No aplica"
        return "No aplica"

    def extraer_puntos(self, retro_prompt):
        """Extrae la puntuación de manera más precisa"""
        if not retro_prompt:
            return "No aplica"
            
        puntos_match = re.search(r'<b>Puntaje<\/b>:\s*(\d+)\s*pts', retro_prompt)
        return puntos_match.group(1).strip() if puntos_match else "No aplica"

    def limpiar_texto_html(self, texto):
        """Limpia el texto de tags HTML y normaliza espacios"""
        # Elimina todos los tags HTML
        texto_limpio = re.sub(r'<[^>]+>', '', texto)
        # Normaliza espacios y elimina espacios múltiples
        texto_limpio = ' '.join(texto_limpio.split())
        # Elimina caracteres especiales y normaliza puntuación
        texto_limpio = texto_limpio.replace('\u00a0', ' ')  # Elimina non-breaking spaces
        return texto_limpio.strip()

    def extraer_retro_contents(self, resultado):
        """Extrae y procesa el campo saex_retroContents."""
        retro_contents_str = resultado.get('saex_retroContents', None)
        retro_contents = self.safe_parse_json(retro_contents_str, {})
        num_preguntas = self.contar_preguntas(retro_contents)

        # Inicializar todos los campos con "No aplica"
        for i in range(1, num_preguntas + 1):
            resultado[f'Pregunta{i}'] = "No aplica"
            resultado[f'Respuesta{i}'] = "No aplica"
            resultado[f'Resp_Modelo{i}'] = "No aplica"
            resultado[f'Info_Correcta{i}'] = "No aplica"
            resultado[f'Puntos{i}'] = "No aplica"

        if retro_contents_str:
            for i in range(1, num_preguntas + 1):
                contenido_pregunta = retro_contents.get(str(i), {})
                
                resultado[f'Pregunta{i}'] = contenido_pregunta.get('question', 'No aplica').strip()
                respuesta = contenido_pregunta.get('answer', 'No aplica').strip()
                resultado[f'Respuesta{i}'] = respuesta if respuesta else "No aplica"

                retro_prompt = contenido_pregunta.get('retroPrompt', '')
                if retro_prompt:
                    retro_prompt = retro_prompt.replace("\r\n", " ").replace("\n", " ").replace("<br>", " ").replace("</br>", " ").strip()

                    modelo_match = re.search(r'<b>Respuesta modelo<\/b>:\s*(.*?)(?=<|$)', retro_prompt)
                    resultado[f'Resp_Modelo{i}'] = modelo_match.group(1).strip() if modelo_match else "No aplica"

                    resultado[f'Info_Correcta{i}'] = self.extraer_info_correcta(retro_prompt)
                    resultado[f'Puntos{i}'] = self.extraer_puntos(retro_prompt)

    def extraer_closing_contents(self, resultado):
        """Extrae y procesa el campo saex_closingContents."""
        closing_contents_str = resultado.get('saex_closingContents', None)
        retro_contents = self.safe_parse_json(resultado.get('saex_retroContents', '{}'), {})
        num_preguntas = self.contar_preguntas(retro_contents)

        for i in range(1, num_preguntas + 1):
            resultado[f'Venta{i}'] = "No aplica"

        if closing_contents_str:
            try:
                closing_contents_str = closing_contents_str.replace("\r\n", " ").replace("\n", " ").strip()
                closing_contents = re.findall(r'<p class="answer">(.*?)<\/p>', closing_contents_str)

                for i, respuesta in enumerate(closing_contents[:num_preguntas]):
                    respuesta_limpia = self.limpiar_texto_html(respuesta)
                    
                    if not respuesta_limpia:
                        continue

                    # Detección mejorada de si/no
                    if respuesta_limpia.lower().strip() in ['si', 'no']:
                        resultado[f'Venta{i + 1}'] = respuesta_limpia.lower()
                        continue

                    # Detección mejorada de puntuación
                    puntos_match = re.search(r'(\d+)\s*/\s*(\d+)\s*pts', respuesta_limpia)
                    if puntos_match:
                        resultado[f'Venta{i + 1}'] = f"{puntos_match.group(1)}/{puntos_match.group(2)} pts"
                        continue

                    # Truncamiento mejorado
                    if len(respuesta_limpia) > 100:
                        palabras = respuesta_limpia[:97].rsplit(' ', 1)[0]
                        resultado[f'Venta{i + 1}'] = f"{palabras}..."
                    else:
                        resultado[f'Venta{i + 1}'] = respuesta_limpia

            except Exception as e:
                logger.error(f"Error al procesar saex_closingContents: {e}")

    def construir_resultado_final(self, resultado):
        """Construye el resultado final en el formato solicitado."""
        resultado_final = {
            'ID_Caso_de_Uso': resultado.get('saex_useCases', 'No aplica'),
            'Cliente': resultado.get('saex_rp_client', 'No aplica'),
            'Usuario': resultado.get('saex_rp_email', 'No aplica'),
            'Usuario Nombre': resultado.get('saex_username', 'No aplica'),
            'Fecha_y_Hora': resultado.get('saex_DateTime', 'No aplica'),
            'Actividad_Nombre': resultado.get('saex_rp_activity', 'No aplica'),
            'ID_Sim': resultado.get('saex_id', 'No aplica'),
            'Puntos_Totales': resultado.get('Puntos_Totales', 'No aplica'),
            'Calificacion': resultado.get('Calificación', 'No aplica'),
            'Caso_de_Uso_Nombre': resultado.get('saex_useCasesTitle', 'No aplica'),
        }

        retro_contents = self.safe_parse_json(resultado.get('saex_retroContents', '{}'), {})
        num_preguntas = self.contar_preguntas(retro_contents)

        for i in range(1, num_preguntas + 1):
            resultado_final[f'Pregunta{i}'] = resultado.get(f'Pregunta{i}', 'No aplica')
            resultado_final[f'Respuesta{i}'] = resultado.get(f'Respuesta{i}', 'No aplica')
            resultado_final[f'Resp_Modelo{i}'] = resultado.get(f'Resp_Modelo{i}', 'No aplica')
            resultado_final[f'Info_Correcta{i}'] = resultado.get(f'Info_Correcta{i}', 'No aplica')
            resultado_final[f'Puntos{i}'] = resultado.get(f'Puntos{i}', 'No aplica')
            resultado_final[f'Venta{i}'] = resultado.get(f'Venta{i}', 'No aplica')

        return resultado_final

import re
import json
from datetime import datetime
from utils.logger import logger

class RolPlaySimExtractor:
    def __init__(self, db_conn):
        self.db_conn = db_conn
        self.datos_finales = []

    def get_data_paginated(self, ids, fecha_inicio=None, fecha_fin=None, page=1, page_size=10000):
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
                saex_id, saex_user, saex_useCases, saex_useCasesTitle,
                saex_username, saex_retroContents, saex_closingContents,
                saex_DateTime, saex_iterations, saex_score, saex_scoreData,
                saex_sold, saex_rp_id, saex_rp_email, saex_rp_activity,
                saex_rp_client
            FROM sale_exercises
            WHERE saex_useCases IN ({format_strings})
            {date_filter}
            LIMIT %s OFFSET %s"""

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
        for resultado_original in resultados:
            resultado = resultado_original.copy()
            self.convertir_fechas_a_iso(resultado)
            self.extraer_score_data(resultado)
            self.extraer_retro_contents(resultado)
            self.extraer_closing_contents(resultado)
            resultado_final = self.construir_resultado_final(resultado)
            self.datos_finales.append(resultado_final)

    def convertir_fechas_a_iso(self, resultado):
        for key, value in resultado.items():
            if isinstance(value, datetime):
                resultado[key] = value.isoformat()

    def safe_parse_json(self, json_str, default_value=None):
        if not json_str:
            return default_value or {}
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.error(f"Error al parsear JSON: {e}")
            return default_value or {}

    def extraer_score_data(self, resultado):
        score_data_str = resultado.get('saex_scoreData', None)
        if score_data_str:
            score_data = self.safe_parse_json(score_data_str, {})
            resultado['Puntos_Totales'] = score_data.get('sum', "")
            resultado['Calificación'] = score_data.get('avg', "")
        else:
            resultado['Puntos_Totales'] = ""
            resultado['Calificación'] = ""

    def contar_preguntas(self, retro_contents):
        if not retro_contents:
            return 0
        numeros = [int(k) for k in retro_contents.keys() if k.isdigit()]
        return max(numeros) if numeros else 0

    def extraer_info_correcta(self, retro_prompt):
        if not retro_prompt:
            return "No aplica"
        
        texto_limpio = self.limpiar_texto_html(retro_prompt).lower()
        
        patrones_si = [
            r'¿has cumplido satisfactoriamente.*?:\s*<span class="uppercase">si</span>',
            r'¿has cumplido satisfactoriamente.*?:\s*<span class="uppercase">sí</span>',
            r'¿la información fue correcta\?.*?:\s*<span class="uppercase">si</span>',
            r'¿la información fue correcta\?.*?:\s*<span class="uppercase">sí</span>',
            r'cumplido satisfactoriamente.*?si[\s\.<]',
            r'información.*?correcta.*?si[\s\.<]',
            r'criterios.*?evaluación.*?si[\s\.<]'
        ]
        
        patrones_no = [
            r'¿has cumplido satisfactoriamente.*?:\s*<span class="uppercase">no</span>',
            r'¿la información fue correcta\?.*?:\s*<span class="uppercase">no</span>',
            r'cumplido satisfactoriamente.*?no[\s\.<]',
            r'información.*?correcta.*?no[\s\.<]',
            r'criterios.*?evaluación.*?no[\s\.<]'
        ]

        for patron in patrones_si:
            if re.search(patron, texto_limpio, re.IGNORECASE | re.DOTALL):
                return "si"
        
        for patron in patrones_no:
            if re.search(patron, texto_limpio, re.IGNORECASE | re.DOTALL):
                return "no"

        return "No aplica"

    def extraer_puntos(self, retro_prompt):
        if not retro_prompt:
            return "No aplica"
        
        patrones_puntos = [
            r'<b>puntaje</b>:\s*(\d+)\s*pts?(?:\s*/\s*\d+)?',
            r'puntaje:\s*(\d+)\s*pts?(?:\s*/\s*\d+)?',
            r'(\d+)\s*pts?(?:\s*/\s*\d+\s*pts?)',
            r'puntuación:\s*(\d+)'
        ]
        
        for patron in patrones_puntos:
            match = re.search(patron, retro_prompt, re.IGNORECASE)
            if match:
                return match.group(1).strip()
                
        return "No aplica"

    def limpiar_texto_html(self, texto):
        if not texto:
            return ""
        texto = texto.lower()
        texto = texto.replace('\r\n', ' ').replace('\n', ' ').replace('<br>', ' ').replace('</br>', ' ')
        texto = re.sub(r'<[^>]+>', ' ', texto)
        texto = ' '.join(texto.split())
        texto = texto.replace('\u00a0', ' ').replace('&nbsp;', ' ')
        texto = texto.replace('sí', 'si')
        return texto.strip()

    def extraer_retro_contents(self, resultado):
        retro_contents_str = resultado.get('saex_retroContents', None)
        retro_contents = self.safe_parse_json(retro_contents_str, {})
        num_preguntas = self.contar_preguntas(retro_contents)

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
                    modelo_match = re.search(r'<b>respuesta modelo</b>:\s*(.*?)(?=<b>|$)', retro_prompt, re.IGNORECASE)
                    resultado[f'Resp_Modelo{i}'] = modelo_match.group(1).strip() if modelo_match else "No aplica"
                    resultado[f'Info_Correcta{i}'] = self.extraer_info_correcta(retro_prompt)
                    resultado[f'Puntos{i}'] = contenido_pregunta.get('puntos', 'No aplica')

    def extraer_closing_contents(self, resultado):
        closing_contents_str = resultado.get('saex_closingContents', None)
        retro_contents = self.safe_parse_json(resultado.get('saex_retroContents', '{}'), {})
        num_preguntas = self.contar_preguntas(retro_contents)

        for i in range(1, num_preguntas + 1):
            resultado[f'Venta{i}'] = "No aplica"

        if closing_contents_str:
            try:
                closing_contents_str = closing_contents_str.replace("\r\n", " ").replace("\n", " ").strip()
                closing_contents = re.findall(r'<p class="answer">(.*?)</p>', closing_contents_str)

                for i, respuesta in enumerate(closing_contents[:num_preguntas]):
                    respuesta_limpia = self.limpiar_texto_html(respuesta)
                    
                    if not respuesta_limpia:
                        continue

                    if respuesta_limpia.lower().strip() in ['si', 'no']:
                        resultado[f'Venta{i + 1}'] = respuesta_limpia.lower()
                        continue

                    puntos_match = re.search(r'(\d+)\s*/\s*(\d+)\s*pts', respuesta_limpia)
                    if puntos_match:
                        resultado[f'Venta{i + 1}'] = f"{puntos_match.group(1)}/{puntos_match.group(2)} pts"
                        continue

                    if len(respuesta_limpia) > 100:
                        palabras = respuesta_limpia[:97].rsplit(' ', 1)[0]
                        resultado[f'Venta{i + 1}'] = f"{palabras}..."
                    else:
                        resultado[f'Venta{i + 1}'] = respuesta_limpia

            except Exception as e:
                logger.error(f"Error al procesar saex_closingContents: {e}")

    def construir_resultado_final(self, resultado):
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

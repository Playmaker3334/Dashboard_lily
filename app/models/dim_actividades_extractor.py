import re
import json
from datetime import datetime
from utils.logger import logger
from bs4 import BeautifulSoup

class DimActividadesExtractor:
    def __init__(self, db_conn):
        self.db_conn = db_conn
        self.datos_finales = []

    def get_data_paginated(self, ids, fecha_inicio=None, fecha_fin=None, page=1, page_size=10000):
        """
        Obtiene datos paginados de la tabla sale_exercises filtrados por saex_useCases y opcionalmente por saex_DateTime.
        Luego procesa los resultados y almacena en self.datos_finales.
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
            logger.debug(f"Ejecutando la consulta: {query} con parámetros: {tuple(query_params)}")
            resultado = self.db_conn.ejecutar_query(query, tuple(query_params))
            if resultado:
                self.procesar_resultados(resultado)
                # Filtrar actividades válidas
                datos_filtrados = [
                    d for d in self.datos_finales
                    if d.get("Actividad_Nombre") and d.get("Actividad_Nombre") != "No aplica"
                ]
                # Eliminar duplicados
                datos_sin_duplicados = self.eliminar_duplicados_json(datos_filtrados)
                return datos_sin_duplicados
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
            actividades = self.extraer_dim_actividades(resultado)
            resultado_final = self.construir_resultado_final(actividades)
            self.datos_finales.append(resultado_final)

    def convertir_fechas_a_iso(self, resultado):
        for key, value in resultado.items():
            if isinstance(value, datetime):
                resultado[key] = value.isoformat()

    def limpiar_valor(self, valor):
        if isinstance(valor, str):
            return re.sub(r'\s+', ' ', valor).strip()
        return valor

    def eliminar_duplicados_json(self, datos):
        actividades_vistas = {}
        for actividad in datos:
            clave_unica = tuple((k, self.limpiar_valor(v)) for k, v in actividad.items() if k != "Actividad_Nombre")
            if clave_unica in actividades_vistas:
                if actividad.get("Actividad_Nombre"):
                    actividades_vistas[clave_unica] = actividad
            else:
                actividades_vistas[clave_unica] = actividad
        return list(actividades_vistas.values())

    def extraer_dim_actividades(self, resultado):
        actividades = {
            'ID_Caso_de_Uso': resultado.get('saex_useCases', 'No aplica'),
            'Caso_de_Uso': resultado.get('saex_useCasesTitle', 'No aplica'),
            'Actividad_Nombre': resultado.get('saex_rp_activity', 'No aplica')
        }

        retro_contents_str = resultado.get('saex_retroContents', None)

        if retro_contents_str:
            try:
                retro_contents = json.loads(retro_contents_str)

                for key, value in retro_contents.items():
                    retro_prompt = value.get('retroPrompt', '')
                    retro_prompt = retro_prompt.replace("\r\n", " ").replace("\n", " ").replace("<br>", " ").replace("</br>", " ").strip()

                    criterio_match = re.search(r'<b>Criterio a evaluar</b>:\s*(.*?)(?=<p>|</p>|\r|\n)', retro_prompt, re.DOTALL)
                    if criterio_match:
                        actividades[f'Criterio_{key}'] = criterio_match.group(1).strip()

                    puntos_max_match = re.search(r'<b>Puntaje</b>:\s*\d+\s*pts\s*/\s*(\d+)\s*pts', retro_prompt)
                    if puntos_max_match:
                        actividades[f'Puntos_Max_{key}'] = puntos_max_match.group(1).strip()

            except json.JSONDecodeError as e:
                logger.error(f"Error al parsear saex_retroContents: {e}")

        closing_contents_str = resultado.get('saex_closingContents', None)

        if closing_contents_str:
            try:
                soup = BeautifulSoup(closing_contents_str, 'html.parser')
                questions = soup.find_all('p', class_='question')

                for i, question in enumerate(questions):
                    pregunta = question.get_text(strip=True)
                    actividades[f'Veredicto_Venta{i + 1}'] = pregunta

            except Exception as e:
                logger.error(f"Error al procesar saex_closingContents: {e}")

        return actividades

    def construir_resultado_final(self, actividades):
        resultado_final = {
            'ID_Caso_de_Uso': actividades.get('ID_Caso_de_Uso', 'No aplica'),
            'Caso_de_Uso': actividades.get('Caso_de_Uso', 'No aplica'),
            'Actividad_Nombre': actividades.get('Actividad_Nombre', 'No aplica'),
        }

        for key in actividades.keys():
            if key.startswith('Criterio_') or key.startswith('Puntos_Max_') or key.startswith('Veredicto_Venta'):
                resultado_final[key] = actividades.get(key, 'No aplica')

        return resultado_final

    def extraer_DimActividades(self):
        datos_finales_sin_duplicados = self.eliminar_duplicados_json(self.datos_finales)
        return datos_finales_sin_duplicados




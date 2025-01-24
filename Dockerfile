# Usa una imagen de Python ligera
FROM python:3.9-slim

# Establece el directorio de trabajo dentro del contenedor
WORKDIR /app

# Copia el archivo de dependencias al contenedor
COPY requirements.txt .

# Instala las dependencias necesarias
RUN pip install --no-cache-dir -r requirements.txt

# Copiar la carpeta 'app' al contenedor
COPY app/ /app

# Exponer el puerto que usará Flask
EXPOSE 7007 

# Comando para ejecutar la aplicación con Gunicorn en el puerto 7001
CMD ["gunicorn", "-w", "5", "-b", "0.0.0.0:7007", "--timeout", "300", "app:app"]





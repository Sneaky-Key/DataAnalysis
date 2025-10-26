# Dockerfile para GateGroupHackathon - DataAnalysis
FROM python:3.11-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Dependencias del sistema necesarias (ligeras)
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential curl git \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements y aprovechar cache de Docker
COPY requirements.txt ./

RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código de la aplicación
COPY . .

# Puerto Streamlit por defecto
EXPOSE 8501

CMD ["streamlit", "run", "Analysis/dashboard.py", "--server.port", "8501", "--server.address", "0.0.0.0"]

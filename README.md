## GateGroupHackathon — DataAnalysis

¡Bienvenido al repositorio DataAnalysis del Hackathon GateGroup! Este proyecto contiene scripts y datos de apoyo para simular, entrenar y desplegar modelos de consumo de catering en vuelos, además de utilidades para administrar inventario por lotes (FEFO).

Este README es intencionalmente exhaustivo: encontrarás la visión general, estructura de archivos, cómo instalar dependencias en Windows PowerShell, instrucciones paso a paso para ejecutar cada componente (generador de datos, entrenamiento y dashboard), notas de seguridad y sugerencias de mejora.

---

## Resumen (tl;dr)

- Generar datos de ejemplo: `DataBase/generate_data.py` — produce inserts SQL de vuelos y servicios.
- Esquema y datos de muestra: `DataBase/DB_Builder.sql`, `DataBase/DB_Data.sql`.
- Entrenar modelos por producto: `Analysis/train.py` — crea `modelos_comida.joblib` y `lista_de_features.joblib`.
- Panel interactivo: `Analysis/dashboard.py` — un Streamlit app para ver inventario, recomendaciones y predicciones.

Recomendación rápida:

1. Crear un entorno virtual Python.
2. Instalar dependencias (ver sección “Dependencias / Requisitos”).
3. Ejecutar `python DataBase/generate_data.py` si necesitas más datos de ejemplo.
4. Conectar o importar `DB_Data.sql` y `DB_Builder.sql` en tu base de datos MySQL para poblar tablas.
5. Entrenar modelos con `python Analysis/train.py`.
6. Ejecutar la interfaz: `streamlit run Analysis/dashboard.py`.

---

## Objetivo del proyecto

Este repositorio simula una solución de soporte de decisiones para la operación de catering a bordo. Permite:

- Simular vuelos y registros de carga/consumo por lote (incluyendo causalidad: temporada, clima, hora del día).  
- Mantener trazabilidad por lote (FEFO) y calcular métricas de riesgo por caducidad.  
- Entrenar modelos por producto que predicen consumo en función de características del vuelo y contexto.  
- Ofrecer un dashboard interactivo para auditar lotes, generar recomendaciones y planificar carga de vuelo.

Uso ideal: operaciones de logística de catering, análisis de desperdicio y optimización de stock por caducidad.

---

## Estructura del repositorio

Raíz del proyecto (relevante):

- `lista_de_features.joblib` — (generado) lista de features guardada por `train.py`.
- `modelos_comida.joblib` — (generado) diccionario de modelos por producto.
- `Analysis/`  
  - `dashboard.py` — aplicación Streamlit para inventario, recomendaciones, predicción y manifiesto.  
  - `train.py` — script para entrenar modelos por producto a partir de la vista logística.  
- `DataBase/`  
  - `DB_Builder.sql` — DDL: tablas y vista `VISTA_LOGISTICA_VUELO`.  
  - `DB_Data.sql` — Inserts de ejemplo para productos, lotes, vuelos y servicios.  
  - `generate_data.py` — script que genera inserts SQL sintéticos con causalidad.  

---

## Dependencias / Requisitos

Recomendado: Python 3.10+ en Windows. Se sugiere crear un virtualenv. Dependencias principales:

- pandas
- faker
- sqlalchemy
- pymysql
- scikit-learn
- joblib
- streamlit
- matplotlib (opcional para gráficas en el dashboard)

Sugerencia de `requirements.txt` (no obligatorio si ya tienes paquetes globales):

```
pandas
faker
SQLAlchemy
PyMySQL
scikit-learn
joblib
streamlit
matplotlib
seaborn
```

Instalación rápida en PowerShell (ejecutar desde la carpeta del repo):

```powershell
python -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt  # si creas el archivo con la lista anterior
# o instalar manualmente:
pip install pandas faker SQLAlchemy PyMySQL scikit-learn joblib streamlit matplotlib seaborn
```

---

## Guía paso a paso

1) Generar datos de ejemplo (opcional — `generate_data.py`)

- Propósito: producir el archivo `inserts_vuelos.sql` con inserts para tablas `VUELO` y `SERVICIO_LOTE_VUELO`.
- Uso:

```powershell
python DataBase\generate_data.py
```

- Resultado: se crea `inserts_vuelos.sql` en el mismo directorio `DataBase`. Puedes importar su contenido a tu DB MySQL.

Notas: el script usa `Faker` y una lógica causal para Temporada, clima, ocupación y consumo. Puedes editar `NUM_VUELOS` en la parte superior del script.

2) Construir la base de datos y poblarla

- Importa `DB_Builder.sql` para crear tablas y la vista `VISTA_LOGISTICA_VUELO`.
- Importa `DB_Data.sql` para datos de muestra inicial. Luego aplica `inserts_vuelos.sql` si quieres más registros sintéticos.

3) Entrenamiento de modelos (`Analysis/train.py`)

- Propósito: leer la vista `VISTA_LOGISTICA_VUELO` (a través de `SERVICIO_LOTE_VUELO` y otras tablas), preprocesar con `pd.get_dummies` y entrenar un `LinearRegression` por producto.
- Salidas: `modelos_comida.joblib` (diccionario producto -> modelo) y `lista_de_features.joblib` (lista de columnas que se usaron como features).

Uso (asegúrate de tener la DB accesible y las credenciales correctas en el script):

```powershell
python Analysis\train.py
```

Notas importantes:
- `train.py` crea y guarda los artefactos en la carpeta `Analysis` utilizando rutas relativas (Path(__file__).resolve().parent).
- Si hay pocos registros para un producto (menos de 10), el script omite ese producto. Ajusta el umbral si quieres.

4) Ejecutar el dashboard interactivo (`Analysis/dashboard.py`)

- Propósito: Streamlit app para inspeccionar inventario, ver recomendaciones y simular predicciones/manifestos por vuelo.

Arrancar la app:

```powershell
streamlit run Analysis\dashboard.py
```

- Notas: el script contiene funciones para conectarse a la DB usando SQLAlchemy y carga los artifacts `.joblib`. Por sencillez el código hoy incluye la URL y credenciales embebidas; se recomienda moverlas a variables de entorno (ver sección Seguridad).

---

## Ejemplos de uso y outputs esperados

- `generate_data.py` -> `inserts_vuelos.sql` con bloques `INSERT INTO VUELO (...) VALUES ...;` y `INSERT INTO SERVICIO_LOTE_VUELO (...) VALUES ...;`.
- `train.py` -> al finalizar verás en consola resumen de modelos entrenados y R2 por producto; archivos `.joblib` guardados en `Analysis/`.
- `dashboard.py` -> UI con pestañas: Panel Principal, Recomendaciones, Predicción de Consumo, Manifesto de Carga y Auditoría de Lotes.

---

## Seguridad y buenas prácticas

- No dejes credenciales en el código fuente. En los scripts actuales la conexión a la base de datos está codificada. Recomiendo migrarlas a variables de entorno o a un archivo `.env` (no versionado).

Ejemplo PowerShell para exportar variables antes de ejecutar:

```powershell
$env:DB_URL = "mysql+pymysql://user:pass@host:port/dbname"
# luego en Python puedes leerlo con os.environ['DB_URL'] o usar python-dotenv
```

- Valida que los puertos/SSL del servicio de base de datos estén configurados correctamente (algunos scripts usan connect_args para SSL).

---

## Desarrollo y mejoras sugeridas

1. Añadir `requirements.txt` y/o `environment.yml` para reproducibilidad.
2. Refactor: extraer conexión a DB y credenciales a un módulo `config.py` y leer variables de entorno.
3. Tests unitarios mínimos: 
   - Generador de datos: confirmar que los DataFrames generados respetan tipos y valores.  
   - Entrenamiento: test que verifica que `joblib` persiste los archivos y que `lista_de_features` contiene las columnas esperadas.  
4. Mejorar modelos: usar modelos regulares (Ridge/Lasso) y validación cruzada.  
5. CI: añadir GitHub Actions para linting y pruebas unitarias.

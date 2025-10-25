

# --- 1. Conexión y Carga de Datos ---

import pandas as pd
from sqlalchemy import create_engine
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import r2_score
import numpy as np

# --- 1. Conexión y Carga de Datos ---

# 1. Definimos la URL base. 
#    - El driver es 'mysql+pymysql'
#    - ¡SIN el '?ssl-mode=...' al final!
db_url_base = "mysql+pymysql://avnadmin:AVNS_m-BChJcXobgh-J9hPdB@hackmty-tec-4e3a.f.aivencloud.com:13731/gategroup_flights?"

# 2. ¡ESTA ES LA SINTAXIS CORRECTA!
#    PyMySQL espera un diccionario 'ssl'
#    y DENTRO de él, la clave 'ssl_mode'.
ssl_args = {
    'ssl': {
        'ssl_mode': 'REQUIRED'
    }
}

try:
    # 3. Creamos el engine con la URL base y los 'connect_args'
    engine = create_engine(db_url_base, connect_args=ssl_args)
    
    # (Opcional) Probar la conexión para ver si funciona
    with engine.connect() as conn:
         print("¡Conexión al motor exitosa!")

except Exception as e:
    print(f"Error creating engine: {e}")
    exit()

# --- El resto de tu código (consulta SQL, etc.) sigue aquí ---
# ... (tu código de 'TU_TABLA_UNICA', 'sql_query', etc. va aquí) ...


# Asigna el nombre real de tu única tabla aquí
TU_TABLA_UNICA = "VISTA_LOGISTICA_VUELO" 

# La consulta ahora es un SELECT simple
sql_query = f"""
SELECT
    -- Features del Vuelo
    V.Num_Pasajeros,
    AL.Nombre AS Nombre_Aerolinea,
    V.Distancia_KM,
    V.Tipo_Trayecto,
    TA.Capacidad_Max AS Capacidad_Max_Avion,

    -- Features del Tiempo
    V.Hora_Dia,
    V.Dia_Semana,
    V.Temporada,
    V.Condicion_Climatica,
    
    -- Features de la Ruta
    A_Salida.Localidad AS Localidad_Salida,
    A_Llegada.Localidad AS Localidad_Llegada,

    -- Features del Producto
    CP.Nombre AS Nombre_Categoria,
    P.Tipo_Especial,
    
    -- La "llave" para filtrar en Python
    P.Nombre AS Nombre_Producto,
    
    -- Tu "target" (la 'y')
    -- NOTA: He cambiado tu cálculo de 'Consumo_Real'
    S.Cantidad_Consumida AS Consumo_Real

FROM 
    SERVICIO_LOTE_VUELO AS S
JOIN 
    VUELO AS V ON S.Vuelo_ID = V.Vuelo_ID
JOIN 
    LOTE_PRODUCTO AS L ON S.Lote_ID = L.Lote_ID
JOIN 
    PRODUCTO AS P ON L.Producto_ID = P.Producto_ID
JOIN 
    CATEGORIA_PRODUCTO AS CP ON P.Categoria_ID = CP.Categoria_ID
JOIN 
    AEROLINEA AS AL ON V.Aerolinea_ID = AL.Aerolinea_ID
JOIN 
    TIPO_AVION AS TA ON V.Tipo_Avion_ID = TA.Tipo_Avion_ID
JOIN 
    AEROPUERTO AS A_Salida ON V.Aeropuerto_Salida_ID = A_Salida.Aeropuerto_ID
JOIN 
    AEROPUERTO AS A_Llegada ON V.Aeropuerto_Llegada_ID = A_Llegada.Aeropuerto_ID
WHERE
    -- Solo entrenamos con datos donde el consumo fue registrado
    S.Cantidad_Consumida IS NOT NULL 
    AND S.Cantidad_Consumida > 0;
"""

print("Cargando datos de la tabla maestra...")
try:
    # Cargamos la tabla completa en 'df'
    df = pd.read_sql(sql_query, engine)
    
    if df.empty:
        print("No se encontraron datos!")
        exit() # Salimos si no hay datos
    else:
        print(f"Datos cargados exitosamente! {len(df)} registros encontrados.")
        print(df.head())

except Exception as e:
    print(f"Error al ejecutar la consulta: {e}")
    exit() # Salimos si la consulta falla
finally:
    engine.dispose()

# --- 2. Pre-procesamiento de Datos (¡El paso clave!) ---

# ¡LA LISTA DE COLUMNAS CATEGÓRICAS DEBE ACTUALIZARSE!
columnas_categoricas = [
    'Nombre_Aerolinea',
    'Tipo_Trayecto',
    'Hora_Dia',
    'Dia_Semana',
    'Temporada',
    'Condicion_Climatica',
    'Localidad_Salida',
    'Localidad_Llegada',
    'Nombre_Categoria',
    'Tipo_Especial'
]

print("\nProcesando datos categóricos (strings a números)...")
# Convertimos todas las columnas de texto en columnas de 0s y 1s
df_processed = pd.get_dummies(df, columns=columnas_categoricas)

print("Datos procesados:")
print(df_processed.head())


# --- 3. Construir un Modelo por Cada Producto ---

trained_models = {}
lista_de_productos = df_processed['Nombre_Producto'].unique()
print(f"\nSe construirán modelos para {len(lista_de_productos)} productos...")

columnas_target = 'Consumo_Real'
columnas_llave = 'Nombre_Producto'

# Obtenemos la lista de features DESPUÉS de pd.get_dummies
all_feature_columns = [
    col for col in df_processed.columns if col not in [columnas_target, columnas_llave]
]

# Guardamos esta lista para usarla en la predicción
model_feature_list = all_feature_columns
print(f"Features a usar: {model_feature_list}")

# Loop para entrenar cada modelo
for producto in lista_de_productos:
    
    df_producto = df_processed[df_processed['Nombre_Producto'] == producto]
    
    if len(df_producto) < 50:
        print(f"Saltando '{producto}': datos insuficientes ({len(df_producto)} registros)")
        continue

    print(f"\n--- Entrenando Modelo para: {producto} ---")
    
    X = df_producto[all_feature_columns]
    y = df_producto[columnas_target]
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    model = LinearRegression()
    model.fit(X_train, y_train)
    
    predictions = model.predict(X_test)
    accuracy = r2_score(y_test, predictions)
    print(f"Modelo para '{producto}' entrenado. Precisión (R2): {accuracy:.4f}")
    
    trained_models[producto] = model

print("\n--- ¡Entrenamiento completado! ---")


import joblib

# ... (todo tu código de entrenamiento)...
# ... (justo después de entrenar todos los modelos) ...

print("\n--- Guardando modelos entrenados en archivos... ---")

# Guardamos el diccionario de modelos
joblib.dump(trained_models, 'modelos_comida.joblib')

# ¡MUY IMPORTANTE! También guardamos la lista de columnas
# Necesitamos esto para procesar los datos nuevos exactamente igual
joblib.dump(model_feature_list, 'lista_de_features.joblib')

print("Modelos y lista de features guardados exitosamente.")


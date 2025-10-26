import random
import datetime
from faker import Faker
import pandas as pd

# Inicialización
fake = Faker()
NUM_VUELOS = 50
OUTPUT_FILE = "inserts_vuelos.sql"

# --- Datos Fijos de tus Tablas (IDs de Data.sql) ---
AEROLINEAS = list(range(301, 316)) # 301 a 315
AVIONES = list(range(101, 106))   # 101 a 105
AEROPUERTOS = list(range(201, 209)) # 201 a 208
LOTES = list(range(601, 6013))    # 601 a 6012 (Lotes activos)
PRODUCTOS = list(range(501, 513)) # 501 a 512

# Mapeo simple de Capacidad de Aviones (para calcular pasajeros)
CAPACIDADES = {101: 380, 102: 320, 103: 290, 104: 180, 105: 170} 

# Mapeo de Productos a Categorías (para la lógica de carga)
# Este mapeo parece incorrecto (usa IDs 4xx), lo reemplazaremos con uno nuevo.
PRODUCTO_CATEGORIA_NUEVO = {
    'Desayuno': [501, 502],
    'Almuerzo/Cena': [503, 504, 505, 506, 507, 508],
    'Bebidas': [509, 510],
    'Snacks': [511, 512]
}

# Mapeo de ID de producto a categoría para la lógica de consumo
PRODUCTO_ID_A_CATEGORIA = {
    501: 'Salchicha de Pavo con Huevo Revuelto y Patata', 502: 'Ratatouille con Tostadas',
    503: 'Pollo con Ensalada de Patata y Espárragos', 504: 'Sándwich de pavo y queso',
    505: 'Ragú de Ternera con Puré', 506: 'Lomo de Salmón con Salsa de Eneldo',
    507: 'Coeur Lion Camembert', 508: 'Blue Castello',
    509: 'Agua Mineral (500ml)', 510: 'Refresco Cola (Lata)',
    511: 'Pan dulce de Nuez', 512: 'Papitas Sabor Original (Bolsa Individual)'
}

PRODUCTO_A_LOTES = {
    501: [603], 502: [608], 503: [604], 504: [609],
    505: [607], 506: [605], 507: [610], 508: [611],
    509: [601], 510: [602], 511: [612], 512: [606]
}

# -----------------------------------------------------
# LÓGICA DE CAUSALIDAD
# -----------------------------------------------------

def generar_datos_vuelo(vuelo_id_start=1401):
    """Genera 300 filas de datos de vuelo con causalidad."""
    vuelos = []
    
    for i in range(NUM_VUELOS):
        Vuelo_ID = vuelo_id_start + i
        
        # Generar Fecha y Tiempo
        fecha_salida = fake.date_between(start_date='-2y', end_date='today')
        hora_salida = datetime.time(random.randint(0, 23), random.choice([0, 15, 30, 45]))
        hora_dia = 'Mañana' if hora_salida.hour < 11 else ('Tarde' if hora_salida.hour < 18 else 'Noche')
        
        # Dias de la semana en español
        dias_semana_es = {
            'Monday': 'Lunes', 'Tuesday': 'Martes', 'Wednesday': 'Miércoles',
            'Thursday': 'Jueves', 'Friday': 'Viernes', 'Saturday': 'Sábado', 'Sunday': 'Domingo'
        }
        dia_semana = dias_semana_es[fecha_salida.strftime('%A')]
        
        # Causalidad 1: Temporada basada en el mes
        mes = fecha_salida.month
        if mes in [12, 1, 6, 7, 8]:
            Temporada = 'Alta'
        elif mes in [2, 3, 10, 11]:
            Temporada = 'Media'
        else:
            Temporada = 'Baja'
            
        # Elegir Aerolínea y Avión
        Aerolinea_ID = random.choice(AEROLINEAS)
        Tipo_Avion_ID = random.choice(AVIONES)
        capacidad_max = CAPACIDADES.get(Tipo_Avion_ID, 200) # Capacidad por defecto
        
        # Causalidad 2: Pasajeros basados en la Temporada
        if Temporada == 'Alta':
            ocupacion_min, ocupacion_max = 0.80, 0.98
        elif Temporada == 'Media':
            ocupacion_min, ocupacion_max = 0.70, 0.90
        else:
            ocupacion_min, ocupacion_max = 0.55, 0.80
        
        Num_Pasajeros = int(capacidad_max * random.uniform(ocupacion_min, ocupacion_max))

        # Otros campos
        Distancia_KM = random.randint(500, 15000)
        Tipo_Trayecto = 'Internacional' if Distancia_KM > 1500 else 'Nacional'
        Condicion_Climatica = random.choice(['Soleado', 'Lluvioso', 'Nublado', 'Tormenta', 'Nevado'])
        
        # Simular hora de llegada
        duracion_min = int(Distancia_KM / 800 * 60) + random.randint(30, 90) # Duración en minutos
        dt_salida = datetime.datetime.combine(fecha_salida, hora_salida)
        dt_llegada = dt_salida + datetime.timedelta(minutes=duracion_min)
        
        vuelos.append({
            'Vuelo_ID': Vuelo_ID, 'Aerolinea_ID': Aerolinea_ID, 'Tipo_Avion_ID': Tipo_Avion_ID, 
            'Aeropuerto_Salida_ID': random.choice(AEROPUERTOS), 'Aeropuerto_Llegada_ID': random.choice(AEROPUERTOS),
            'Fecha_Salida': fecha_salida, 'Hora_Salida_Programada': hora_salida,
            'Fecha_Llegada': dt_llegada.date(), 'Hora_Llegada_Programada': dt_llegada.time(),
            'Tipo_Trayecto': Tipo_Trayecto, 'Distancia_KM': Distancia_KM, 'Num_Pasajeros': Num_Pasajeros,
            'Hora_Dia': hora_dia, 'Dia_Semana': dia_semana, 'Temporada': Temporada, 
            'Condicion_Climatica': Condicion_Climatica
        })
        
    return pd.DataFrame(vuelos)

def generar_datos_servicio(df_vuelos):
    """Genera las sentencias de carga y consumo basadas en la lógica de vuelo."""
    servicios = []
    
    for _, vuelo in df_vuelos.iterrows():
        Vuelo_ID = vuelo['Vuelo_ID']
        Num_Pasajeros = vuelo['Num_Pasajeros']
        Hora_Dia = vuelo['Hora_Dia']
        Clima = vuelo['Condicion_Climatica']
        
        lotes_usados_en_vuelo = set()
        productos_a_cargar = []
        
        # Lógica de menú más dinámica
        # 1. Añadir bebidas base
        productos_a_cargar.extend(PRODUCTO_CATEGORIA_NUEVO['Bebidas'])
        
        # 2. Añadir plato principal según la hora
        if Hora_Dia == 'Mañana':
            productos_a_cargar.append(random.choice(PRODUCTO_CATEGORIA_NUEVO['Desayuno']))
        else: # Tarde o Noche
            num_platos = random.randint(1, 2)
            platos_seleccionados = random.sample(PRODUCTO_CATEGORIA_NUEVO['Almuerzo/Cena'], num_platos)
            productos_a_cargar.extend(platos_seleccionados)

        # 3. Añadir un snack aleatorio con 70% de probabilidad
        if random.random() < 0.7:
            productos_a_cargar.append(random.choice(PRODUCTO_CATEGORIA_NUEVO['Snacks']))

        productos_a_cargar = list(set(productos_a_cargar)) # Eliminar duplicados
        
        for Producto_ID in productos_a_cargar:
            lotes_validos_para_producto = PRODUCTO_A_LOTES.get(Producto_ID, [])
            lotes_disponibles_para_producto = [lote for lote in lotes_validos_para_producto if lote not in lotes_usados_en_vuelo]

            if not lotes_disponibles_para_producto:
                continue 

            lote_elegido = random.choice(lotes_disponibles_para_producto)
            lotes_usados_en_vuelo.add(lote_elegido)

            # 4. Lógica de Tasa de Consumo y Causalidad por Clima
            base_rate = random.uniform(0.75, 0.85)
            
            categoria = PRODUCTO_ID_A_CATEGORIA.get(Producto_ID, '')
            if Clima in ['Soleado', 'Tormenta'] and Producto_ID in [509, 510]:
                base_rate += 0.08
            elif Clima == 'Nevado' and Producto_ID in [501, 502, 505, 506]:
                base_rate += 0.05

            tasa_consumo_final = min(max(base_rate, 0.5), 0.98)
            
            factor_carga = 1.2 if categoria == 'Bebidas (No Alcohólicas)' else 1.05
            Cantidad_Cargada = int(Num_Pasajeros * factor_carga)
            Cantidad_Consumida = int(Cantidad_Cargada * tasa_consumo_final)
            
            servicios.append({
                'Vuelo_ID': Vuelo_ID,
                'Lote_ID': lote_elegido,
                'Cantidad_Cargada': Cantidad_Cargada,
                'Cantidad_Consumida': Cantidad_Consumida
            })
            
    return pd.DataFrame(servicios)


def generar_sql(df_vuelos, df_servicios):
    """Escribe los DataFrames a un archivo SQL con sentencias INSERT."""
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write("-- INSERTS GENERADOS POR SCRIPT DE PYTHON CON LÓGICA DE CAUSALIDAD\n")
        f.write(f"-- Total de {len(df_vuelos)} vuelos generados.\n\n")

        # 1. Sentencias de Vuelo
        f.write("--- INSERTS PARA LA TABLA VUELO ---\n")
        for _, row in df_vuelos.iterrows():
            f.write(f"INSERT INTO VUELO (Vuelo_ID, Aerolinea_ID, Tipo_Avion_ID, Aeropuerto_Salida_ID, Aeropuerto_Llegada_ID, Fecha_Salida, Hora_Salida_Programada, Fecha_Llegada, Hora_Llegada_Programada, Tipo_Trayecto, Distancia_KM, Num_Pasajeros, Hora_Dia, Dia_Semana, Temporada, Condicion_Climatica) VALUES (\n")
            f.write(f"  {row['Vuelo_ID']}, {row['Aerolinea_ID']}, {row['Tipo_Avion_ID']}, {row['Aeropuerto_Salida_ID']}, {row['Aeropuerto_Llegada_ID']},\n")
            f.write(f"  '{row['Fecha_Salida']}', '{row['Hora_Salida_Programada']}', '{row['Fecha_Llegada']}', '{row['Hora_Llegada_Programada']}',\n")
            f.write(f"  '{row['Tipo_Trayecto']}', {row['Distancia_KM']}, {row['Num_Pasajeros']}, '{row['Hora_Dia']}', '{row['Dia_Semana']}',\n")
            f.write(f"  '{row['Temporada']}', '{row['Condicion_Climatica']}'\n);\n")
            
        # 2. Sentencias de Servicio_Lote_Vuelo
        f.write("\n--- INSERTS PARA LA TABLA SERVICIO_LOTE_VUELO ---\n")
        for _, row in df_servicios.iterrows():
            f.write(f"INSERT INTO SERVICIO_LOTE_VUELO (Vuelo_ID, Lote_ID, Cantidad_Cargada, Cantidad_Consumida) VALUES (\n")
            f.write(f"  {row['Vuelo_ID']}, {row['Lote_ID']}, {row['Cantidad_Cargada']}, {row['Cantidad_Consumida']}\n);\n")


# --- EJECUCIÓN ---
if __name__ == '__main__':
    # 1. Generar DataFrames
    df_vuelos = generar_datos_vuelo()
    df_servicios = generar_datos_servicio(df_vuelos)
    
    # 2. Generar Archivo SQL
    generar_sql(df_vuelos, df_servicios)
    print(f"✅ ¡Generación completada! Archivo '{OUTPUT_FILE}' creado con {len(df_vuelos)} vuelos con causalidad.")
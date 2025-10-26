import streamlit as st
import pandas as pd
import numpy as np
import joblib
from sqlalchemy import create_engine, text
import datetime
from pathlib import Path

# --- 1. CONFIGURACIÓN INICIAL ---
st.set_page_config(
    page_title="Gategroup Predicción",
    page_icon="✈️",
    layout="wide"
)

# --- 2. CACHING DE RECURSOS ---
BASE_DIR = Path(__file__).resolve().parent
MODEL_FILE = BASE_DIR / "modelos_comida.joblib"
FEATURES_FILE = BASE_DIR / "lista_de_features.joblib"

@st.cache_resource
def get_db_engine():
    """Crea y devuelve un motor de conexión SQLAlchemy."""
    try:
        db_url_base = "mysql+pymysql://avnadmin:AVNS_m-BChJcXobgh-J9hPdB@hackmty-tec-4e3a.f.aivencloud.com:13731/gategroup_flights?"
        ssl_args = {'ssl': {'ssl_mode': 'REQUIRED'}}
        engine = create_engine(db_url_base, connect_args=ssl_args)
        print("¡Conexión de inventario al motor exitosa!")
        return engine
    except Exception as e:
        st.error(f"Error al conectar con la DB: {e}")
        return None

@st.cache_resource
def load_model_assets():
    """Carga los modelos entrenados, la lista de features y el mapa de productos."""
    try:
        trained_models = joblib.load(MODEL_FILE)
        model_feature_list = joblib.load(FEATURES_FILE)
        info_productos = {
            # (Tu diccionario info_productos va aquí...)
            "Salchicha de Pavo con Huevo Revuelto y Patata": ("Desayuno Caliente", "Normal"),
            "Ratatouille con Tostadas": ("Desayuno Caliente", "Vegetariano"),
            "Pollo con Ensalada de Patata y Espárragos": ("Almuerzo Frío", "Normal"),
            "Sándwich de pavo y queso": ("Almuerzo Frío", "Normal"),
            "Ragú de Ternera con Puré": ("Platos Calientes (Rotativo)", "Normal"),
            "Opción VIP: Lomo de Salmón con Salsa de Eneldo": ("Platos Calientes (Rotativo)", "VIP"),
            "Coeur Lion Camembert": ("Selecciones de Quesos", "Normal"),
            "Blue Castello": ("Selecciones de Quesos", "Normal"),
            "Agua Mineral (500ml)": ("Bebidas (No Alcohólicas)", "Normal"),
            "Refresco Cola (Lata)": ("Bebidas (No Alcohólicas)", "Normal"),
            "Pan dulce de Nuez": ("Snacks y Panadería", "Normal"),
            "Papitas Sabor Original (Bolsa Individual)": ("Snacks y Panadería", "Normal")
        }
        print("¡Modelos de predicción cargados!")
        return trained_models, model_feature_list, info_productos
    except Exception as e:
        print(f"!!! ERROR AL CARGAR ARCHIVOS .joblib !!! Error: {e}")
        return None, None, None

# --- 3. FUNCIONES DE LÓGICA DE NEGOCIO ---

@st.cache_data(ttl=600) # Cachear los datos del inventario por 10 minutos
def fetch_inventory_data(_engine):
    """Consulta la DB y devuelve el inventario con estado R/Y/G."""
    
    # La consulta SQL no cambia
    sql_query = text("""
        SELECT L.Lote_ID, L.Numero_Lote, L.Fecha_Caducidad, P.Nombre AS Nombre_Producto
        FROM LOTE_PRODUCTO AS L
        JOIN PRODUCTO AS P ON L.Producto_ID = P.Producto_ID
        ORDER BY L.Fecha_Caducidad ASC;
    """)
    
    inventory_list = []
    today = datetime.date.today()
    one_week_from_now = today + datetime.timedelta(days=7)
    
    try:
        with _engine.connect() as conn:
            result = conn.execute(sql_query)
            for row in result:
                item = dict(row._mapping)
                exp_date = item['Fecha_Caducidad']
                
                # --- ¡AQUÍ ESTÁ EL CAMBIO! ---
                # Calculamos la diferencia de días
                dias_restantes = (exp_date - today).days
                item['Dias_Restantes'] = dias_restantes
                # --- FIN DEL CAMBIO ---

                # La lógica de estado (R/Y/G) no cambia
                if exp_date <= today:
                    item['Estado'] = '🔴 Caducado'
                elif exp_date <= one_week_from_now:
                    item['Estado'] = '🟡 Próximo a Caducar'
                else:
                    item['Estado'] = '🟢 En Buen Estado'
                
                item['Fecha_Caducidad'] = exp_date.isoformat()
                inventory_list.append(item)
        return pd.DataFrame(inventory_list)
    except Exception as e:
        st.error(f"Error al consultar inventario: {e}")
        return pd.DataFrame()

# --- ¡ELIMINADO! ---
# La función discard_lot() ya no es necesaria.

# --- 4. DATOS PARA LOS MENÚS DESPLEGABLES ---
LISTA_AEROLINEAS = [
    'LATAM Airlines', 'Qatar Airways', 'Iberia Airlines', 'EasyJet', 'Lufthansa',
    'United Airlines', 'Delta Air Lines', 'Virgin Atlantic', 'Air Europa', 'T\'way Air',
    'Japan Airlines', 'Aeroméxico', 'Avianca', 'Aeromar', 'Aerolíneas Argentinas'
]
LISTA_LOCALIDADES = [
    'Santiago, Chile', 'Doha, Catar', 'Madrid, España', 'Londres, Reino Unido',
    'Frankfurt, Alemania', 'Nueva York, EEUU', 'Ciudad de México, México', 'Tokio, Japón'
]
LISTA_DIAS = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
LISTA_HORA_DIA = ['Mañana', 'Tarde', 'Noche']
LISTA_TEMPORADA = ['Baja', 'Media', 'Alta']
LISTA_CLIMA = ['Soleado', 'Lluvioso', 'Nevado', 'Nublado', 'Tormenta']
LISTA_TRAYECTO = ['Nacional', 'Internacional']

# --- 5. LÓGICA PRINCIPAL DE LA APLICACIÓN ---
def main():
    
    engine = get_db_engine()
    model_assets = load_model_assets()
    
    if not engine:
        st.error("❌ ERROR CRÍTICO: No se pudo conectar a la Base de Datos.")
        return
    if model_assets[0] is None or model_assets[1] is None:
        st.error("❌ ERROR CRÍTICO: No se pudieron cargar los archivos del modelo (.joblib).")
        return
    
    st.success("✅ ¡Conexión a la Base de Datos y Modelos cargados exitosamente!")
    
    trained_models, model_feature_list, info_productos = model_assets
    
    if not trained_models:
        st.warning("⚠️ Aviso: No se encontraron modelos entrenados.")

    st.sidebar.title("Navegación")
    page = st.sidebar.radio(
        "Ir a:",
        ["✈️ Predicción de Consumo", "🚨 Gestión de Inventario"]
    )
    
    # ... (PÁGINA 1: PREDICCIÓN DE CONSUMO - No cambia en absoluto) ...
    if page == "✈️ Predicción de Consumo":
        st.title("✈️ Simulador de Carga de Vuelo")
        st.markdown("Selecciona los parámetros del vuelo para predecir el consumo de alimentos.")

        with st.form(key="prediction_form"):
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Info del Vuelo")
                num_pasajeros = st.number_input("Número de Pasajeros", min_value=1, max_value=500, value=150)
                aerolinea = st.selectbox("Aerolínea", options=LISTA_AEROLINEAS, index=11) 
                distancia_km = st.number_input("Distancia (KM)", min_value=100, max_value=20000, value=1500)
                tipo_trayecto = st.selectbox("Tipo de Trayecto", options=LISTA_TRAYECTO)
                capacidad_avion = st.number_input("Capacidad Máx. Avión", min_value=50, max_value=500, value=180)
            
            with col2:
                st.subheader("Contexto del Vuelo")
                hora_dia = st.selectbox("Hora del Día", options=LISTA_HORA_DIA)
                dia_semana = st.selectbox("Día de la Semana", options=LISTA_DIAS, index=4) 
                temporada = st.selectbox("Temporada", options=LISTA_TEMPORADA, index=2)
                condicion_clima = st.selectbox("Condición Climática", options=LISTA_CLIMA)
                localidad_salida = st.selectbox("Localidad de Salida", options=LISTA_LOCALIDADES, index=6)
                localidad_llegada = st.selectbox("Localidad de Llegada", options=LISTA_LOCALIDADES, index=2)

            submit_button = st.form_submit_button(label="Predecir Consumo")

        if submit_button:
            if not trained_models:
                st.error("No se pueden hacer predicciones porque no hay modelos entrenados.")
            else:
                with st.spinner("Calculando predicciones... 🧠"):
                    # (Toda la lógica de predicción va aquí, no cambia)
                    datos_vuelo_futuro = {
                        "Num_Pasajeros": num_pasajeros, "Aerolinea": aerolinea, "Distancia_KM": distancia_km,
                        "Tipo_Trayecto": tipo_trayecto, "Capacidad_Max_Avion": capacidad_avion, "Hora_Dia": hora_dia,
                        "Dia_Semana": dia_semana, "Temporada": temporada, "Condicion_Climatica": condicion_clima,
                        "Localidad_Salida": localidad_salida, "Localidad_Llegada": localidad_llegada
                    }
                    predicciones_finales = {}
                    for nombre_producto, modelo_especifico in trained_models.items():
                        try:
                            categoria, tipo_especial = info_productos[nombre_producto]
                            datos_completos_producto = datos_vuelo_futuro.copy()
                            datos_completos_producto['Nombre_Categoria'] = categoria
                            datos_completos_producto['Tipo_Especial'] = tipo_especial
                            if 'Aerolinea' in datos_completos_producto:
                                datos_completos_producto['Nombre_Aerolinea'] = datos_completos_producto.pop('Aerolinea')
                            nuevo_vuelo_df = pd.DataFrame([datos_completos_producto])
                            nuevo_vuelo_procesado = pd.get_dummies(nuevo_vuelo_df)
                            nuevo_vuelo_procesado = nuevo_vuelo_procesado.reindex(columns=model_feature_list, fill_value=0)
                            prediccion = modelo_especifico.predict(nuevo_vuelo_procesado)
                            unidades_necesarias = max(0, prediccion[0])
                            predicciones_finales[nombre_producto] = round(unidades_necesarias)
                        except Exception as e:
                            predicciones_finales[nombre_producto] = -1
                    st.subheader("Resultados de la Predicción")
                    results_df = pd.DataFrame.from_dict(predicciones_finales, orient='index', columns=['Unidades Necesarias'])
                    results_df = results_df[results_df['Unidades Necesarias'] > 0] 
                    results_df = results_df.sort_values(by='Unidades Necesarias', ascending=False)
                    if results_df.empty:
                        st.info("No se predijo consumo para este tipo de vuelo.")
                    else:
                        st.dataframe(results_df)
                        st.balloons()

    # ==================================================================
    # PÁGINA 2: GESTIÓN DE INVENTARIO (Simplificada)
    # ==================================================================
    elif page == "🚨 Gestión de Inventario":
        st.title("🚨 Gestión de Caducidad de Lotes")
        st.markdown("Esta tabla muestra **todos** los lotes y su estado de caducidad calculado.")
        
        if st.button("Refrescar Datos"):
            st.cache_data.clear() # Limpia el caché de 'fetch_inventory_data'
            st.rerun()

        df_inventory = fetch_inventory_data(engine)
        
        if df_inventory.empty:
            st.info("No se encontraron lotes en la base de datos.")
        else:
            # Función para colorear el Estado (con Verde)
            def style_status(val):
                color = 'black'
                if val == '🔴 Caducado':
                    color = 'red'
                elif val == '🟡 Próximo a Caducar':
                    color = '#d17900' # Naranja/Ámbar
                elif val == '🟢 En Buen Estado':
                    color = 'green' # Verde
                return f'color: {color}; font-weight: bold;'
            
            # --- ¡NUEVO! Función para colorear los Días Restantes ---
            def style_dias_restantes(val):
                color = 'black'
                if val <= 0:
                    color = 'red'
                elif val <= 7:
                    color = '#d17900' # Naranja/Ámbar
                else:
                    color = 'green'
                return f'color: {color}; font-weight: bold;'

            # --- ¡CAMBIO IMPORTANTE! ---
            # Añadimos 'Dias_Restantes' a la lista de columnas del dataframe
            st.dataframe(
                df_inventory[['Estado', 'Dias_Restantes', 'Nombre_Producto', 'Numero_Lote', 'Fecha_Caducidad']]
                .style
                .apply(axis=0, subset=['Estado'], func=lambda x: [style_status(v) for v in x])
                .apply(axis=0, subset=['Dias_Restantes'], func=lambda x: [style_dias_restantes(v) for v in x]), # Aplicamos el nuevo estilo
                
                use_container_width=True
            )
            
            # --- ¡ELIMINADO! ---
            # Toda la sección de "Marcar Lote como Desechado" ha sido eliminada.

if __name__ == "__main__":
    main()
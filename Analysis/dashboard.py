import streamlit as st
import pandas as pd
import numpy as np
import joblib
from sqlalchemy import create_engine, text
import datetime
from pathlib import Path
import altair as alt

# --- 1. CONFIGURACIÓN INICIAL ---
st.set_page_config( page_title="Gategroup Dashboard", page_icon="✈️", layout="wide")

# --- 2. CACHING DE RECURSOS ---
BASE_DIR = Path(__file__).resolve().parent
MODEL_FILE = BASE_DIR / "modelos_comida.joblib"
FEATURES_FILE = BASE_DIR / "lista_de_features.joblib"
# LOGO_FILE = BASE_DIR / "logo.png" # Descomenta si tienes un logo

@st.cache_resource
def get_db_engine():
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
    try:
        trained_models = joblib.load(MODEL_FILE)
        model_feature_list = joblib.load(FEATURES_FILE)
        info_productos = {
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

@st.cache_data(ttl=300)
def fetch_inventory_dashboard_data(_engine):
    sql_query = text("""
        SELECT P.Producto_ID, P.Nombre AS Nombre_Producto, CP.Nombre AS Nombre_Categoria,
               L.Lote_ID, L.Numero_Lote, L.Fecha_Caducidad, L.Cantidad_Inicial,
               COALESCE(Agg.Total_Consumido, 0) AS Total_Consumido,
               (L.Cantidad_Inicial - COALESCE(Agg.Total_Consumido, 0)) AS Cantidad_Actual
        FROM LOTE_PRODUCTO AS L JOIN PRODUCTO AS P ON L.Producto_ID = P.Producto_ID
        JOIN CATEGORIA_PRODUCTO AS CP ON P.Categoria_ID = CP.Categoria_ID
        LEFT JOIN ( SELECT Lote_ID, SUM(COALESCE(Cantidad_Consumida, 0)) AS Total_Consumido
                    FROM SERVICIO_LOTE_VUELO GROUP BY Lote_ID ) AS Agg ON L.Lote_ID = Agg.Lote_ID
        ORDER BY L.Fecha_Caducidad ASC; """)
    inventory_list = []; today = datetime.date.today()
    try:
        with _engine.connect() as conn:
            result = conn.execute(sql_query)
            for row in result:
                item = dict(row._mapping); exp_date = item['Fecha_Caducidad']
                dias_restantes = (exp_date - today).days; item['Dias_Restantes'] = dias_restantes
                if dias_restantes <= 0: item['Estado'] = '🔴 Crítico'
                elif dias_restantes <= 3: item['Estado'] = '🟠 Advertencia'
                elif dias_restantes <= 7: item['Estado'] = '🟡 Atención'
                else: item['Estado'] = '🟢 Óptimo'
                item['Fecha_Caducidad'] = exp_date.isoformat(); inventory_list.append(item)
        return pd.DataFrame(inventory_list)
    except Exception as e:
        st.error(f"Error al consultar inventario: {e}"); return pd.DataFrame()

@st.cache_data(ttl=300)
def calculate_historical_consumption(_engine, analysis_window_days=30):
    sql_query = text(f"""
        SELECT P.Producto_ID, P.Nombre AS Nombre_Producto, SUM(SLV.Cantidad_Consumida) AS Total_Consumido
        FROM SERVICIO_LOTE_VUELO AS SLV JOIN VUELO AS V ON SLV.Vuelo_ID = V.Vuelo_ID
        JOIN LOTE_PRODUCTO AS LP ON SLV.Lote_ID = LP.Lote_ID JOIN PRODUCTO AS P ON LP.Producto_ID = P.Producto_ID
        WHERE V.Fecha_Salida >= CURDATE() - INTERVAL {analysis_window_days} DAY AND SLV.Cantidad_Consumida IS NOT NULL
        GROUP BY P.Producto_ID, P.Nombre; """)
    try:
        df = pd.read_sql(sql_query, _engine)
        if df.empty: return pd.DataFrame(columns=['Producto_ID', 'Nombre_Producto', 'Avg_Diario', 'Avg_Semanal'])
        df['Avg_Diario'] = df['Total_Consumido'] / analysis_window_days
        df['Avg_Semanal'] = df['Avg_Diario'] * 7
        return df
    except Exception as e:
        st.error(f"Error calculando consumo histórico: {e}"); return pd.DataFrame(columns=['Producto_ID', 'Nombre_Producto', 'Avg_Diario', 'Avg_Semanal'])

@st.cache_data(ttl=300)
def fetch_recommendations(_engine):
    df_inventory = fetch_inventory_dashboard_data(_engine); df_consumption = calculate_historical_consumption(_engine)
    if df_inventory.empty: return []
    recommendations = []; df_lotes_activos = df_inventory[df_inventory['Cantidad_Actual'] > 0]
    for _, lote in df_lotes_activos.iterrows():
        dias = lote['Dias_Restantes']
        if dias <= 0: recommendations.append({ "Prioridad": "Alta", "Icono": "🔴", "Estado": "error", "Tipo": "Lote Caducado", "Producto": lote['Nombre_Producto'], "Lote": lote['Numero_Lote'], "Metrica": f"{lote['Cantidad_Actual']} items caducados (hace {-dias} días).", "Accion": "Retirar de inventario y desechar inmediatamente."})
        elif 0 < dias <= 3: recommendations.append({"Prioridad": "Alta", "Icono": "🟠", "Estado": "error", "Tipo": "Riesgo Alto de Merma", "Producto": lote['Nombre_Producto'], "Lote": lote['Numero_Lote'], "Metrica": f"{lote['Cantidad_Actual']} items vencen en {dias} días.", "Accion": "Usar urgente o donar. Priorizar en próximos vuelos."})
    df_stock_total = df_lotes_activos.groupby('Producto_ID').agg(Stock_Total=('Cantidad_Actual', 'sum'), Nombre_Producto=('Nombre_Producto', 'first')).reset_index()
    if not df_consumption.empty:
        df_product_analysis = pd.merge(df_stock_total, df_consumption, on='Producto_ID', how='left')
        df_product_analysis['Avg_Semanal'] = df_product_analysis['Avg_Semanal'].fillna(0)
        for _, prod in df_product_analysis.iterrows():
            stock = prod['Stock_Total']; consumo_sem = prod['Avg_Semanal']
            if consumo_sem > 0 and stock < (consumo_sem * 0.5): recommendations.append({"Prioridad": "Media", "Icono": "🟡", "Estado": "warning", "Tipo": "Riesgo de Quiebre de Stock", "Producto": prod['Nombre_Producto_x'], "Lote": "N/A (Todos los lotes)", "Metrica": f"Stock Total: {stock:.0f} | Consumo Semanal: {consumo_sem:.1f}", "Accion": "Reabastecer pronto. Inventario actual está por debajo del 50% del consumo."})
    def sort_key(r):
        prio_map = {"Alta": 0, "Media": 1, "Baja": 2}; dias = 999
        if "días" in r["Metrica"]:
             try: dias = int(r["Metrica"].split(" ")[-2])
             except: pass
        if "caducados" in r["Metrica"]: dias = -int(r["Metrica"].split(" ")[-2])
        return (prio_map.get(r["Prioridad"], 9), dias)
    recommendations.sort(key=sort_key)
    return recommendations

# --- ¡FUNCIÓN MOVIDA AQUÍ! ---
def run_prediction_logic(flight_data, models, features, product_map):
    """ Ejecuta la lógica de predicción y devuelve un DataFrame de resultados. """
    predicciones = {}
    for nombre_producto, modelo_especifico in models.items():
        try:
            categoria, tipo_especial = product_map[nombre_producto]
            datos_completos = flight_data.copy()
            datos_completos['Nombre_Categoria'] = categoria; datos_completos['Tipo_Especial'] = tipo_especial
            if 'Aerolinea' in datos_completos: datos_completos['Nombre_Aerolinea'] = datos_completos.pop('Aerolinea')
            df_nuevo = pd.DataFrame([datos_completos])
            df_procesado = pd.get_dummies(df_nuevo); df_procesado = df_procesado.reindex(columns=features, fill_value=0)
            prediccion = modelo_especifico.predict(df_procesado); unidades = max(0, prediccion[0])
            predicciones[nombre_producto] = round(unidades)
        except Exception: predicciones[nombre_producto] = -1
    df_resultados = pd.DataFrame.from_dict(predicciones, orient='index', columns=['Demanda_Base'])
    df_resultados = df_resultados[df_resultados['Demanda_Base'] > 0]
    return df_resultados

# (La función generate_manifest_pdf fue eliminada en el paso anterior)

# --- 4. DATOS PARA LOS MENÚS DESPLEGABLES ---
LISTA_AEROLINEAS = ['LATAM Airlines', 'Qatar Airways', 'Iberia Airlines', 'EasyJet', 'Lufthansa', 'United Airlines', 'Delta Air Lines', 'Virgin Atlantic', 'Air Europa', 'T\'way Air', 'Japan Airlines', 'Aeroméxico', 'Avianca', 'Aeromar', 'Aerolíneas Argentinas']
LISTA_LOCALIDADES = ['Santiago, Chile', 'Doha, Catar', 'Madrid, España', 'Londres, Reino Unido', 'Frankfurt, Alemania', 'Nueva York, EEUU', 'Ciudad de México, México', 'Tokio, Japón']
LISTA_DIAS = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
LISTA_HORA_DIA = ['Mañana', 'Tarde', 'Noche']
LISTA_TEMPORADA = ['Baja', 'Media', 'Alta']
LISTA_CLIMA = ['Soleado', 'Lluvioso', 'Nevado', 'Nublado', 'Tormenta']
LISTA_TRAYECTO = ['Nacional', 'Internacional']

# --- 5. LÓGICA PRINCIPAL DE LA APLICACIÓN ---
def main():
    engine = get_db_engine(); model_assets = load_model_assets()
    if not engine: st.error("❌ ERROR CRÍTICO: No se pudo conectar a la Base de Datos."); return
    if model_assets[0] is None or model_assets[1] is None: st.error("❌ ERROR CRÍTICO: No se pudieron cargar los archivos del modelo (.joblib)."); return
    trained_models, model_feature_list, info_productos = model_assets
    if not trained_models: st.sidebar.warning("Aviso: No se encontraron modelos entrenados.")

    st.sidebar.title("Navegación")
    page_options = ["📊 Panel Principal", "💡 Recomendaciones", "✈️ Predicción de Consumo", "📋 Manifesto de Carga", "🚨 Auditoría de Lotes"]
    page = st.sidebar.radio("Ir a:", page_options)

    # ===================== PÁGINA 1: PANEL PRINCIPAL =====================
    if page == "📊 Panel Principal":
        st.title("📊 Panel Principal de Inventario")
        st.markdown("Vista consolidada del inventario activo y métricas clave.")
        df_inventory_full = fetch_inventory_dashboard_data(engine)
        if df_inventory_full.empty: st.warning("No se encontraron datos de inventario."); return
        df_activos = df_inventory_full[df_inventory_full['Cantidad_Actual'] > 0].copy()
        total_items_actuales = df_activos['Cantidad_Actual'].sum()
        total_lotes_activos = len(df_activos)
        lotes_optimos = len(df_activos[df_activos['Estado'] == '🟢 Óptimo'])
        lotes_en_riesgo = len(df_activos[df_activos['Estado'].str.contains('Crítico|Advertencia|Atención')])
        st.header("Métricas en Tiempo Real")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Inventario Total (Items)", f"{total_items_actuales:,.0f}")
        col2.metric("Lotes Activos (con stock)", f"{total_lotes_activos:,.0f}")
        col3.metric("Lotes en Estado Óptimo", f"{lotes_optimos:,.0f}")
        col4.metric("Lotes en Riesgo (≤7 Días)", f"{lotes_en_riesgo:,.0f}", delta=f"{lotes_en_riesgo} Lotes en Riesgo", delta_color="inverse")
        st.divider()
        st.header("Visualización del Inventario")
        df_estado_grupo = df_activos.groupby('Estado').agg(Conteo=('Estado', 'count')).reset_index()
        df_categoria_grupo = df_activos.groupby('Nombre_Categoria').agg(Stock_Total=('Cantidad_Actual', 'sum')).reset_index()
        col_graf1, col_graf2 = st.columns(2)
        with col_graf1:
            domain_colores = ['🔴 Crítico', '🟠 Advertencia', '🟡 Atención', '🟢 Óptimo']
            range_colores = ['#d9534f', '#f0ad4e', '#FFD700', '#5cb85c']
            pie_chart = alt.Chart(df_estado_grupo).mark_arc(outerRadius=120).encode(theta=alt.Theta("Conteo:Q", stack=True), color=alt.Color("Estado:N", scale=alt.Scale(domain=domain_colores, range=range_colores), legend=alt.Legend(title="Estado del Lote")), tooltip=["Estado", "Conteo"]).properties(title="Distribución del Estado del Inventario")
            st.altair_chart(pie_chart, use_container_width=True)
        with col_graf2:
            bar_chart = alt.Chart(df_categoria_grupo).mark_bar().encode(x=alt.X('Nombre_Categoria:N', title='Categoría', sort='-y'), y=alt.Y('Stock_Total:Q', title='Cantidad de Stock Total'), color='Nombre_Categoria:N', tooltip=['Nombre_Categoria', 'Stock_Total']).properties(title="Stock Total por Categoría").interactive()
            st.altair_chart(bar_chart, use_container_width=True)
        st.divider()
        st.header("Inventario Actual (Ordenado por FEFO)")
        st.markdown("Solo se muestran lotes con `Cantidad_Actual > 0`.")
        def style_status(val):
            color = 'black'
            if val == '🔴 Crítico': color = '#d9534f'
            elif val == '🟠 Advertencia': color = '#f0ad4e'
            elif val == '🟡 Atención': color = '#E5C100'
            elif val == '🟢 Óptimo': color = '#5cb85c'
            return f'color: {color}; font-weight: bold;'
        columnas_display = ['Estado', 'Dias_Restantes', 'Nombre_Producto', 'Numero_Lote', 'Cantidad_Actual', 'Fecha_Caducidad']
        df_display = df_activos[columnas_display].rename(columns={'Nombre_Producto': 'Producto', 'Numero_Lote': 'Código de Lote', 'Cantidad_Actual': 'Cantidad', 'Fecha_Caducidad': 'Vencimiento', 'Dias_Restantes': 'Días Restantes'})
        st.dataframe(df_display.style.apply(axis=0, subset=['Estado'], func=lambda x: [style_status(v) for v in x]).apply(axis=0, subset=['Días Restantes'], func=lambda x: [style_status(v) for v in x.map(lambda d: df_activos.loc[x.index[list(x).index(d)]]['Estado'])]), use_container_width=True)

    # ===================== PÁGINA 2: RECOMENDACIONES =====================
    elif page == "💡 Recomendaciones":
        st.title("💡 Panel de Recomendaciones")
        st.markdown("Acciones prioritarias basadas en inventario y consumo (últimos 30 días).")
        if st.button("Refrescar Recomendaciones"): st.cache_data.clear(); st.rerun()
        with st.spinner("Generando recomendaciones... 🧠"): recommendations = fetch_recommendations(engine)
        if not recommendations: st.success("🎉 ¡Todo en orden! No hay recomendaciones urgentes.")
        else:
            alta = [r for r in recommendations if r['Prioridad'] == 'Alta']; media = [r for r in recommendations if r['Prioridad'] == 'Media']
            if alta:
                st.subheader("Prioridad Alta (Acción Inmediata)")
                for r in alta:
                    with st.status(label=f"**{r['Icono']} {r['Tipo']}:** {r['Producto']}", state="error"): st.markdown(f"**Lote:** {r['Lote']}"); st.markdown(f"**Métrica:** {r['Metrica']}"); st.markdown(f"**Acción:** {r['Accion']}")
            if media:
                st.subheader("Prioridad Media (Planificar)")
                for r in media:
                    with st.status(label=f"**{r['Icono']} {r['Tipo']}:** {r['Producto']}", state="warning"): st.markdown(f"**Lote:** {r['Lote']}"); st.markdown(f"**Métrica:** {r['Metrica']}"); st.markdown(f"**Acción:** {r['Accion']}")

    # ===================== PÁGINA 3: PREDICCIÓN DE CONSUMO =====================
    elif page == "✈️ Predicción de Consumo":
        st.title("✈️ Simulador de Carga de Vuelo"); st.markdown("Selecciona los parámetros del vuelo para predecir el consumo.")
        results_placeholder = st.empty()
        with st.form(key="prediction_form"):
            col1, col2 = st.columns(2)
            with col1: st.subheader("Info del Vuelo"); num_pasajeros = st.number_input("Número de Pasajeros", 1, 500, 150); aerolinea = st.selectbox("Aerolínea", LISTA_AEROLINEAS, 11); distancia_km = st.number_input("Distancia (KM)", 100, 20000, 1500); tipo_trayecto = st.selectbox("Tipo de Trayecto", LISTA_TRAYECTO); capacidad_avion = st.number_input("Capacidad Máx. Avión", 50, 500, 180)
            with col2: st.subheader("Contexto del Vuelo"); hora_dia = st.selectbox("Hora del Día", LISTA_HORA_DIA); dia_semana = st.selectbox("Día de la Semana", LISTA_DIAS, 4); temporada = st.selectbox("Temporada", LISTA_TEMPORADA, 2); condicion_clima = st.selectbox("Condición Climática", LISTA_CLIMA); localidad_salida = st.selectbox("Localidad de Salida", LISTA_LOCALIDADES, 6); localidad_llegada = st.selectbox("Localidad de Llegada", LISTA_LOCALIDADES, 2)
            submit_button = st.form_submit_button(label="Predecir Consumo")
        if submit_button:
            if not trained_models: results_placeholder.error("No se pueden hacer predicciones.")
            else:
                with st.spinner("Calculando predicciones... 🧠"):
                    datos_vuelo_futuro = {"Num_Pasajeros": num_pasajeros, "Aerolinea": aerolinea, "Distancia_KM": distancia_km, "Tipo_Trayecto": tipo_trayecto, "Capacidad_Max_Avion": capacidad_avion, "Hora_Dia": hora_dia, "Dia_Semana": dia_semana, "Temporada": temporada, "Condicion_Climatica": condicion_clima, "Localidad_Salida": localidad_salida, "Localidad_Llegada": localidad_llegada}
                    df_resultados = run_prediction_logic(datos_vuelo_futuro, trained_models, model_feature_list, info_productos) # USA LA FUNCIÓN GLOBAL
                with results_placeholder.container():
                    st.subheader("Resultados de la Predicción")
                    if df_resultados.empty: st.info("No se predijo consumo.")
                    else: st.dataframe(df_resultados)

    # ==================================================================
    # PÁGINA 4: MANIFESTO DE CARGA (Título corregido)
    # ==================================================================
    elif page == "📋 Manifesto de Carga":
        st.title("📋 Manifesto de Carga")
        st.markdown("Genera y asigna lotes (FEFO) para la carga de un vuelo específico.")

        # Inicializar estado si no existe
        if 'manifesto_df' not in st.session_state:
            st.session_state.manifesto_df = pd.DataFrame()
            st.session_state.manifesto_lotes_asignados = {}

        # --- STEP 1: Formulario de Datos del Vuelo ---
        st.header("1. Datos del Vuelo")
        with st.form(key="manifesto_form"):
            col1, col2 = st.columns(2)
            # ... (Inputs del formulario - sin cambios) ...
            with col1:
                m_num_pasajeros = st.number_input("Número de Pasajeros", 1, 500, 150)
                m_aerolinea = st.selectbox("Aerolínea", LISTA_AEROLINEAS, 11)
                m_distancia_km = st.number_input("Distancia (KM)", 100, 20000, 1500)
                m_tipo_trayecto = st.selectbox("Tipo de Trayecto", LISTA_TRAYECTO)
            with col2:
                m_capacidad_avion = st.number_input("Capacidad Máx. Avión", 50, 500, 180)
                m_hora_dia = st.selectbox("Hora del Día", LISTA_HORA_DIA)
                m_dia_semana = st.selectbox("Día de la Semana", LISTA_DIAS, 4)
                m_temporada = st.selectbox("Temporada", LISTA_TEMPORADA, 2)
            m_localidad_salida = st.selectbox("Localidad de Salida", LISTA_LOCALIDADES, 6)
            m_localidad_llegada = st.selectbox("Localidad de Llegada", LISTA_LOCALIDADES, 2)
            m_condicion_clima = st.selectbox("Condición Climática", LISTA_CLIMA)

            manifesto_submit = st.form_submit_button(label="Generar Recomendación de Carga")

        # --- STEP 2: Lógica (Predicción + Buffer + Asignación FEFO) ---
        if manifesto_submit:
            with st.spinner("Calculando demanda, aplicando buffer y asignando lotes FEFO..."):
                datos_vuelo = { # Diccionario con datos del vuelo
                    "Num_Pasajeros": m_num_pasajeros, "Aerolinea": m_aerolinea, "Distancia_KM": m_distancia_km,
                    "Tipo_Trayecto": m_tipo_trayecto, "Capacidad_Max_Avion": m_capacidad_avion, "Hora_Dia": m_hora_dia,
                    "Dia_Semana": m_dia_semana, "Temporada": m_temporada, "Condicion_Climatica": m_condicion_clima,
                    "Localidad_Salida": m_localidad_salida, "Localidad_Llegada": m_localidad_llegada
                }
                df_demanda = run_prediction_logic(datos_vuelo, trained_models, model_feature_list, info_productos)

                if df_demanda.empty:
                    st.error("No se predijo demanda."); st.session_state.manifesto_df = pd.DataFrame(); st.session_state.manifesto_lotes_asignados = {}
                else:
                    df_demanda['Buffer (5%)'] = (df_demanda['Demanda_Base'] * 0.05).apply(np.ceil)
                    df_demanda['Cantidad_Final'] = df_demanda['Demanda_Base'] + df_demanda['Buffer (5%)']
                    df_manifesto = df_demanda.astype(int)[['Demanda_Base', 'Buffer (5%)', 'Cantidad_Final']].sort_values(by='Cantidad_Final', ascending=False)
                    st.session_state.manifesto_df = df_manifesto

                    # --- Lógica de Asignación FEFO ---
                    df_inventory = fetch_inventory_dashboard_data(engine)
                    # Filtra por stock > 0 Y que el estado NO sea Crítico
                    df_inv_activos = df_inventory[(df_inventory['Cantidad_Actual'] > 0) & (df_inventory['Estado'] != '🔴 Crítico')]

                    lotes_asignados_dict = {}
                    inventario_temporal = df_inv_activos.copy()

                    for producto, row in df_manifesto.iterrows():
                        cantidad_necesaria = row['Cantidad_Final']
                        lotes_para_producto = []
                        lotes_disponibles = inventario_temporal[inventario_temporal['Nombre_Producto'] == producto].sort_values(by='Fecha_Caducidad') # FEFO

                        for _, lote in lotes_disponibles.iterrows():
                            if cantidad_necesaria <= 0: break

                            needed = int(cantidad_necesaria)
                            available = int(lote['Cantidad_Actual'])
                            cantidad_a_tomar = min(needed, available)

                            if cantidad_a_tomar > 0:
                                lotes_para_producto.append({
                                    'Numero_Lote': lote['Numero_Lote'],
                                    'Cantidad_Tomada': cantidad_a_tomar,
                                    'Fecha_Caducidad': lote['Fecha_Caducidad'],
                                    'Estado_Lote': lote['Estado'] # Guardamos el estado para mostrarlo
                                })
                                inventario_temporal.loc[lote.name, 'Cantidad_Actual'] -= cantidad_a_tomar
                                cantidad_necesaria -= cantidad_a_tomar

                        lotes_asignados_dict[producto] = lotes_para_producto

                        if cantidad_necesaria > 0:
                             st.warning(f"¡Insuficiente stock para '{producto}'! Faltan {cantidad_necesaria} unidades.")

                    st.session_state.manifesto_lotes_asignados = lotes_asignados_dict


        # --- STEP 3: Mostrar Manifiesto (como lista) e Inventario ---
        if not st.session_state.manifesto_df.empty:
            st.divider()
            st.header("2. Revisión del Manifiesto y Stock")

            col_man, col_inv = st.columns([0.6, 0.4])

            with col_man:
                st.subheader("Manifiesto Recomendado (Lotes Asignados FEFO)")
                st.markdown("Productos, cantidades y lotes específicos sugeridos.")

                df_manifest = st.session_state.manifesto_df
                lotes_asignados = st.session_state.manifesto_lotes_asignados

                for producto, row in df_manifest.iterrows():
                    lotes_del_producto = lotes_asignados.get(producto, [])

                    # --- TÍTULO CORREGIDO ---
                    # El título del expander ahora es más simple
                    titulo_expander = f"📦 **{producto}**"

                    with st.expander(titulo_expander, expanded=True):
                        # --- CANTIDAD FINAL DESTACADA (DENTRO) ---
                        # Usamos markdown con HTML para el tamaño
                        st.markdown(f"Cantidad Total: <span style='font-size: 1.5em; font-weight: bold;'>{row['Cantidad_Final']}</span>", unsafe_allow_html=True)
                        st.markdown(f"(Demanda Base: `{row['Demanda_Base']}` | Buffer: `{row['Buffer (5%)']}`)")
                        st.markdown("---") # Separador

                        # --- Mostrar Lotes Asignados ---
                        if lotes_del_producto:
                            st.markdown("**Lotes Asignados (FEFO):**")
                            for lote_info in lotes_del_producto:
                                # Mostramos el estado del lote asignado
                                st.markdown(f"   - Lote `{lote_info['Numero_Lote']}` ({lote_info['Estado_Lote']}): Tomar `{lote_info['Cantidad_Tomada']}` (Vence: {lote_info['Fecha_Caducidad']})")
                        else:
                            st.warning("   - No se encontraron lotes disponibles o no se pudo cubrir la cantidad.")

            with col_inv:
                st.subheader("Inventario FEFO Relevante")
                st.markdown("Stock (no caduco) de los productos del manifiesto.")
                
                # --- PASO 1: Ver inventario COMPLETO ---
                df_inventory = fetch_inventory_dashboard_data(engine)
                st.write("1. Inventario Completo (fetch_inventory_dashboard_data):", df_inventory) # DEBUG 1
                
                # --- PASO 2: Filtrar activos (Stock > 0 y NO Crítico) ---
                df_inv_activos = df_inventory[(df_inventory['Cantidad_Actual'] > 0) & (df_inventory['Estado'] != '🔴 Crítico')]
                st.write("2. Inventario Activo (Stock > 0, No Crítico):", df_inv_activos) # DEBUG 2

                # --- PASO 3: Ver qué productos necesita el manifiesto ---
                productos_en_manifiesto = df_manifest.index.tolist()
                st.write("3. Productos requeridos por el manifiesto:", productos_en_manifiesto) # DEBUG 3

                # --- PASO 4: Filtrar por productos del manifiesto ---
                df_inv_filtrado = df_inv_activos[df_inv_activos['Nombre_Producto'].isin(productos_en_manifiesto)]
                st.write("4. Inventario Filtrado Final (para la tabla):", df_inv_filtrado) # DEBUG 4 (El que ya tenías)


    # ===================== PÁGINA 5: AUDITORÍA DE LOTES =====================
    elif page == "🚨 Auditoría de Lotes":
        st.title("🚨 Auditoría de Lotes (Historial Completo)"); st.markdown("Todos los lotes, incluyendo agotados.")
        if st.button("Refrescar Datos"): st.cache_data.clear(); st.rerun()
        df_inventory_full = fetch_inventory_dashboard_data(engine)
        if df_inventory_full.empty: st.info("No se encontraron lotes.")
        else:
            def style_status_audit(val):
                color = 'black'
                if val == '🔴 Crítico': color = '#d9534f'
                elif val == '🟠 Advertencia': color = '#f0ad4e'
                elif val == '🟡 Atención': color = '#E5C100'
                elif val == '🟢 Óptimo': color = '#5cb85c'
                return f'color: {color}; font-weight: bold;'
            df_display_audit = df_inventory_full.rename(columns={'Nombre_Producto': 'Producto', 'Numero_Lote': 'Código de Lote', 'Cantidad_Actual': 'Cantidad Restante', 'Fecha_Caducidad': 'Vencimiento', 'Dias_Restantes': 'Días Restantes'})
            st.dataframe(df_display_audit.style.apply(axis=0, subset=['Estado'], func=lambda x: [style_status_audit(v) for v in x]).apply(axis=0, subset=['Días Restantes'], func=lambda x: [style_status_audit(v) for v in x.map(lambda d: df_inventory_full.loc[x.index[list(x).index(d)]]['Estado'])]), use_container_width=True)

if __name__ == "__main__":
    main()
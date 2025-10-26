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

# --- 2. DICCIONARIO DE TRADUCCIONES ---
# (Asegúrate que este diccionario esté completo y correcto)
translations = {
    "es": {
        # General
        "db_conn_success": "¡Conexión de inventario al motor exitosa!", "db_conn_error": "Error al conectar con la DB:",
        "load_models_success": "¡Modelos de predicción cargados!", "load_models_error": "!!! ERROR AL CARGAR ARCHIVOS .joblib !!! Error:",
        "critical_db_error": "❌ ERROR CRÍTICO: No se pudo conectar a la Base de Datos.",
        "critical_model_error": "❌ ERROR CRÍTICO: No se pudieron cargar los archivos del modelo (.joblib).",
        "models_not_trained_warning": "Aviso: No se encontraron modelos entrenados. Vuelve a ejecutar 'train.py'.",
        "sidebar_title": "Navegación", "sidebar_prompt": "Ir a:", "sidebar_lang_select": "Idioma / Language",
        "refresh_button": "Refrescar Datos", "spinner_calculating": "Calculando...", "spinner_generating": "Generando...",
        "error_querying_inventory": "Error al consultar inventario:", "error_calculating_consumption": "Error calculando consumo histórico:",
        "all_clear_no_recommendations": "🎉 ¡Todo en orden! No hay recomendaciones urgentes.",
        "no_inventory_data_warning": "No se encontraron datos de inventario. Revisa la conexión o la base de datos.",
        "no_lots_found": "No se encontraron lotes.", "no_active_lots_found": "No se encontraron lotes activos con stock.",
        # Estado Lotes (Claves internas: critical, warning, attention, optimal)
        "status_critical": "🔴 Crítico", "status_warning": "🟠 Advertencia", "status_attention": "🟡 Atención", "status_optimal": "🟢 Óptimo",
        # Página: Panel Principal
        "dashboard_title": "📊 Panel Principal de Inventario", "dashboard_subtitle": "Vista consolidada del inventario activo y métricas clave.",
        "dashboard_metrics_header": "Métricas en Tiempo Real", "metric_total_inventory": "Inventario Total (Items)",
        "metric_active_lots": "Lotes Activos (con stock)", "metric_optimal_lots": "Lotes en Estado Óptimo",
        "metric_risk_lots": "Lotes en Riesgo (≤7 Días)", "metric_risk_delta": "{count} Lotes en Riesgo",
        "dashboard_viz_header": "Visualización del Inventario", "pie_chart_title": "Distribución del Estado del Inventario",
        "pie_chart_legend": "Estado del Lote", "bar_chart_title": "Stock Total por Categoría",
        "bar_chart_x_axis": "Categoría", "bar_chart_y_axis": "Cantidad de Stock Total",
        "dashboard_table_header": "Inventario Actual (Ordenado por FEFO)",
        "dashboard_table_subtitle": "Mostrando lotes con `Cantidad Actual > 0`.", # Actualizado
        "col_status": "Estado", "col_days_remaining": "Días Restantes", "col_product": "Producto",
        "col_lot_code": "Código de Lote", "col_quantity": "Cantidad", "col_expiration": "Vencimiento",
        # Página: Recomendaciones
        "recommendations_title": "💡 Panel de Recomendaciones", "recommendations_subtitle": "Acciones prioritarias basadas en inventario y consumo (últimos 30 días).",
        "refresh_recommendations_button": "Refrescar Recomendaciones",
        "recommendations_prio_high": "Prioridad Alta (Acción Inmediata)", "recommendations_prio_medium": "Prioridad Media (Planificar)",
        "rec_type_expired": "Lote Caducado", "rec_type_waste_risk": "Riesgo Alto de Merma", "rec_type_stockout_risk": "Riesgo de Quiebre de Stock",
        "rec_metric_expired": "{qty} items caducados (hace {days} días).", "rec_metric_expiring": "{qty} items vencen en {days} días.",
        "rec_metric_stockout": "Stock Total: {stock:.0f} | Consumo Semanal: {consumo:.1f}",
        "rec_action_expired": "Retirar de inventario y desechar inmediatamente.", "rec_action_expiring": "Usar urgente o donar. Priorizar en próximos vuelos.",
        "rec_action_stockout": "Reabastecer pronto. Inventario actual está por debajo del 50% del consumo.",
        "rec_lote_all": "N/A (Todos los lotes)", "prio_high": "Alta", "prio_medium": "Media", "prio_low": "Baja",
        # Página: Predicción de Consumo
        "forecast_title": "✈️ Simulador de Carga de Vuelo", "forecast_subtitle": "Selecciona los parámetros del vuelo para predecir el consumo.",
        "form_flight_info": "Info del Vuelo", "form_passengers": "Número de Pasajeros", "form_airline": "Aerolínea",
        "form_distance": "Distancia (KM)", "form_route_type": "Tipo de Trayecto", "form_aircraft_capacity": "Capacidad Máx. Avión",
        "form_flight_context": "Contexto del Vuelo", "form_time_day": "Hora del Día", "form_day_week": "Día de la Semana",
        "form_season": "Temporada", "form_weather": "Condición Climática", "form_departure": "Localidad de Salida",
        "form_arrival": "Localidad de Llegada", "form_predict_button": "Predecir Consumo",
        "forecast_error_no_models": "No se pueden hacer predicciones porque no hay modelos entrenados.",
        "forecast_results_header": "Resultados de la Predicción", "forecast_no_consumption": "No se predijo consumo para este tipo de vuelo.",
        "col_predicted_demand": "Demanda Prevista",
        # Página: Manifiesto de Carga
        "manifest_title": "📋 Manifesto de Carga", "manifest_subtitle": "Genera y asigna lotes (FEFO) para la carga de un vuelo específico.",
        "manifest_step1_header": "1. Datos del Vuelo", "manifest_generate_button": "Generar Recomendación de Carga",
        "manifest_error_no_demand": "No se predijo demanda.", "manifest_step2_header": "2. Revisión del Manifiesto y Stock",
        "manifest_left_header": "Manifiesto Recomendado (Lotes Asignados FEFO)", "manifest_left_subtitle": "Productos, cantidades y lotes específicos sugeridos.",
        "manifest_total_quantity": "Cantidad Total:", "manifest_base_demand": "Demanda Base", "manifest_buffer": "Buffer",
        "manifest_assigned_lots": "**Lotes Asignados (FEFO):**", "manifest_take_qty": "Tomar", "manifest_expires": "Vence",
        "manifest_no_lots_found": "- No se encontraron lotes disponibles o no se pudo cubrir la cantidad.",
        "manifest_insufficient_stock_warning": "¡Insuficiente stock para '{prod}'! Faltan {qty} unidades.",
        "manifest_right_header": "Inventario FEFO Relevante", "manifest_right_subtitle": "Stock (no caduco) de los productos del manifiesto.",
        # Página: Auditoría de Lotes
        "audit_title": "🚨 Auditoría de Lotes (Historial Completo)", "audit_subtitle": "Todos los lotes, incluyendo agotados.",
        "col_remaining_qty": "Cantidad Restante",
        "manifest_debug_step1": "1. Inventario Completo (fetch_inventory_dashboard_data):",
        "manifest_debug_step2": "2. Inventario Activo (Stock > 0, No Crítico):",
        "manifest_debug_step3": "3. Productos requeridos por el manifiesto:",
        "manifest_debug_step4": "4. Inventario Filtrado Final (para la tabla):",
    },
    "en": {
        # General
        "db_conn_success": "Inventory database connection successful!", "db_conn_error": "Error connecting to DB:",
        "load_models_success": "Prediction models loaded!", "load_models_error": "!!! ERROR LOADING .joblib FILES !!! Error:",
        "critical_db_error": "❌ CRITICAL ERROR: Could not connect to the Database.",
        "critical_model_error": "❌ CRITICAL ERROR: Could not load model files (.joblib).",
        "models_not_trained_warning": "Warning: No trained models found. Run 'train.py' again.",
        "sidebar_title": "Navigation", "sidebar_prompt": "Go to:", "sidebar_lang_select": "Idioma / Language",
        "refresh_button": "Refresh Data", "spinner_calculating": "Calculating...", "spinner_generating": "Generating...",
        "error_querying_inventory": "Error querying inventory:", "error_calculating_consumption": "Error calculating historical consumption:",
        "all_clear_no_recommendations": "🎉 All clear! No urgent recommendations.",
        "no_inventory_data_warning": "No inventory data found. Check connection or database.",
        "no_lots_found": "No lots found.", "no_active_lots_found": "No active lots with stock found.",
        # Lot Status (Internal keys: critical, warning, attention, optimal)
        "status_critical": "🔴 Critical", "status_warning": "🟠 Warning", "status_attention": "🟡 Attention", "status_optimal": "🟢 Optimal",
        # Page: Dashboard
        "dashboard_title": "📊 Inventory Dashboard", "dashboard_subtitle": "Consolidated view of active inventory and key metrics.",
        "dashboard_metrics_header": "Real-Time Metrics", "metric_total_inventory": "Total Inventory (Items)",
        "metric_active_lots": "Active Lots (in stock)", "metric_optimal_lots": "Lots in Optimal State",
        "metric_risk_lots": "Lots at Risk (≤7 Days)", "metric_risk_delta": "{count} Lots at Risk",
        "dashboard_viz_header": "Inventory Visualization", "pie_chart_title": "Inventory Status Distribution",
        "pie_chart_legend": "Lot Status", "bar_chart_title": "Total Stock by Category",
        "bar_chart_x_axis": "Category", "bar_chart_y_axis": "Total Stock Quantity",
        "dashboard_table_header": "Current Inventory (FEFO Ordered)",
        "dashboard_table_subtitle": "Showing lots with `Current Quantity > 0`.", # Updated
        "col_status": "Status", "col_days_remaining": "Days Remaining", "col_product": "Product",
        "col_lot_code": "Lot Code", "col_quantity": "Quantity", "col_expiration": "Expiration",
        # Page: Recommendations
        "recommendations_title": "💡 Recommendations Panel", "recommendations_subtitle": "Priority actions based on inventory status and consumption (last 30 days).",
        "refresh_recommendations_button": "Refresh Recommendations",
        "recommendations_prio_high": "High Priority (Immediate Action)", "recommendations_prio_medium": "Medium Priority (Plan)",
        "rec_type_expired": "Expired Lot", "rec_type_waste_risk": "High Risk of Waste", "rec_type_stockout_risk": "Risk of Stockout",
        "rec_metric_expired": "{qty} items expired ({days} days ago).", "rec_metric_expiring": "{qty} items expire in {days} days.",
        "rec_metric_stockout": "Total Stock: {stock:.0f} | Weekly Consumption: {consumo:.1f}",
        "rec_action_expired": "Remove from inventory and discard immediately.", "rec_action_expiring": "Use urgently or donate. Prioritize on upcoming flights.",
        "rec_action_stockout": "Restock soon. Current inventory is below 50% of consumption.",
        "rec_lote_all": "N/A (All lots)", "prio_high": "High", "prio_medium": "Medium", "prio_low": "Low",
        # Page: Consumption Forecast
        "forecast_title": "✈️ Flight Load Simulator", "forecast_subtitle": "Select flight parameters to forecast food consumption.",
        "form_flight_info": "Flight Info", "form_passengers": "Number of Passengers", "form_airline": "Airline",
        "form_distance": "Distance (KM)", "form_route_type": "Route Type", "form_aircraft_capacity": "Max Aircraft Capacity",
        "form_flight_context": "Flight Context", "form_time_day": "Time of Day", "form_day_week": "Day of Week",
        "form_season": "Season", "form_weather": "Weather Condition", "form_departure": "Departure Location",
        "form_arrival": "Arrival Location", "form_predict_button": "Predict Consumption",
        "forecast_error_no_models": "Cannot make predictions because no models are trained.",
        "forecast_results_header": "Prediction Results", "forecast_no_consumption": "No consumption predicted for this flight type.",
        "col_predicted_demand": "Predicted Demand",
        # Page: Loading Manifest
        "manifest_title": "📋 Loading Manifest", "manifest_subtitle": "Generate and assign lots (FEFO) for a specific flight's load.",
        "manifest_step1_header": "1. Flight Data", "manifest_generate_button": "Generate Load Recommendation",
        "manifest_error_no_demand": "No demand predicted.", "manifest_step2_header": "2. Manifest Review and Stock",
        "manifest_left_header": "Recommended Manifest (FEFO Lots Assigned)", "manifest_left_subtitle": "Suggested products, quantities, and specific lots.",
        "manifest_total_quantity": "Total Quantity:", "manifest_base_demand": "Base Demand", "manifest_buffer": "Buffer",
        "manifest_assigned_lots": "**Assigned Lots (FEFO):**", "manifest_take_qty": "Take", "manifest_expires": "Expires",
        "manifest_no_lots_found": "- No available lots found or quantity could not be met.",
        "manifest_insufficient_stock_warning": "Insufficient stock for '{prod}'! Missing {qty} units.",
        "manifest_right_header": "Relevant FEFO Inventory", "manifest_right_subtitle": "Stock for products in the manifest (non-expired).",
         # Page: Lot Audit
        "audit_title": "🚨 Lot Audit (Full History)", "audit_subtitle": "All lots from the database, including out-of-stock.",
        "col_remaining_qty": "Remaining Qty",
        "manifest_debug_step1": "1. Complete Inventory (fetch_inventory_dashboard_data):",
        "manifest_debug_step2": "2. Active Inventory (Stock > 0, Not Critical):",
        "manifest_debug_step3": "3. Products required by manifest:",
        "manifest_debug_step4": "4. Final Filtered Inventory (for table):",
    }
}

# --- 3. HELPER FUNCTION FOR TRANSLATION ---
def t(key):
    lang = st.session_state.get('lang', 'es')
    # Fallback to Spanish if key not found in selected language
    return translations.get(lang, translations['es']).get(key, translations['es'].get(key, f"[{key}]"))

# --- CACHING DE RECURSOS ---
BASE_DIR = Path(__file__).resolve().parent
MODEL_FILE = BASE_DIR / "modelos_comida.joblib"
FEATURES_FILE = BASE_DIR / "lista_de_features.joblib"

# --- Mapeo FIJO de Status_Key a Color (Independiente del idioma) ---
STATUS_KEY_COLOR_MAP = {
    'critical': '#d9534f', # Rojo
    'warning': '#f0ad4e',  # Naranja
    'attention': '#E5C100',# Amarillo (más oscuro)
    'optimal': '#5cb85c',   # Verde
    'default': '#000000'   # Negro por defecto
}

@st.cache_resource
def get_db_engine():
    try:
        db_url_base = "mysql+pymysql://avnadmin:AVNS_m-BChJcXobgh-J9hPdB@hackmty-tec-4e3a.f.aivencloud.com:13731/gategroup_flights?"
        ssl_args = {'ssl': {'ssl_mode': 'REQUIRED'}}
        engine = create_engine(db_url_base, connect_args=ssl_args)
        print(t("db_conn_success"))
        return engine
    except Exception as e:
        st.error(f"{t('db_conn_error')} {e}")
        return None

@st.cache_resource
def load_model_assets():
    try:
        trained_models = joblib.load(MODEL_FILE)
        model_feature_list = joblib.load(FEATURES_FILE)
        info_productos = { # Asegúrate que estos nombres coincidan EXACTAMENTE con tu tabla PRODUCTO
            "Salchicha de Pavo con Huevo Revuelto y Patata": ("Desayuno Caliente", "Normal"),
            "Ratatouille con Tostadas": ("Desayuno Caliente", "Vegetariano"),
            "Pollo con Ensalada de Patata y Espárragos": ("Almuerzo Frío", "Normal"),
            "Sándwich de pavo y queso": ("Almuerzo Frío", "Normal"),
            "Ragú de Ternera con Puré": ("Platos Calientes (Rotativo)", "Normal"),
            "Opción VIP: Lomo de Salmón con Salsa de Eneldo": ("Platos Calientes (Rotativo)", "VIP"), # Nombre largo
            "Lomo de Salmón con Salsa de Eneldo": ("Platos Calientes (Rotativo)", "VIP"), # Posible nombre corto?
            "Coeur Lion Camembert": ("Selecciones de Quesos", "Normal"),
            "Blue Castello": ("Selecciones de Quesos", "Normal"),
            "Agua Mineral (500ml)": ("Bebidas (No Alcohólicas)", "Normal"),
            "Refresco Cola (Lata)": ("Bebidas (No Alcohólicas)", "Normal"),
            "Pan dulce de Nuez": ("Snacks y Panadería", "Normal"),
            "Papitas Sabor Original (Bolsa Individual)": ("Snacks y Panadería", "Normal")
        }
        print(t("load_models_success"))
        return trained_models, model_feature_list, info_productos
    except FileNotFoundError:
         st.error(f"CRITICAL ERROR: Model files not found. Ensure '{MODEL_FILE.name}' and '{FEATURES_FILE.name}' exist.")
         st.stop() # Detiene si faltan archivos
    except Exception as e:
        st.error(f"{t('load_models_error')} {e}")
        st.stop() # Detiene si hay otro error


# --- 4. FUNCIONES DE LÓGICA DE NEGOCIO (Con Status_Key) ---

# --- fetch_inventory_dashboard_data AHORA depende del idioma ---
# Quitamos @st.cache_data para asegurar que siempre use el idioma actual
# @st.cache_data(ttl=300)
def fetch_inventory_dashboard_data(_engine, lang): # Recibe el idioma
    # (Consulta SQL sin cambios)
    sql_query = text(""" SELECT P.Producto_ID, P.Nombre AS Nombre_Producto, CP.Nombre AS Nombre_Categoria, L.Lote_ID, L.Numero_Lote, L.Fecha_Caducidad, L.Cantidad_Inicial, COALESCE(Agg.Total_Consumido, 0) AS Total_Consumido, (L.Cantidad_Inicial - COALESCE(Agg.Total_Consumido, 0)) AS Cantidad_Actual FROM LOTE_PRODUCTO AS L JOIN PRODUCTO AS P ON L.Producto_ID = P.Producto_ID JOIN CATEGORIA_PRODUCTO AS CP ON P.Categoria_ID = CP.Categoria_ID LEFT JOIN ( SELECT Lote_ID, SUM(COALESCE(Cantidad_Consumida, 0)) AS Total_Consumido FROM SERVICIO_LOTE_VUELO GROUP BY Lote_ID ) AS Agg ON L.Lote_ID = Agg.Lote_ID ORDER BY L.Fecha_Caducidad ASC; """)
    inventory_list = []; today = datetime.date.today()
    current_translations = translations.get(lang, translations['es']) # Obtiene traducciones para el idioma actual
    try:
        with _engine.connect() as conn:
            result = conn.execute(sql_query)
            for row in result:
                item = dict(row._mapping); exp_date = item['Fecha_Caducidad']
                dias_restantes = (exp_date - today).days; item['Dias_Restantes'] = dias_restantes
                # --- Status_Key FIJA y Estado Traducido (usando current_translations) ---
                if dias_restantes <= 0:
                    item['Status_Key'] = 'critical'
                    item['Estado'] = current_translations.get('status_critical', '[status_critical]')
                elif dias_restantes <= 3:
                    item['Status_Key'] = 'warning'
                    item['Estado'] = current_translations.get('status_warning', '[status_warning]')
                elif dias_restantes <= 7:
                    item['Status_Key'] = 'attention'
                    item['Estado'] = current_translations.get('status_attention', '[status_attention]')
                else:
                    item['Status_Key'] = 'optimal'
                    item['Estado'] = current_translations.get('status_optimal', '[status_optimal]')
                # --- Fin Status_Key ---
                item['Fecha_Caducidad'] = exp_date.isoformat(); inventory_list.append(item)
        return pd.DataFrame(inventory_list)
    except Exception as e:
        st.error(f"{t('error_querying_inventory')} {e}"); return pd.DataFrame()

# @st.cache_data(ttl=300) # También quitamos cache aquí por si acaso
def calculate_historical_consumption(_engine, analysis_window_days=30):
    # (Sin cambios necesarios aquí)
    sql_query = text(f""" SELECT P.Producto_ID, P.Nombre AS Nombre_Producto, SUM(SLV.Cantidad_Consumida) AS Total_Consumido FROM SERVICIO_LOTE_VUELO AS SLV JOIN VUELO AS V ON SLV.Vuelo_ID = V.Vuelo_ID JOIN LOTE_PRODUCTO AS LP ON SLV.Lote_ID = LP.Lote_ID JOIN PRODUCTO AS P ON LP.Producto_ID = P.Producto_ID WHERE V.Fecha_Salida >= CURDATE() - INTERVAL {analysis_window_days} DAY AND SLV.Cantidad_Consumida IS NOT NULL GROUP BY P.Producto_ID, P.Nombre; """)
    try:
        df = pd.read_sql(sql_query, _engine)
        if df.empty: return pd.DataFrame(columns=['Producto_ID', 'Nombre_Producto', 'Avg_Diario', 'Avg_Semanal'])
        df['Avg_Diario'] = df['Total_Consumido'] / analysis_window_days
        df['Avg_Semanal'] = df['Avg_Diario'] * 7
        return df
    except Exception as e:
        st.error(f"{t('error_calculating_consumption')} {e}"); return pd.DataFrame(columns=['Producto_ID', 'Nombre_Producto', 'Avg_Diario', 'Avg_Semanal'])

# @st.cache_data(ttl=300) # Quitamos cache aquí
def fetch_recommendations(_engine, lang): # Recibe idioma
    df_inventory = fetch_inventory_dashboard_data(_engine, lang) # Pasa idioma
    df_consumption = calculate_historical_consumption(_engine)
    if df_inventory.empty: return []
    current_translations = translations.get(lang, translations['es']) # Traducciones actuales
    recommendations = []; df_lotes_activos = df_inventory[df_inventory['Cantidad_Actual'] > 0]
    for _, lote in df_lotes_activos.iterrows():
        dias = lote['Dias_Restantes']; qty = lote['Cantidad_Actual']
        # Usa current_translations para generar textos
        if dias <= 0: recommendations.append({
                "Prioridad": current_translations.get('prio_high', '[prio_high]'), "Icono": "🔴", "Estado": "error",
                "Tipo": current_translations.get('rec_type_expired', '[rec_type_expired]'), "Producto": lote['Nombre_Producto'], "Lote": lote['Numero_Lote'],
                "Metrica": current_translations.get('rec_metric_expired', '[rec_metric_expired]').format(qty=qty, days=abs(dias)),
                "Accion": current_translations.get('rec_action_expired', '[rec_action_expired]')
            })
        elif 0 < dias <= 3: recommendations.append({
                "Prioridad": current_translations.get('prio_high', '[prio_high]'), "Icono": "🟠", "Estado": "error",
                "Tipo": current_translations.get('rec_type_waste_risk', '[rec_type_waste_risk]'), "Producto": lote['Nombre_Producto'], "Lote": lote['Numero_Lote'],
                "Metrica": current_translations.get('rec_metric_expiring', '[rec_metric_expiring]').format(qty=qty, days=dias),
                "Accion": current_translations.get('rec_action_expiring', '[rec_action_expiring]')
            })
    df_stock_total = df_lotes_activos.groupby('Producto_ID').agg(Stock_Total=('Cantidad_Actual', 'sum'), Nombre_Producto=('Nombre_Producto', 'first')).reset_index()
    if not df_consumption.empty:
        df_product_analysis = pd.merge(df_stock_total, df_consumption, on='Producto_ID', how='left')
        df_product_analysis['Avg_Semanal'] = df_product_analysis['Avg_Semanal'].fillna(0)
        for _, prod in df_product_analysis.iterrows():
            stock = prod['Stock_Total']; consumo_sem = prod['Avg_Semanal']
            if consumo_sem > 0 and stock < (consumo_sem * 0.5): recommendations.append({
                    "Prioridad": current_translations.get('prio_medium', '[prio_medium]'), "Icono": "🟡", "Estado": "warning",
                    "Tipo": current_translations.get('rec_type_stockout_risk', '[rec_type_stockout_risk]'), "Producto": prod['Nombre_Producto_x'],
                    "Lote": current_translations.get('rec_lote_all', '[rec_lote_all]'),
                    "Metrica": current_translations.get('rec_metric_stockout', '[rec_metric_stockout]').format(stock=stock, consumo=consumo_sem),
                    "Accion": current_translations.get('rec_action_stockout', '[rec_action_stockout]')
                })
    def sort_key(r): # La clave de orden ahora debe usar inglés fijo o índices numéricos
        prio_map = {current_translations.get('prio_high', 'High'): 0, current_translations.get('prio_medium', 'Medium'): 1, current_translations.get('prio_low', 'Low'): 2}; dias = 999
        # Simplificar la extracción de días si el formato traducido varía mucho
        try:
             # Intenta buscar un número seguido de "días" o "days"
             match = re.search(r'(\d+)\s+(days|días)', r["Metrica"])
             if match:
                 dias = int(match.group(1))
                 if "expired" in r["Metrica"] or "caducados" in r["Metrica"]:
                     dias = -dias # Hacer negativo si es 'hace X días'
        except:
            pass # Mantener dias=999 si falla la extracción
        return (prio_map.get(r["Prioridad"], 9), dias)

    # Importar re al inicio del script si usas re.search
    import re
    recommendations.sort(key=sort_key)
    return recommendations


def run_prediction_logic(flight_data, models, features, product_map):
    # (Sin cambios necesarios aquí)
    predicciones = {}
    # ... (resto de la función) ...
    for nombre_producto, modelo_especifico in models.items():
        try:
            if nombre_producto not in product_map: continue
            categoria, tipo_especial = product_map[nombre_producto]
            datos_completos = flight_data.copy()
            datos_completos['Nombre_Categoria'] = categoria; datos_completos['Tipo_Especial'] = tipo_especial
            if 'Aerolinea' in datos_completos: datos_completos['Nombre_Aerolinea'] = datos_completos.pop('Aerolinea')
            df_nuevo = pd.DataFrame([datos_completos])
            df_procesado = pd.get_dummies(df_nuevo); df_procesado = df_procesado.reindex(columns=features, fill_value=0)
            prediccion = modelo_especifico.predict(df_procesado); unidades = max(0, int(prediccion[0]))
            predicciones[nombre_producto] = round(unidades)
        except KeyError as e: print(f"Error Key (run_prediction_logic): Prod '{nombre_producto}' no mapeado. {e}"); predicciones[nombre_producto] = -1
        except Exception as e: print(f"Error prediciendo '{nombre_producto}': {e}"); predicciones[nombre_producto] = -1
    df_resultados = pd.DataFrame.from_dict(predicciones, orient='index', columns=['Demanda_Base'])
    df_resultados = df_resultados[df_resultados['Demanda_Base'] >= 0]
    return df_resultados


# --- 5. DATOS PARA LOS MENÚS DESPLEGABLES ---
# (Sin cambios)
LISTA_AEROLINEAS = ['LATAM Airlines', 'Qatar Airways', 'Iberia Airlines', 'EasyJet', 'Lufthansa', 'United Airlines', 'Delta Air Lines', 'Virgin Atlantic', 'Air Europa', 'T\'way Air', 'Japan Airlines', 'Aeroméxico', 'Avianca', 'Aeromar', 'Aerolíneas Argentinas']
LISTA_LOCALIDADES = ['Santiago, Chile', 'Doha, Catar', 'Madrid, España', 'Londres, Reino Unido', 'Frankfurt, Alemania', 'Nueva York, EEUU', 'Ciudad de México, México', 'Tokio, Japón']
LISTA_DIAS = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
LISTA_HORA_DIA = ['Mañana', 'Tarde', 'Noche']
LISTA_TEMPORADA = ['Baja', 'Media', 'Alta']
LISTA_CLIMA = ['Soleado', 'Lluvioso', 'Nevado', 'Nublado', 'Tormenta']
LISTA_TRAYECTO = ['Nacional', 'Internacional']

# --- 6. LÓGICA PRINCIPAL DE LA APLICACIÓN (Con Status_Key y Estilos Simplificados) ---
def main():
    # --- Selector de Idioma ---
    st.sidebar.selectbox( t('sidebar_lang_select'), options=['es', 'en'], format_func=lambda x: "Español" if x == 'es' else "English", key='lang' )
    # Obtener idioma actual DESPUÉS del selector
    current_lang = st.session_state.get('lang', 'es')

    engine = get_db_engine(); model_assets = load_model_assets()
    if not engine: st.error(t("critical_db_error")); return
    if model_assets is None or model_assets[0] is None or model_assets[1] is None: st.error(t("critical_model_error")); st.stop()
    trained_models, model_feature_list, info_productos = model_assets
    if not trained_models: st.sidebar.warning(t("models_not_trained_warning"))

    st.sidebar.title(t("sidebar_title"))
    page_options = { "📊 Panel Principal": "dashboard_title", "💡 Recomendaciones": "recommendations_title", "✈️ Predicción de Consumo": "forecast_title", "📋 Manifesto de Carga": "manifest_title", "🚨 Auditoría de Lotes": "audit_title" }
    page_keys = list(page_options.keys())
    page = st.sidebar.radio( t("sidebar_prompt"), page_keys, format_func=lambda key: t(page_options[key]) )

    # ===================== PÁGINA 1: PANEL PRINCIPAL =====================
    if page == "📊 Panel Principal":
        st.title(t("dashboard_title"))
        st.markdown(t("dashboard_subtitle"))
        # Pasa el idioma actual a la función
        df_inventory_full = fetch_inventory_dashboard_data(engine, current_lang)

        if df_inventory_full.empty: st.warning(t("no_inventory_data_warning")); return

        # Filtra usando Status_Key (columna interna fija)
        df_activos = df_inventory_full[(df_inventory_full['Cantidad_Actual'] > 0)].copy() # Mostrar todos activos, incl. críticos con stock

        if df_activos.empty: st.info(t("no_active_lots_found"));
        else:
            total_items_actuales = df_activos['Cantidad_Actual'].sum()
            total_lotes_activos = len(df_activos)
            lotes_optimos = len(df_activos[df_activos['Status_Key'] == 'optimal'])
            lotes_en_riesgo = len(df_activos[df_activos['Status_Key'].isin(['critical', 'warning', 'attention'])]) # Usa claves internas

            st.header(t("dashboard_metrics_header"))
            col1, col2, col3, col4 = st.columns(4)
            col1.metric(t("metric_total_inventory"), f"{total_items_actuales:,.0f}")
            col2.metric(t("metric_active_lots"), f"{total_lotes_activos:,.0f}")
            col3.metric(t("metric_optimal_lots"), f"{lotes_optimos:,.0f}")
            col4.metric(t("metric_risk_lots"), f"{lotes_en_riesgo:,.0f}", delta=t("metric_risk_delta").format(count=lotes_en_riesgo), delta_color="inverse")
            st.divider()
            st.header(t("dashboard_viz_header"))

            # Agrupa por Status_Key para lógica, usa Estado (ya traducido) para mostrar
            df_estado_grupo = df_activos.groupby('Status_Key', observed=True).agg(Conteo=('Status_Key', 'count'), Estado_Display=('Estado', 'first')).reset_index()

            df_categoria_grupo = df_activos.groupby('Nombre_Categoria', observed=True).agg(Stock_Total=('Cantidad_Actual', 'sum')).reset_index()

            col_graf1, col_graf2 = st.columns(2)
            with col_graf1:
                st.markdown("##### " + t("pie_chart_title"))
                # Mapeo fijo de Status_Key a color
                color_map = STATUS_KEY_COLOR_MAP # Usa el mapa global
                domain_presente_keys = df_estado_grupo['Status_Key'].tolist()
                range_presente = [color_map.get(key, color_map['default']) for key in domain_presente_keys]

                if df_estado_grupo.empty or not domain_presente_keys: st.info("No data for status distribution chart.")
                else:
                    try:
                        pie_chart = alt.Chart(df_estado_grupo).mark_arc(outerRadius=120).encode(
                            theta=alt.Theta("Conteo:Q", stack=True),
                            # Color usa Status_Key (fijo), Leyenda/Tooltip usan Estado_Display (traducido)
                            color=alt.Color("Status_Key:N", scale=alt.Scale(domain=domain_presente_keys, range=range_presente), legend=None),
                            order=alt.Order("Conteo:Q", sort="descending"),
                            tooltip=[alt.Tooltip("Estado_Display:N", title=t('col_status')), alt.Tooltip("Conteo:Q", title="Count")]
                        ).properties(
                             # Añade leyenda manualmente basada en Estado_Display
                             # Esto es más complejo en Altair, podríamos omitirla o simplificarla
                        )
                        # Intenta añadir leyenda basada en Estado_Display
                        legend = alt.Chart(df_estado_grupo).mark_point().encode(
                            y=alt.Y('Estado_Display:N', axis=alt.Axis(orient="right", title=t("pie_chart_legend"))),
                            color=alt.Color('Status_Key:N', scale=alt.Scale(domain=domain_presente_keys, range=range_presente), legend=None)
                        )

                        # Muestra gráfica principal (sin leyenda combinada por simplicidad ahora)
                        st.altair_chart(pie_chart, use_container_width=True)
                        # Podrías mostrar la leyenda separada: st.altair_chart(legend, use_container_width=True)

                    except Exception as e: st.error(f"Error displaying pie chart: {e}")
            with col_graf2:
                st.markdown("##### " + t("bar_chart_title"))
                if df_categoria_grupo.empty: st.info(t("no_inventory_data_warning"))
                else:
                    bar_chart = alt.Chart(df_categoria_grupo).mark_bar().encode(x=alt.X('Nombre_Categoria:N', title=t("bar_chart_x_axis"), sort='-y'), y=alt.Y('Stock_Total:Q', title=t("bar_chart_y_axis")), color='Nombre_Categoria:N', tooltip=['Nombre_Categoria', 'Stock_Total']).interactive()
                    st.altair_chart(bar_chart, use_container_width=True)
            st.divider()
            st.header(t("dashboard_table_header"))
            st.markdown(t("dashboard_table_subtitle"))

            # --- ESTILO CORREGIDO V10 ---
            # Función de estilo basada en Status_Key FIJA
            def style_by_status_key(status_key):
                color = STATUS_KEY_COLOR_MAP.get(status_key, STATUS_KEY_COLOR_MAP['default'])
                return f'color: {color}; font-weight: bold;'

            # Prepara el DataFrame para mostrar (incluye Status_Key y Estado traducido)
            columnas_a_mostrar = ['Estado', 'Dias_Restantes', 'Nombre_Producto', 'Numero_Lote', 'Cantidad_Actual', 'Fecha_Caducidad', 'Status_Key']
            df_display_base = df_activos[[col for col in columnas_a_mostrar if col in df_activos.columns]].copy()

            # Renombrar columnas para visualización
            df_display_renamed = df_display_base.rename(columns={
                 'Estado': t('col_status'), 'Dias_Restantes': t('col_days_remaining'), 'Nombre_Producto': t('col_product'),
                 'Numero_Lote': t('col_lot_code'), 'Cantidad_Actual': t('col_quantity'), 'Fecha_Caducidad': t('col_expiration')
            })

            # Crea el Styler sobre el DataFrame RENOMBRADO
            styler = df_display_renamed.style

            # Aplica formato (opcional)
            styler = styler.format(subset=[t('col_quantity')], formatter="{:,.0f}")

            # Aplica estilo usando apply por fila, accediendo a Status_Key del df original
            def apply_style_to_row(row):
                 original_index = row.name # Índice de la fila en df_display_renamed
                 status_key = df_display_base.loc[original_index]['Status_Key'] # Busca Status_Key en df original
                 style = style_by_status_key(status_key)
                 # Devuelve lista de estilos para TODAS las columnas, aplicando solo a las deseadas
                 return [style if col_name in [t('col_status'), t('col_days_remaining')] else '' for col_name in df_display_renamed.columns]

            styler = styler.apply(apply_style_to_row, axis=1) # Aplica estilo POR FILA

            # Selecciona las columnas a mostrar (traducidas) EXCLUYENDO Status_Key
            columnas_finales_traducidas = [t('col_status'), t('col_days_remaining'), t('col_product'), t('col_lot_code'), t('col_quantity'), t('col_expiration')]
            st.dataframe(styler,
                         column_order=[col for col in columnas_finales_traducidas if col in df_display_renamed.columns],
                         column_config={'Status_Key': None} if 'Status_Key' in df_display_base.columns else None, # Oculta la columna Status_Key
                         use_container_width=True)
            # --- FIN ESTILO CORREGIDO V10 ---


    # ===================== PÁGINA 2: RECOMENDACIONES =====================
    elif page == "💡 Recomendaciones":
        current_lang = st.session_state.get('lang', 'es') # Obtiene idioma
        st.title(t("recommendations_title"))
        st.markdown(t("recommendations_subtitle"))
        # Usamos t() para el label del botón
        if st.button(t("refresh_recommendations_button")):
            # Limpiamos caches relevantes si es necesario (fetch_recommendations y fetch_inventory_dashboard_data)
            # st.cache_data.clear() # Limpia TODA la cache de @st.cache_data si es necesario
            # O podrías intentar limpiar funciones específicas si las vuelves a cachear
            fetch_recommendations.clear()
            fetch_inventory_dashboard_data.clear()
            st.rerun()
        with st.spinner(t("spinner_generating")):
             recommendations = fetch_recommendations(engine, current_lang) # Pasa idioma
        if not recommendations:
            st.success(t("all_clear_no_recommendations"))
        else:
            alta = [r for r in recommendations if r['Prioridad'] == t('prio_high')]
            media = [r for r in recommendations if r['Prioridad'] == t('prio_medium')]

            if alta:
                st.subheader(t("recommendations_prio_high"))
                for r in alta:
                    # --- CORRECCIÓN DE INDENTACIÓN ---
                    with st.status(label=f"**{r['Icono']} {r['Tipo']}:** {r['Producto']}", state="error"):
                        st.markdown(f"**Lote:** {r['Lote']}")
                        st.markdown(f"**Metric:** {r['Metrica']}")
                        st.markdown(f"**Action:** {r['Accion']}")
                    # --- FIN CORRECCIÓN ---
            if media:
                st.subheader(t("recommendations_prio_medium"))
                for r in media:
                     # --- CORRECCIÓN DE INDENTACIÓN ---
                    with st.status(label=f"**{r['Icono']} {r['Tipo']}:** {r['Producto']}", state="warning"):
                        st.markdown(f"**Lote:** {r['Lote']}")
                        st.markdown(f"**Metric:** {r['Metrica']}")
                        st.markdown(f"**Action:** {r['Accion']}")

    # ===================== PÁGINA 3: PREDICCIÓN DE CONSUMO =====================
    elif page == "✈️ Predicción de Consumo":
        st.title(t("forecast_title")); st.markdown(t("forecast_subtitle"))
        results_placeholder = st.empty()
        with st.form(key="prediction_form"):
             col1, col2 = st.columns(2)
             # ... (Inputs del formulario traducidos con t()) ...
             with col1: st.subheader(t("form_flight_info")); num_pasajeros = st.number_input(t("form_passengers"), 1, 500, 150); aerolinea = st.selectbox(t("form_airline"), LISTA_AEROLINEAS, 11); distancia_km = st.number_input(t("form_distance"), 100, 20000, 1500); tipo_trayecto = st.selectbox(t("form_route_type"), LISTA_TRAYECTO); capacidad_avion = st.number_input(t("form_aircraft_capacity"), 50, 500, 180)
             with col2: st.subheader(t("form_flight_context")); hora_dia = st.selectbox(t("form_time_day"), LISTA_HORA_DIA); dia_semana = st.selectbox(t("form_day_week"), LISTA_DIAS, 4); temporada = st.selectbox(t("form_season"), LISTA_TEMPORADA, 2); condicion_clima = st.selectbox(t("form_weather"), LISTA_CLIMA); localidad_salida = st.selectbox(t("form_departure"), LISTA_LOCALIDADES, 6); localidad_llegada = st.selectbox(t("form_arrival"), LISTA_LOCALIDADES, 2)
             submit_button = st.form_submit_button(label=t("form_predict_button"))
        if submit_button:
             if not trained_models: results_placeholder.error(t("forecast_error_no_models"))
             else:
                 with st.spinner(t("spinner_calculating")):
                     datos_vuelo_futuro = {"Num_Pasajeros": num_pasajeros, "Aerolinea": aerolinea, "Distancia_KM": distancia_km, "Tipo_Trayecto": tipo_trayecto, "Capacidad_Max_Avion": capacidad_avion, "Hora_Dia": hora_dia, "Dia_Semana": dia_semana, "Temporada": temporada, "Condicion_Climatica": condicion_clima, "Localidad_Salida": localidad_salida, "Localidad_Llegada": localidad_llegada}
                     # Asegúrate que info_productos esté cargado correctamente
                     if info_productos:
                         df_resultados = run_prediction_logic(datos_vuelo_futuro, trained_models, model_feature_list, info_productos)
                     else:
                         st.error("Error: Product information map not loaded.") # Error si falta info_productos
                         df_resultados = pd.DataFrame() # DataFrame vacío

                 with results_placeholder.container():
                     st.subheader(t("forecast_results_header"))
                     if df_resultados.empty: st.info(t("forecast_no_consumption"))
                     else: st.dataframe(df_resultados.rename(columns={'Demanda_Base': t('col_predicted_demand')}))


    # ===================== PÁGINA 4: MANIFESTO DE CARGA =====================
    elif page == "📋 Manifesto de Carga":
        current_lang = st.session_state.get('lang', 'es') # Obtiene idioma
        st.title(t("manifest_title")); st.markdown(t("manifest_subtitle"))
        if 'manifesto_df' not in st.session_state: st.session_state.manifesto_df = pd.DataFrame(); st.session_state.manifesto_lotes_asignados = {}
        st.header(t("manifest_step1_header"))
        with st.form(key="manifesto_form"):
             # ... (Inputs del formulario traducidos con t()) ...
             col1, col2 = st.columns(2)
             with col1: m_num_pasajeros = st.number_input(t("form_passengers"), 1, 500, 150); m_aerolinea = st.selectbox(t("form_airline"), LISTA_AEROLINEAS, 11); m_distancia_km = st.number_input(t("form_distance"), 100, 20000, 1500); m_tipo_trayecto = st.selectbox(t("form_route_type"), LISTA_TRAYECTO)
             with col2: m_capacidad_avion = st.number_input(t("form_aircraft_capacity"), 50, 500, 180); m_hora_dia = st.selectbox(t("form_time_day"), LISTA_HORA_DIA); m_dia_semana = st.selectbox(t("form_day_week"), LISTA_DIAS, 4); m_temporada = st.selectbox(t("form_season"), LISTA_TEMPORADA, 2)
             m_localidad_salida = st.selectbox(t("form_departure"), LISTA_LOCALIDADES, 6); m_localidad_llegada = st.selectbox(t("form_arrival"), LISTA_LOCALIDADES, 2); m_condicion_clima = st.selectbox(t("form_weather"), LISTA_CLIMA)
             manifesto_submit = st.form_submit_button(label=t("manifest_generate_button"))
        if manifesto_submit:
             with st.spinner(t("spinner_generating") + "..."):
                 datos_vuelo = {"Num_Pasajeros": m_num_pasajeros, "Aerolinea": m_aerolinea, "Distancia_KM": m_distancia_km, "Tipo_Trayecto": m_tipo_trayecto, "Capacidad_Max_Avion": m_capacidad_avion, "Hora_Dia": m_hora_dia, "Dia_Semana": m_dia_semana, "Temporada": m_temporada, "Condicion_Climatica": m_condicion_clima, "Localidad_Salida": m_localidad_salida, "Localidad_Llegada": m_localidad_llegada}
                 if info_productos: # Chequea si info_productos existe
                     df_demanda = run_prediction_logic(datos_vuelo, trained_models, model_feature_list, info_productos)
                 else:
                     st.error("Error: Product information map not loaded for manifest."); df_demanda = pd.DataFrame()

                 if df_demanda.empty: st.error(t("manifest_error_no_demand")); st.session_state.manifesto_df = pd.DataFrame(); st.session_state.manifesto_lotes_asignados = {}
                 else:
                     df_demanda['Buffer (5%)'] = (df_demanda['Demanda_Base'] * 0.05).apply(np.ceil)
                     df_demanda['Quantity_Final'] = df_demanda['Demanda_Base'] + df_demanda['Buffer (5%)']
                     df_manifesto = df_demanda.astype(int)[['Demanda_Base', 'Buffer (5%)', 'Quantity_Final']].sort_values(by='Quantity_Final', ascending=False)
                     st.session_state.manifesto_df = df_manifesto
                     df_inventory = fetch_inventory_dashboard_data(engine, current_lang) # Pasa idioma
                     # Usa Status_Key para filtrar
                     df_inv_activos = df_inventory[(df_inventory['Cantidad_Actual'] > 0) & (df_inventory['Status_Key'] != 'critical')]
                     lotes_asignados_dict = {}; inventario_temporal = df_inv_activos.copy()
                     for producto, row in df_manifesto.iterrows():
                         cantidad_necesaria = row['Quantity_Final']
                         lotes_para_producto = []; lotes_disponibles = inventario_temporal[inventario_temporal['Nombre_Producto'] == producto].sort_values(by='Fecha_Caducidad')
                         for _, lote in lotes_disponibles.iterrows():
                             if cantidad_necesaria <= 0: break
                             needed = int(cantidad_necesaria); available = int(lote['Cantidad_Actual'])
                             cantidad_a_tomar = min(needed, available)
                             if cantidad_a_tomar > 0:
                                 lotes_para_producto.append({'Numero_Lote': lote['Numero_Lote'], 'Cantidad_Tomada': cantidad_a_tomar, 'Fecha_Caducidad': lote['Fecha_Caducidad'], 'Estado_Lote': lote['Estado']}) # Guarda 'Estado' (traducido)
                                 inventario_temporal.loc[lote.name, 'Cantidad_Actual'] -= cantidad_a_tomar
                                 cantidad_necesaria -= cantidad_a_tomar
                         lotes_asignados_dict[producto] = lotes_para_producto
                         if cantidad_necesaria > 0: st.warning(t("manifest_insufficient_stock_warning").format(prod=producto, qty=cantidad_necesaria))
                     st.session_state.manifesto_lotes_asignados = lotes_asignados_dict

        if not st.session_state.manifesto_df.empty:
             st.divider(); st.header(t("manifest_step2_header"))
             col_man, col_inv = st.columns([0.6, 0.4])
             with col_man:
                 st.subheader(t("manifest_left_header")); st.markdown(t("manifest_left_subtitle"))
                 df_manifest = st.session_state.manifesto_df; lotes_asignados = st.session_state.manifesto_lotes_asignados
                 for producto, row in df_manifest.iterrows():
                     lotes_del_producto = lotes_asignados.get(producto, [])
                     titulo_expander = f"📦 **{producto}**"
                     with st.expander(titulo_expander, expanded=True):
                         st.markdown(f"{t('manifest_total_quantity')} <span style='font-size: 1.5em; font-weight: bold;'>{row['Quantity_Final']}</span>", unsafe_allow_html=True)
                         st.markdown(f"({t('manifest_base_demand')}: `{row['Demanda_Base']}` | {t('manifest_buffer')}: `{row['Buffer (5%)']}`)")
                         st.markdown("---")
                         if lotes_del_producto:
                             st.markdown(t("manifest_assigned_lots"))
                             for lote_info in lotes_del_producto: st.markdown(f"   - Lote `{lote_info['Numero_Lote']}` ({lote_info['Estado_Lote']}): {t('manifest_take_qty')} `{lote_info['Cantidad_Tomada']}` ({t('manifest_expires')}: {lote_info['Fecha_Caducidad']})")
                         else: st.warning(f"   {t('manifest_no_lots_found')}")
             with col_inv:
                st.subheader(t("manifest_right_header")) # Usa t()
                st.markdown(t("manifest_right_subtitle")) # Usa t()

                # --- TABLAS DE DEBUG RESTAURADAS (con traducciones) ---
                current_lang = st.session_state.get('lang', 'es') # Necesitamos el idioma actual
                df_inventory = fetch_inventory_dashboard_data(engine, current_lang) # Pasa idioma
                # DEBUG 1: Muestra inventario completo (opcional, descomenta si lo necesitas)
                # st.write(t("manifest_debug_step1"), df_inventory)

                # DEBUG 2: Muestra inventario activo (filtrado por stock y no crítico)
                # Usa Status_Key para filtrar consistentemente
                df_inv_activos = df_inventory[(df_inventory['Cantidad_Actual'] > 0) & (df_inventory['Status_Key'] != 'critical')]
                st.write(t("manifest_debug_step2"), df_inv_activos)

                # DEBUG 3: Muestra qué productos necesita el manifiesto
                productos_en_manifiesto = st.session_state.manifesto_df.index.tolist() # Usa el df del estado
                st.write(t("manifest_debug_step3"), productos_en_manifiesto)

                # DEBUG 4: Muestra el inventario final filtrado antes de la tabla principal
                df_inv_filtrado = df_inv_activos[df_inv_activos['Nombre_Producto'].isin(productos_en_manifiesto)]
                #st.write(t("manifest_debug_step4"), df_inv_filtrado)
                # --- FIN TABLAS DE DEBUG RESTAURADAS ---

                # --- Tabla principal de inventario (sin cambios) ---
                st.dataframe(
                    df_inv_filtrado[['Estado', 'Nombre_Producto', 'Numero_Lote', 'Cantidad_Actual', 'Fecha_Caducidad']].rename(columns={
                         'Estado': t('col_status'), 'Nombre_Producto': t('col_product'), 'Numero_Lote': t('col_lot_code'),
                         'Cantidad_Actual': t('col_quantity'), 'Fecha_Caducidad': t('col_expiration')
                    }),
                    height=300, # Ajusta altura si es necesario con las tablas de debug
                    use_container_width=True
                )


    # ===================== PÁGINA 5: AUDITORÍA DE LOTES =====================
    elif page == "🚨 Auditoría de Lotes":
        current_lang = st.session_state.get('lang', 'es') # Obtiene idioma
        st.title(t("audit_title")); st.markdown(t("audit_subtitle"))
        if st.button(t("refresh_button")): st.cache_data.clear(); st.rerun() # Considera limpiar cache específica
        df_inventory_full = fetch_inventory_dashboard_data(engine, current_lang) # Pasa idioma
        if df_inventory_full.empty: st.info(t("no_lots_found"))
        else:
            # Función de estilo basada en Status_Key FIJA
            def style_by_status_key_audit(status_key):
                 color = STATUS_KEY_COLOR_MAP.get(status_key, STATUS_KEY_COLOR_MAP['default'])
                 return f'color: {color}; font-weight: bold;'

            # Prepara DataFrame base con Status_Key
            columnas_audit = ['Estado', 'Dias_Restantes', 'Nombre_Producto', 'Numero_Lote', 'Cantidad_Actual', 'Fecha_Caducidad', 'Status_Key']
            df_display_audit_base = df_inventory_full[[col for col in columnas_audit if col in df_inventory_full.columns]].copy()

            # Renombrar columnas ANTES de aplicar estilo
            df_display_audit_renamed = df_display_audit_base.rename(columns={
                'Estado': t('col_status'), 'Dias_Restantes': t('col_days_remaining'), 'Nombre_Producto': t('col_product'),
                'Numero_Lote': t('col_lot_code'), 'Cantidad_Actual': t('col_remaining_qty'), 'Fecha_Caducidad': t('col_expiration')
            })

            # Define qué columnas colorear (con nombres traducidos)
            cols_to_color_audit = [t('col_status'), t('col_days_remaining')]

            # Función para aplicar a filas, usa Status_Key original
            def apply_style_to_row_audit(row):
                 original_index = row.name
                 status_key = df_display_audit_base.loc[original_index]['Status_Key'] if 'Status_Key' in df_display_audit_base else None
                 style = style_by_status_key_audit(status_key) if status_key else ''
                 return [style if col_name in cols_to_color_audit else '' for col_name in df_display_audit_renamed.columns]

            styler_audit = df_display_audit_renamed.style.apply(apply_style_to_row_audit, axis=1)

            # Formato (opcional)
            styler_audit = styler_audit.format(subset=[t('col_remaining_qty')], formatter="{:,.0f}")

            # Selecciona y ordena columnas a mostrar (traducidas) EXCLUYENDO Status_Key
            columnas_finales_audit = [t('col_status'), t('col_days_remaining'), t('col_product'), t('col_lot_code'), t('col_remaining_qty'), t('col_expiration')]
            st.dataframe(styler_audit,
                         column_order=[col for col in columnas_finales_audit if col in df_display_audit_renamed.columns],
                         column_config={'Status_Key': None} if 'Status_Key' in df_display_audit_base.columns else None,
                         use_container_width=True)

if __name__ == "__main__":
    # Importar re aquí si usas la lógica de regex en fetch_recommendations
    import re
    main()
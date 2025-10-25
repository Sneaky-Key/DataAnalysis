import pandas as pd
import numpy as np
import joblib
from flask import Flask, request, jsonify
from flask_cors import CORS

# --- 1. Cargar los modelos guardados al iniciar ---
print("Cargando modelos desde el archivo...")
try:
    trained_models = joblib.load('modelos_comida.joblib')
    model_feature_list = joblib.load('lista_de_features.joblib')
    # Cargar el mapa de info_productos (de tu script anterior)
    # (Pega aquí tu diccionario 'info_productos' de la respuesta anterior)
    info_productos = {
        # --- DESAYUNO CALIENTE (CAT 401) ---
        "Salchicha de Pavo con Huevo Revuelto y Patata": ("Desayuno Caliente", "Normal"),
        "Ratatouille con Tostadas": ("Desayuno Caliente", "Vegetariano"),
        
        # --- ALMUERZO FRÍO (CAT 402) ---
        "Pollo con Ensalada de Patata y Espárragos": ("Almuerzo Frío", "Normal"),
        "Sándwich de pavo y queso": ("Almuerzo Frío", "Normal"),
        
        # --- PLATOS CALIENTES (ROTATIVO) (CAT 403) ---
        "Ragú de Ternera con Puré": ("Platos Calientes (Rotativo)", "Normal"),
        "Opción VIP: Lomo de Salmón con Salsa de Eneldo": ("Platos Calientes (Rotativo)", "VIP"),
        
        # --- SELECCIONES DE QUESOS (CAT 404) ---
        "Coeur Lion Camembert": ("Selecciones de Quesos", "Normal"),
        "Blue Castello": ("Selecciones de Quesos", "Normal"),
        
        # --- BEBIDAS (NO ALCOHÓLICAS) (CAT 405) ---
        "Agua Mineral (500ml)": ("Bebidas (No Alcohólicas)", "Normal"),
        "Refresco Cola (Lata)": ("Bebidas (No Alcohólicas)", "Normal"),
        
        # --- SNACKS Y PANADERÍA (CAT 406) ---
        "Pan dulce de Nuez": ("Snacks y Panadería", "Normal"),
        "Papitas Sabor Original (Bolsa Individual)": ("Snacks y Panadería", "Normal")
    }
    print("¡Modelos y datos de productos cargados!")
except FileNotFoundError:
    print("ERROR: No se encontraron los archivos .joblib. Asegúrate de correr 'train.py' primero.")
    exit()

# --- 2. Configurar la aplicación Flask (la "cocina") ---
app = Flask(__name__)
# CORS permite que tu Frontend (ej. localhost:3000) hable con tu Backend (ej. localhost:5000)
CORS(app) 

# --- 3. Crear el "endpoint" de predicción ---
# Esta es la URL que tu Frontend llamará (ej. http://localhost:5000/predict)
@app.route('/predict', methods=['POST'])
def predict_flight():
    # 1. Recibir los datos del vuelo desde el Frontend (vienen en JSON)
    try:
        datos_vuelo_futuro = request.get_json()
        
        # --- CAMBIO 1: VALIDACIÓN ACTUALIZADA ---
        # Validar que los datos *nuevos* estén
        campos_requeridos = ['Num_Pasajeros', 'Aerolinea', 'Distancia_KM', 'Tipo_Trayecto', 'Hora_Dia']
        if not all(campo in datos_vuelo_futuro for campo in campos_requeridos):
            return jsonify({'error': 'Faltan datos clave del vuelo (Pasajeros, Aerolinea, Distancia, Trayecto, Hora)'}), 400

    except Exception as e:
        return jsonify({'error': f'Error al leer JSON: {str(e)}'}), 400

    print(f"Recibida petición de predicción para: {datos_vuelo_futuro}")
    
    predicciones_finales = {}
    
    # 2. Iterar sobre todos los productos que nuestro modelo conoce
    for nombre_producto, modelo_especifico in trained_models.items():
        
        try:
            # 3. Combinar datos del vuelo + datos del producto (del mapa)
            categoria, tipo_especial = info_productos[nombre_producto]
            
            datos_completos_producto = datos_vuelo_futuro.copy()
            datos_completos_producto['Nombre_Categoria'] = categoria
            datos_completos_producto['Tipo_Especial'] = tipo_especial
            
            # --- CAMBIO 2: RENOMBRAR LA CLAVE ---
            # El modelo entrenó con 'Nombre_Aerolinea', pero el frontend envía 'Aerolinea'.
            # Las renombramos para que coincidan.
            if 'Aerolinea' in datos_completos_producto:
                datos_completos_producto['Nombre_Aerolinea'] = datos_completos_producto.pop('Aerolinea')
            
            # 4. Procesar los datos (pd.get_dummies + reindex)
            nuevo_vuelo_df = pd.DataFrame([datos_completos_producto])
            nuevo_vuelo_procesado = pd.get_dummies(nuevo_vuelo_df)
            
            # ¡CRÍTICO! Usamos la lista guardada para asegurar 100% de coincidencia
            # Esta lista 'model_feature_list' fue creada por el NUEVO train.py,
            # así que ya espera todas las nuevas features.
            nuevo_vuelo_procesado = nuevo_vuelo_procesado.reindex(columns=model_feature_list, fill_value=0)
            
            # 5. ¡Predecir!
            prediccion = modelo_especifico.predict(nuevo_vuelo_procesado)
            unidades_necesarias = max(0, prediccion[0])
            
            # 6. Guardar el resultado
            predicciones_finales[nombre_producto] = round(unidades_necesarias)

        except KeyError as e:
            # Este error ocurre si 'info_productos' no está completo
            print(f"Error de Key: No se encontró '{nombre_producto}' en 'info_productos'.")
            predicciones_finales[nombre_producto] = -1 # Marcar como error
        except Exception as e:
            print(f"Error prediciendo '{nombre_producto}': {str(e)}")
            predicciones_finales[nombre_producto] = -1 # Marcar como error

    # 7. Devolver todas las predicciones al Frontend como JSON
    print("Enviando predicciones de vuelta al Frontend.")
    return jsonify(predicciones_finales)

# --- 4. Correr el servidor ---
if __name__ == '__main__':
    # Corre el servidor en el puerto 5000, accesible desde tu red
    app.run(host='0.0.0.0', port=5000, debug=True)
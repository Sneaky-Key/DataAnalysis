-- 1. Tabla: AEROPUERTO
-- Almacena la información de las localidades/latitudes de salida y llegada.
CREATE TABLE AEROPUERTO (
    Aeropuerto_ID INT PRIMARY KEY,
    Codigo_IATA CHAR(3) UNIQUE NOT NULL,
    Nombre VARCHAR(100) NOT NULL,
    Localidad VARCHAR(100) NOT NULL,
    Latitud DECIMAL(10, 6),
    Longitud DECIMAL(10, 6)
);

-- 2. Tabla: TIPO_AVION
-- Almacena los modelos de aeronaves.
CREATE TABLE TIPO_AVION (
    Tipo_Avion_ID INT PRIMARY KEY,
    Modelo VARCHAR(50) UNIQUE NOT NULL,
    Capacidad_Max INT NOT NULL
);

-- 3. Tabla: AEROLINEA
-- Almacena las aerolíneas y su asociación con gategroup (para seguimiento logístico).
CREATE TABLE AEROLINEA (
    Aerolinea_ID INT PRIMARY KEY,
    Nombre VARCHAR(100) UNIQUE NOT NULL,
    Codigo_IATA CHAR(2) UNIQUE NOT NULL,
    Asociacion_gategroup_Nota VARCHAR(255)
);

-- 4. Tabla: VUELO
-- Almacena la información principal de los 3000+ vuelos.
CREATE TABLE VUELO (
    Vuelo_ID INT PRIMARY KEY,
    Aerolinea_ID INT NOT NULL,
    Tipo_Avion_ID INT NOT NULL,
    Aeropuerto_Salida_ID INT NOT NULL,
    Aeropuerto_Llegada_ID INT NOT NULL,

    Fecha_Salida DATE NOT NULL,
    Hora_Salida_Programada TIME NOT NULL,
    Fecha_Llegada DATE NOT NULL,
    Hora_Llegada_Programada TIME NOT NULL,

    Tipo_Trayecto ENUM('Nacional', 'Internacional') NOT NULL,
    Distancia_KM INT NOT NULL,
    Num_Pasajeros INT NOT NULL,

    Hora_Dia ENUM('Mañana', 'Tarde', 'Noche') NOT NULL,
    Dia_Semana ENUM('Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo') NOT NULL,
    Temporada ENUM('Baja', 'Media', 'Alta') NOT NULL,
    Condicion_Climatica ENUM('Soleado', 'Lluvioso', 'Nevado', 'Nublado', 'Tormenta') NOT NULL,

    FOREIGN KEY (Aerolinea_ID) REFERENCES AEROLINEA(Aerolinea_ID),
    FOREIGN KEY (Tipo_Avion_ID) REFERENCES TIPO_AVION(Tipo_Avion_ID),
    FOREIGN KEY (Aeropuerto_Salida_ID) REFERENCES AEROPUERTO(Aeropuerto_ID),
    FOREIGN KEY (Aeropuerto_Llegada_ID) REFERENCES AEROPUERTO(Aeropuerto_ID)
);

-- 5. Tabla: CATEGORIA_PRODUCTO
-- Clasificación de los productos (menú, bebidas, snacks).
CREATE TABLE CATEGORIA_PRODUCTO (
    Categoria_ID INT PRIMARY KEY,
    Nombre VARCHAR(50) UNIQUE NOT NULL
);

-- 6. Tabla: PRODUCTO
-- Inventario de productos de catering de gategroup.
CREATE TABLE PRODUCTO (
    Producto_ID INT PRIMARY KEY,
    Categoria_ID INT NOT NULL,
    Nombre VARCHAR(100) NOT NULL,
    Tipo_Especial VARCHAR(100) COMMENT 'Ej: VIP, vegetariano, vegano, sin gluten',

    FOREIGN KEY (Categoria_ID) REFERENCES CATEGORIA_PRODUCTO(Categoria_ID)
);

-- 7. Tabla: LOTE_PRODUCTO
-- Gestión de lotes, esencial para el seguimiento de caducidad.
DROP TABLE IF EXISTS LOTE_PRODUCTO;
CREATE TABLE LOTE_PRODUCTO (
    Lote_ID INT PRIMARY KEY,
    Producto_ID INT NOT NULL,
    Numero_Lote VARCHAR(50) UNIQUE NOT NULL,
    Fecha_Caducidad DATE NOT NULL,
    Cantidad_Inicial INT NOT NULL,


    FOREIGN KEY (Producto_ID) REFERENCES PRODUCTO(Producto_ID)
);

-- 8. Tabla: SERVICIO_LOTE_VUELO
-- Relación de muchos a muchos para saber qué lote de producto fue cargado en qué vuelo y en qué cantidad.
-- Es la clave para la gestión de logística y caducidad.
DROP TABLE IF EXISTS SERVICIO_LOTE_VUELO;
CREATE TABLE SERVICIO_LOTE_VUELO (
    Servicio_Lote_ID INT PRIMARY KEY AUTO_INCREMENT,
    Vuelo_ID INT NOT NULL,
    Lote_ID INT NOT NULL,
    Cantidad_Cargada INT NOT NULL,
    Cantidad_Consumida INT, -- Puede ser NULL al momento de la carga, se llena post-vuelo.

    FOREIGN KEY (Vuelo_ID) REFERENCES VUELO(Vuelo_ID),
    FOREIGN KEY (Lote_ID) REFERENCES LOTE_PRODUCTO(Lote_ID),
    UNIQUE KEY uk_vuelo_lote (Vuelo_ID, Lote_ID)
);

-- 9. Vista: VISTA_LOGISTICA_VUELO
DROP VIEW IF EXISTS VISTA_LOGISTICA_VUELO;
CREATE VIEW VISTA_LOGISTICA_VUELO AS
SELECT
    V.Vuelo_ID,
    AER.Nombre AS Aerolinea,
    V.Num_Pasajeros,
    ASALIDA.Codigo_IATA AS Origen_IATA,
    ASALIDA.Localidad AS Origen_Localidad,
    ALLEGA.Codigo_IATA AS Destino_IATA,
    ALLEGA.Localidad AS Destino_Localidad,
    V.Fecha_Salida,
    V.Hora_Salida_Programada,
    V.Fecha_Llegada,
    V.Hora_Llegada_Programada,
    V.Dia_Semana,
    V.Temporada,
    V.Condicion_Climatica,

    -- Información de la Categoría (NUEVAS COLUMNAS)
    CP.Categoria_ID,
    CP.Nombre AS Nombre_Categoria,

    -- Información del Producto y Lote
    LP.Producto_ID,
    P.Nombre AS Nombre_Producto,
    LP.Lote_ID,
    LP.Numero_Lote,
    LP.Fecha_Caducidad,
    LP.Cantidad_Inicial AS Lote_Cantidad_Inicial,

    -- Información de la Carga y Consumo
    SLV.Cantidad_Cargada AS Cantidad_Subida_Al_Vuelo,
    (SLV.Cantidad_Cargada - COALESCE(SLV.Cantidad_Consumida, 0)) AS Cantidad_Sobrante_Del_Vuelo
FROM
    VUELO V
INNER JOIN
    AEROLINEA AER ON V.Aerolinea_ID = AER.Aerolinea_ID
INNER JOIN
    AEROPUERTO ASALIDA ON V.Aeropuerto_Salida_ID = ASALIDA.Aeropuerto_ID
INNER JOIN
    AEROPUERTO ALLEGA ON V.Aeropuerto_Llegada_ID = ALLEGA.Aeropuerto_ID
INNER JOIN
    SERVICIO_LOTE_VUELO SLV ON V.Vuelo_ID = SLV.Vuelo_ID
INNER JOIN
    LOTE_PRODUCTO LP ON SLV.Lote_ID = LP.Lote_ID
INNER JOIN
    PRODUCTO P ON LP.Producto_ID = P.Producto_ID
INNER JOIN
    CATEGORIA_PRODUCTO CP ON P.Categoria_ID = CP.Categoria_ID;

-- NOTA: La función COALESCE(SLV.Cantidad_Consumida, 0) asegura que si el consumo es NULL (no registrado aún),
-- la cantidad sobrante se calcule como la cantidad cargada.
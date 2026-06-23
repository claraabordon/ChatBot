# motor.py — Máquina de Estados para Bot Conversacional de WhatsApp
# Relevamiento Anual de Prestadores (ANEXO I)
# Versión: 4.1 - Refactorización Estructural Profunda
# - Validación por Padrón Oficial (PEDIR_ID)
# - Menú Inicial de Opciones (Paso 0.1) + Consulta Técnica (Paso 0.2)
# - Doble Afectación Personal (afectacion_agua + afectacion_cloacas)
# - Edición Final por Casilleros (Paso 25 Interactivo)

import json
import os
from persistencia import guardar_datos

# ============================================================================
# CONSTANTES Y CONFIGURACIÓN
# ============================================================================

PERFILES_PERSONAL = ["Profesionales", "Técnicos", "Administrativos", "Obreros", "Otros"]
TIPO_SERVICIO_AGUA_SOLO = 1
TIPO_SERVICIO_CLOACAS_SOLO = 2
TIPO_SERVICIO_AMBOS = 3

# Mapeo de casilleros para el resumen de edición (Paso 25)
CASILLEROS_EDICION = {
    "1": ("conexiones_agua", "Conexiones de agua residenciales/totales"),
    "2": ("habitantes_agua", "Población servida con red de agua"),
    "3": ("caudal_agua_m3dia", "Caudal diario de agua (m³/día)"),
    "4": ("macromedidores_operativos_agua", "Macro-medidores operativos"),
    "5": ("longitud_red_agua_km", "Longitud total red de agua (km)"),
    "6": ("capacidad_almacenamiento_m3", "Capacidad de almacenamiento (m³)"),
    "7": ("conexiones_cloacas", "Conexiones cloacales residenciales"),
    "8": ("conexiones_cloacas_com_ind", "Conexiones cloacales comerciales/industriales"),
    "9": ("habitantes_cloacas", "Población servida con red de cloacas"),
    "10": ("longitud_red_cloacas_km", "Longitud total red de cloacas (km)"),
    "11": ("caudal_cloacas_media", "Caudal diario cloacal (m³/día)"),
    "12": ("reclamos_falta_presion", "Reclamos por falta de presión de agua"),
    "13": ("reclamos_escape_calzada_vereda", "Reclamos por escapes/fugas de agua"),
    "14": ("reclamos_obstruccion_cloacal", "Reclamos por obstrucciones cloacales"),
    "15": ("cortes_servicio_falta_pago", "Cortes de servicio por falta de pago"),
    "16": ("poblacion_urbana_cloacas", "Población urbana estimada (Solo Cloacas)"),
}

# ============================================================================
# FUNCIONES DE CARGA Y VALIDACIÓN DE PADRÓN
# ============================================================================

def cargar_padron_oficial():
    """
    Carga el padrón oficial de prestadores desde el archivo JSON.
    Estructura esperada: {"ID_NUMERICO": "Nombre Oficial del Prestador"}
    Retorna: dict con el padrón o {} si no existe el archivo.
    """
    archivo = "padron_prestadores.json"
    if os.path.exists(archivo):
        try:
            with open(archivo, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    return {}

def validar_id_prestador(id_texto):
    """
    Valida que el ID existe en el padrón oficial.
    Retorna: (es_valido: bool, nombre_oficial: str o None)
    """
    try:
        # Intentar convertir a entero (ID numérico)
        id_numerico = str(int(id_texto.strip()))
        padron = cargar_padron_oficial()

        if id_numerico in padron:
            return True, padron[id_numerico]
        else:
            return False, None
    except ValueError:
        return False, None

def obtener_estado_prestador(id_prestador):
    """
    Verifica si un prestador ya completó el registro.
    Retorna: (existe: bool, estado: str)
    """
    archivo = "respuestas_prestadores.json"
    if os.path.exists(archivo):
        try:
            with open(archivo, "r", encoding="utf-8") as f:
                lista_datos = json.load(f)
                for registro in lista_datos:
                    if registro.get("id_prestador") == id_prestador:
                        estado = registro.get("estado_registro", "Incompleto")
                        return True, estado
        except (json.JSONDecodeError, IOError):
            pass
    return False, None

# ============================================================================
# INICIALIZACIÓN DE SESIÓN
# ============================================================================

def crear_sesion_nueva(telefono):
    """
    Crea un diccionario de sesión inicial para un prestador.
    Inicializa todos los campos requeridos con valores None y estado "Incompleto".
    El flujo OBLIGATORIAMENTE comienza en paso 0 (PEDIR_ID).
    """
    return {
        "telefono": telefono,
        "id_prestador": None,              # Será cargado en Paso 0
        "nombre_prestador": None,          # Será extraído del padrón en Paso 0
        "estado_registro": "Incompleto",
        "paso_actual": 0,                  # PEDIR_ID (Paso Inicial Obligatorio)
        "paso_personal_actual": None,      # dependencia -> contratados -> afectacion_agua -> afectacion_cloacas
        "perfil_personal_index": 0,        # Índice del perfil actual (0-4)
        "en_modo_edicion": False,          # Flag para detectar si venimos de edición en paso 25
        "paso_edicion_previo": None,       # Guarda el paso original antes de entrar en edición
        "bloqueado_por_completitud": False,  # Candado electrónico si ya completó
        "consulta_soporte": None,          # Almacena la consulta técnica del usuario

        # Datos básicos
        "localidad": None,
        "referente": None,
        "tipo_servicio": None,

        # Comercialización
        "agua_tarifado": None,
        "cloacas_tarifado": None,

        # Personal (diccionario anidado con doble afectación)
        "personal": {
            "Profesionales": {"dependencia": None, "contratados": None, "afectacion_agua": None, "afectacion_cloacas": None},
            "Técnicos": {"dependencia": None, "contratados": None, "afectacion_agua": None, "afectacion_cloacas": None},
            "Administrativos": {"dependencia": None, "contratados": None, "afectacion_agua": None, "afectacion_cloacas": None},
            "Obreros": {"dependencia": None, "contratados": None, "afectacion_agua": None, "afectacion_cloacas": None},
            "Otros": {"dependencia": None, "contratados": None, "afectacion_agua": None, "afectacion_cloacas": None},
        },

        # Infraestructura Agua
        "conexiones_agua": None,
        "habitantes_agua": None,
        "caudal_agua_m3dia": None,
        "tiene_fuente_captacion_compleja": None,
        "tiene_medidores_nuevos_año": None,
        "tiene_analisis_laboratorio_autocontrol": None,
        "tiene_balance_hidrico_mensual": None,
        "macromedidores_operativos_agua": None,
        "longitud_red_agua_km": None,
        "capacidad_almacenamiento_m3": None,

        # Infraestructura Cloacas
        "poblacion_urbana_cloacas": None,
        "conexiones_cloacas": None,
        "conexiones_cloacas_com_ind": None,
        "habitantes_cloacas": None,
        "longitud_red_cloacas_km": None,
        "caudal_cloacas_media": None,
        "tiene_infraestructura_cloacal_compleja": None,

        # Reclamos y Facturación
        "reclamos_falta_presion": None,
        "reclamos_escape_calzada_vereda": None,
        "reclamos_obstruccion_cloacal": None,
        "cortes_servicio_falta_pago": None,
    }

# ============================================================================
# FUNCIONES DE VALIDACIÓN
# ============================================================================

def es_numero_valido(texto, permitir_cero=True):
    """
    Valida si el texto es un número válido (entero o decimal).
    Retorna: (es_válido: bool, valor: float o int)
    """
    try:
        valor = float(texto.strip())
        if not permitir_cero and valor == 0:
            return False, valor
        return True, valor
    except ValueError:
        return False, None

def es_opcion_valida(texto, opciones_validas):
    """
    Valida si el texto está en la lista de opciones válidas.
    """
    return texto.strip() in opciones_validas

def es_saltar(respuesta):
    """
    Verifica si el usuario quiere saltear esta pregunta.
    """
    return respuesta.strip().lower() == "siguiente"

# ============================================================================
# FUNCIONES DE FLUJO DE CONVERSACIÓN
# ============================================================================

def obtener_proximo_paso(datos):
    """
    Calcula automáticamente cuál debe ser el próximo paso del flujo conversacional.
    Retorna: (paso_numero, mensaje_prompt)
    """
    paso = datos["paso_actual"]
    tipo_servicio = datos["tipo_servicio"]

    # PASO 0: PEDIR_ID (Paso Inicial Obligatorio - Validación por Padrón)
    if paso == 0:
        prompt = (
            "¡Hola! 👋 Te damos la bienvenida al asistente virtual para el Relevamiento Anual de Prestadores. "
            "Para empezar, por favor escribí tu *ID numérico de prestador* según el padrón oficial.\n\n"
            "💡 Este ID es fundamental para validar tu institución en nuestro registro."
        )
        return paso, prompt

    # PASO 0.1: Menú de Opciones Inicial (NUEVO)
    elif paso == 0.1:
        nombre = datos.get("nombre_prestador", "Institución")
        prompt = (
            f"¡Validación exitosa! 🎉 Bienvenida institución: *{nombre}*.\n\n"
            "¿Qué deseas hacer hoy?\n"
            "1 - Iniciar o continuar la carga del Relevamiento Anual (ANEXO I)\n"
            "2 - Ponerme en contacto con el equipo técnico (Consultas/Soporte)\n\n"
            "Respondé solo con el número de opción (1 o 2)."
        )
        return paso, prompt

    # PASO 0.2: Dejar Consulta Técnica (NUEVO)
    elif paso == 0.2:
        prompt = (
            "Por favor, escribí tu consulta técnica detallada a continuación. "
            "Un asesor se comunicará con vos a la brevedad: 🛠️"
        )
        return paso, prompt

    # PASO 1: Localidad
    elif paso == 1:
        prompt = "¿A qué *Localidad o Paraje* pertenece la institución?"
        return paso, prompt

    # PASO 2: Referente
    elif paso == 2:
        prompt = "¿Cuál es el nombre del *referente o contacto principal* para el relevamiento?"
        return paso, prompt

    # PASO 3: Tipo de Servicio
    elif paso == 3:
        prompt = (
            "¿Qué tipo de servicio brinda la institución?\n"
            "1 - Solo Agua\n"
            "2 - Solo Cloacas\n"
            "3 - Ambos\n\n"
            "Respondé solo con el número."
        )
        return paso, prompt

    # PASO 3.1: ¿Agua tarifado? (Condicional si tipo_servicio es 1 o 3)
    elif paso == 3.1:
        if tipo_servicio not in [TIPO_SERVICIO_AGUA_SOLO, TIPO_SERVICIO_AMBOS]:
            datos["paso_actual"] = 3.2
            return obtener_proximo_paso(datos)

        prompt = (
            "¿El servicio de AGUA POTABLE es tarifado?\n"
            "1 - Sí (Medido o Tasa)\n"
            "2 - No (Gratuito/Subvencionado)"
        )
        return paso, prompt

    # PASO 3.2: ¿Cloacas tarifado? (Condicional si tipo_servicio es 2 o 3)
    elif paso == 3.2:
        if tipo_servicio not in [TIPO_SERVICIO_CLOACAS_SOLO, TIPO_SERVICIO_AMBOS]:
            datos["paso_actual"] = 3.3
            return obtener_proximo_paso(datos)

        prompt = (
            "¿El servicio de DESAGÜES CLOACALES es tarifado?\n"
            "1 - Sí\n"
            "2 - No"
        )
        return paso, prompt

    # PASO 3.3: Iniciar Personal (Paso unificado con Doble Afectación)
    elif paso == 3.3:
        if datos["paso_personal_actual"] is None:
            # Primera vez: inicializar el módulo de personal
            datos["paso_personal_actual"] = "dependencia"
            datos["perfil_personal_index"] = 0
        return obtener_paso_personal(datos)

    # PASO 4: Conexiones de Agua (Solo Agua/Ambos)
    elif paso == 4:
        if tipo_servicio not in [TIPO_SERVICIO_AGUA_SOLO, TIPO_SERVICIO_AMBOS]:
            datos["paso_actual"] = 14 if tipo_servicio == TIPO_SERVICIO_CLOACAS_SOLO else 24
            return obtener_proximo_paso(datos)

        prompt = (
            "¿Cuántas *conexiones de agua* residenciales/totales activas tiene el sistema actualmente? "
            "(Si no tenés este dato, escribí 'siguiente')."
        )
        return paso, prompt

    # PASO 5: Habitantes Agua (Solo Agua/Ambos)
    elif paso == 5:
        if tipo_servicio not in [TIPO_SERVICIO_AGUA_SOLO, TIPO_SERVICIO_AMBOS]:
            datos["paso_actual"] = 14
            return obtener_proximo_paso(datos)

        prompt = "¿A cuántos *habitantes* abastece efectivamente con la red de agua potable? (Población servida)"
        return paso, prompt

    # PASO 6: Caudal Agua (Solo Agua/Ambos)
    elif paso == 6:
        if tipo_servicio not in [TIPO_SERVICIO_AGUA_SOLO, TIPO_SERVICIO_AMBOS]:
            datos["paso_actual"] = 14
            return obtener_proximo_paso(datos)

        prompt = "¿Cuál es el *caudal diario de agua* promedio liberado a la red (en m³/día)?"
        return paso, prompt

    # PASO 7: Flag - Fuente de Captación Compleja (Solo Agua/Ambos)
    elif paso == 7:
        if tipo_servicio not in [TIPO_SERVICIO_AGUA_SOLO, TIPO_SERVICIO_AMBOS]:
            datos["paso_actual"] = 14
            return obtener_proximo_paso(datos)

        prompt = (
            "¿Cuentan con fuentes de captación (Superficial/Pozo/Acueducto) o planta de potabilización?\n"
            "1 - Sí\n"
            "2 - No"
        )
        return paso, prompt

    # PASO 8: Flag - Medidores Nuevos (Solo Agua/Ambos)
    elif paso == 8:
        if tipo_servicio not in [TIPO_SERVICIO_AGUA_SOLO, TIPO_SERVICIO_AMBOS]:
            datos["paso_actual"] = 14
            return obtener_proximo_paso(datos)

        prompt = (
            "¿Instalaron medidores domiciliarios nuevos durante el último año?\n"
            "1 - Sí\n"
            "2 - No"
        )
        return paso, prompt

    # PASO 9: Flag - Análisis de Laboratorio (Solo Agua/Ambos)
    elif paso == 9:
        if tipo_servicio not in [TIPO_SERVICIO_AGUA_SOLO, TIPO_SERVICIO_AMBOS]:
            datos["paso_actual"] = 14
            return obtener_proximo_paso(datos)

        prompt = (
            "¿Realizan análisis de autocontrol de laboratorio en almacenamiento o red?\n"
            "1 - Sí\n"
            "2 - No"
        )
        return paso, prompt

    # PASO 10: Flag - Balance Hídrico Mensual (Solo Agua/Ambos)
    elif paso == 10:
        if tipo_servicio not in [TIPO_SERVICIO_AGUA_SOLO, TIPO_SERVICIO_AMBOS]:
            datos["paso_actual"] = 14
            return obtener_proximo_paso(datos)

        prompt = (
            "¿Llevan un registro de Balance Hídrico mensual del sistema?\n"
            "1 - Sí\n"
            "2 - No"
        )
        return paso, prompt

    # PASO 11: Macromedidores Operativos (Solo Agua/Ambos)
    elif paso == 11:
        if tipo_servicio not in [TIPO_SERVICIO_AGUA_SOLO, TIPO_SERVICIO_AMBOS]:
            datos["paso_actual"] = 14
            return obtener_proximo_paso(datos)

        prompt = "¿Cuántos *macro-medidores operativos* tienen instalados a la salida de las fuentes o plantas?"
        return paso, prompt

    # PASO 12: Longitud Red Agua (Solo Agua/Ambos)
    elif paso == 12:
        if tipo_servicio not in [TIPO_SERVICIO_AGUA_SOLO, TIPO_SERVICIO_AMBOS]:
            datos["paso_actual"] = 14
            return obtener_proximo_paso(datos)

        prompt = "¿Cuál es la *longitud total de la red de distribución* de agua (en kilómetros)?"
        return paso, prompt

    # PASO 13: Capacidad Almacenamiento (Solo Agua/Ambos)
    elif paso == 13:
        if tipo_servicio not in [TIPO_SERVICIO_AGUA_SOLO, TIPO_SERVICIO_AMBOS]:
            datos["paso_actual"] = 14
            return obtener_proximo_paso(datos)

        prompt = (
            "¿Cuál es la *capacidad de almacenamiento total* del sistema "
            "(suma de cisternas y tanques en m³)?"
        )
        return paso, prompt

    # PASO 14: Población Urbana Cloacas (Solo si es solo cloacas)
    elif paso == 14:
        if tipo_servicio == TIPO_SERVICIO_CLOACAS_SOLO:
            prompt = "Para el módulo de cloacas: ¿Cuál es la *población urbana estimada* de la localidad?"
            return paso, prompt
        else:
            datos["paso_actual"] = 15
            return obtener_proximo_paso(datos)

    # PASO 15: Conexiones Cloacales Residenciales (Solo Cloacas/Ambos)
    elif paso == 15:
        if tipo_servicio not in [TIPO_SERVICIO_CLOACAS_SOLO, TIPO_SERVICIO_AMBOS]:
            datos["paso_actual"] = 24
            return obtener_proximo_paso(datos)

        prompt = "¿Cuántas *conexiones cloacales residenciales* activas tiene la red actualmente?"
        return paso, prompt

    # PASO 16: Conexiones Cloacales Comerciales (Solo Cloacas/Ambos)
    elif paso == 16:
        if tipo_servicio not in [TIPO_SERVICIO_CLOACAS_SOLO, TIPO_SERVICIO_AMBOS]:
            datos["paso_actual"] = 24
            return obtener_proximo_paso(datos)

        prompt = "¿Cuántas *conexiones cloacales comerciales, industriales o institucionales* activas tienen?"
        return paso, prompt

    # PASO 17: Habitantes Cloacas (Solo Cloacas/Ambos)
    elif paso == 17:
        if tipo_servicio not in [TIPO_SERVICIO_CLOACAS_SOLO, TIPO_SERVICIO_AMBOS]:
            datos["paso_actual"] = 24
            return obtener_proximo_paso(datos)

        prompt = "¿A cuántos *habitantes* conecta efectivamente la red de desagües cloacales?"
        return paso, prompt

    # PASO 18: Longitud Red Cloacas (Solo Cloacas/Ambos)
    elif paso == 18:
        if tipo_servicio not in [TIPO_SERVICIO_CLOACAS_SOLO, TIPO_SERVICIO_AMBOS]:
            datos["paso_actual"] = 24
            return obtener_proximo_paso(datos)

        prompt = "¿Cuál es la *longitud total de la red colectora* cloacal (en kilómetros)?"
        return paso, prompt

    # PASO 19: Caudal Cloacas (Solo Cloacas/Ambos)
    elif paso == 19:
        if tipo_servicio not in [TIPO_SERVICIO_CLOACAS_SOLO, TIPO_SERVICIO_AMBOS]:
            datos["paso_actual"] = 24
            return obtener_proximo_paso(datos)

        prompt = "¿Cuál es el *caudal diario cloacal* promedio que ingresa o se trata (en m³/día)?"
        return paso, prompt

    # PASO 20: Flag - Infraestructura Cloacal Compleja (Solo Cloacas/Ambos)
    elif paso == 20:
        if tipo_servicio not in [TIPO_SERVICIO_CLOACAS_SOLO, TIPO_SERVICIO_AMBOS]:
            datos["paso_actual"] = 24
            return obtener_proximo_paso(datos)

        prompt = (
            "¿El sistema cuenta con infraestructura compleja como colectores principales, "
            "estaciones de bombeo o planta de tratamiento de líquidos cloacales?\n"
            "1 - Sí\n"
            "2 - No"
        )
        return paso, prompt

    # PASO 21: Reclamos Falta de Presión (Solo Agua/Ambos)
    elif paso == 21:
        if tipo_servicio not in [TIPO_SERVICIO_AGUA_SOLO, TIPO_SERVICIO_AMBOS]:
            datos["paso_actual"] = 23
            return obtener_proximo_paso(datos)

        prompt = (
            "Pasamos al módulo de Reclamos y Atención. 📞 "
            "¿Cuántos reclamos anuales registraron por *Falta de presión de agua*?"
        )
        return paso, prompt

    # PASO 22: Reclamos Escapes (Solo Agua/Ambos)
    elif paso == 22:
        if tipo_servicio not in [TIPO_SERVICIO_AGUA_SOLO, TIPO_SERVICIO_AMBOS]:
            datos["paso_actual"] = 23
            return obtener_proximo_paso(datos)

        prompt = "¿Cuántos reclamos anuales registraron por *Escapes o Fugas de agua* en calzada o vereda?"
        return paso, prompt

    # PASO 23: Reclamos Obstrucción Cloacal (Solo Cloacas/Ambos)
    elif paso == 23:
        if tipo_servicio not in [TIPO_SERVICIO_CLOACAS_SOLO, TIPO_SERVICIO_AMBOS]:
            datos["paso_actual"] = 24
            return obtener_proximo_paso(datos)

        prompt = "¿Cuántos reclamos anuales registraron por *Obstrucciones domiciliarias o desbordes cloacales*?"
        return paso, prompt

    # PASO 24: Cortes por Falta de Pago (Todos)
    elif paso == 24:
        prompt = (
            "Por último, en relación a Facturación comercial: "
            "¿Cuántos *cortes efectivos del servicio por falta de pago* realizaron en el último año?"
        )
        return paso, prompt

    # PASO 25: Resumen y Edición Final (Interactivo por Casilleros)
    elif paso == 25:
        return generar_resumen_edicion(datos)

    return paso, "Error: paso desconocido."

def obtener_paso_personal(datos):
    """
    Maneja el módulo dinámico de Personal con Doble Afectación.
    MANTIENE paso_actual = 3.3 FIJO durante toda la iteración.
    Solo transiciona cuando se terminan los 5 perfiles.
    Retorna: (paso_numero, mensaje_prompt)
    """
    tipo_servicio = datos["tipo_servicio"]
    perfil_index = datos["perfil_personal_index"]
    paso_personal = datos["paso_personal_actual"]
    perfil_actual = PERFILES_PERSONAL[perfil_index]

    # SIEMPRE retornamos paso 3.3 mientras estemos en personal
    paso_actual_total = 3.3

    if paso_personal == "dependencia":
        prompt = f"*{perfil_actual}*: ¿Cuántos en relación de dependencia (Sueldos/Salarios)?"
        return paso_actual_total, prompt

    elif paso_personal == "contratados":
        prompt = f"*{perfil_actual}*: ¿Cuántos contratados (Honorarios/Prestaciones)?"
        return paso_actual_total, prompt

    elif paso_personal == "afectacion_agua":
        # Verificar si hay personal en este perfil
        personal_datos = datos["personal"][perfil_actual]
        total_personal = (personal_datos["dependencia"] or 0) + (personal_datos["contratados"] or 0)

        # Si el total es 0, asignar 0 a ambas afectaciones y avanzar
        if total_personal == 0:
            datos["personal"][perfil_actual]["afectacion_agua"] = 0
            datos["personal"][perfil_actual]["afectacion_cloacas"] = 0
            datos["perfil_personal_index"] += 1
            if datos["perfil_personal_index"] < len(PERFILES_PERSONAL):
                datos["paso_personal_actual"] = "dependencia"
                return obtener_paso_personal(datos)
            else:
                datos["paso_actual"] = 4
                datos["paso_personal_actual"] = None
                return obtener_proximo_paso(datos)

        # Si tipo_servicio es 1 (Solo Agua), asignar automáticamente
        if tipo_servicio == TIPO_SERVICIO_AGUA_SOLO:
            datos["personal"][perfil_actual]["afectacion_agua"] = 100
            datos["personal"][perfil_actual]["afectacion_cloacas"] = 0
            datos["perfil_personal_index"] += 1
            if datos["perfil_personal_index"] < len(PERFILES_PERSONAL):
                datos["paso_personal_actual"] = "dependencia"
                return obtener_paso_personal(datos)
            else:
                datos["paso_actual"] = 4
                datos["paso_personal_actual"] = None
                return obtener_proximo_paso(datos)

        # Si tipo_servicio es 2 (Solo Cloacas), asignar automáticamente
        elif tipo_servicio == TIPO_SERVICIO_CLOACAS_SOLO:
            datos["personal"][perfil_actual]["afectacion_agua"] = 0
            datos["personal"][perfil_actual]["afectacion_cloacas"] = 100
            datos["perfil_personal_index"] += 1
            if datos["perfil_personal_index"] < len(PERFILES_PERSONAL):
                datos["paso_personal_actual"] = "dependencia"
                return obtener_paso_personal(datos)
            else:
                datos["paso_actual"] = 4
                datos["paso_personal_actual"] = None
                return obtener_proximo_paso(datos)

        else:
            # Ambos: preguntar % para AGUA
            prompt = f"*{perfil_actual}*: ¿Qué % de afectación al servicio de AGUA POTABLE? (0-100)"
            return paso_actual_total, prompt

    elif paso_personal == "afectacion_cloacas":
        # Preguntar % para CLOACAS
        prompt = f"*{perfil_actual}*: ¿Qué % de afectación al servicio de DESAGÜES CLOACALES? (0-100)"
        return paso_actual_total, prompt

    return paso_actual_total, "Error en módulo de personal."

def procesar_respuesta_personal(datos, respuesta):
    """
    Procesa la respuesta del usuario en el módulo de Personal.
    Mantiene paso_actual = 3.3 durante toda la iteración.
    Retorna: (éxito: bool, mensaje_error: str o None)
    """
    tipo_servicio = datos["tipo_servicio"]
    perfil_index = datos["perfil_personal_index"]
    paso_personal = datos["paso_personal_actual"]
    perfil_actual = PERFILES_PERSONAL[perfil_index]

    if es_saltar(respuesta):
        valor = None
    else:
        valido, valor = es_numero_valido(respuesta, permitir_cero=True)
        if not valido:
            return False, "❌ Por favor, escribí un número válido (o 'siguiente' para saltear)."

    if paso_personal == "dependencia":
        datos["personal"][perfil_actual]["dependencia"] = valor
        datos["paso_personal_actual"] = "contratados"

    elif paso_personal == "contratados":
        datos["personal"][perfil_actual]["contratados"] = valor
        datos["paso_personal_actual"] = "afectacion_agua"

        total_personal = (datos["personal"][perfil_actual]["dependencia"] or 0) + (valor if valor is not None else 0)

        # Si no hay personal, asignar 0 a ambas afectaciones y avanzar
        if total_personal == 0:
            datos["personal"][perfil_actual]["afectacion_agua"] = 0
            datos["personal"][perfil_actual]["afectacion_cloacas"] = 0
            datos["perfil_personal_index"] += 1

            if datos["perfil_personal_index"] < len(PERFILES_PERSONAL):
                datos["paso_personal_actual"] = "dependencia"
            else:
                datos["paso_actual"] = 4
                datos["paso_personal_actual"] = None

        # Si hay personal pero tipo_servicio es SOLO AGUA
        elif tipo_servicio == TIPO_SERVICIO_AGUA_SOLO:
            datos["personal"][perfil_actual]["afectacion_agua"] = 100
            datos["personal"][perfil_actual]["afectacion_cloacas"] = 0
            datos["perfil_personal_index"] += 1

            if datos["perfil_personal_index"] < len(PERFILES_PERSONAL):
                datos["paso_personal_actual"] = "dependencia"
            else:
                datos["paso_actual"] = 4
                datos["paso_personal_actual"] = None

        # Si hay personal pero tipo_servicio es SOLO CLOACAS
        elif tipo_servicio == TIPO_SERVICIO_CLOACAS_SOLO:
            datos["personal"][perfil_actual]["afectacion_agua"] = 0
            datos["personal"][perfil_actual]["afectacion_cloacas"] = 100
            datos["perfil_personal_index"] += 1

            if datos["perfil_personal_index"] < len(PERFILES_PERSONAL):
                datos["paso_personal_actual"] = "dependencia"
            else:
                datos["paso_actual"] = 4
                datos["paso_personal_actual"] = None

    elif paso_personal == "afectacion_agua":
        if valor is not None:
            if valor < 0 or valor > 100:
                return False, "❌ El porcentaje debe estar entre 0 y 100."

        datos["personal"][perfil_actual]["afectacion_agua"] = valor
        datos["paso_personal_actual"] = "afectacion_cloacas"

    elif paso_personal == "afectacion_cloacas":
        if valor is not None:
            if valor < 0 or valor > 100:
                return False, "❌ El porcentaje debe estar entre 0 y 100."

        # Validación CRÍTICA: Suma no debe superar 100%
        afectacion_agua = datos["personal"][perfil_actual]["afectacion_agua"] or 0
        afectacion_cloacas = valor if valor is not None else 0
        suma_afectaciones = afectacion_agua + afectacion_cloacas

        if suma_afectaciones > 100:
            return False, (
                "❌ La suma de las afectaciones supera el 100% de la jornada laboral de este perfil. "
                "Ingresá el % de cloacas correcto."
            )

        datos["personal"][perfil_actual]["afectacion_cloacas"] = valor
        datos["perfil_personal_index"] += 1

        if datos["perfil_personal_index"] < len(PERFILES_PERSONAL):
            datos["paso_personal_actual"] = "dependencia"
        else:
            datos["paso_actual"] = 4
            datos["paso_personal_actual"] = None

    guardar_datos(datos)
    return True, None

def generar_resumen_edicion(datos):
    """
    Genera el RESUMEN CONSOLIDADO de datos para edición final (Paso 25).
    Mapea cada variable a un casillero del 1 al 16.
    Retorna: (paso_numero, mensaje_prompt)
    """
    tipo_servicio = datos["tipo_servicio"]

    # Construir resumen con casilleros
    resumen_lineas = ["📋 *RESUMEN DE DATOS CARGADOS:*\n"]

    # Casilleros de Agua
    if tipo_servicio in [TIPO_SERVICIO_AGUA_SOLO, TIPO_SERVICIO_AMBOS]:
        val = datos.get("conexiones_agua")
        resumen_lineas.append(f"*Casillero 1:* Conexiones de agua: {val if val is not None else '(no cargado)'}")

        val = datos.get("habitantes_agua")
        resumen_lineas.append(f"*Casillero 2:* Población servida (agua): {val if val is not None else '(no cargado)'}")

        val = datos.get("caudal_agua_m3dia")
        resumen_lineas.append(f"*Casillero 3:* Caudal agua (m³/día): {val if val is not None else '(no cargado)'}")

        val = datos.get("macromedidores_operativos_agua")
        resumen_lineas.append(f"*Casillero 4:* Macro-medidores: {val if val is not None else '(no cargado)'}")

        val = datos.get("longitud_red_agua_km")
        resumen_lineas.append(f"*Casillero 5:* Longitud red agua (km): {val if val is not None else '(no cargado)'}")

        val = datos.get("capacidad_almacenamiento_m3")
        resumen_lineas.append(f"*Casillero 6:* Capacidad almacenamiento (m³): {val if val is not None else '(no cargado)'}")

    # Casilleros de Cloacas
    if tipo_servicio in [TIPO_SERVICIO_CLOACAS_SOLO, TIPO_SERVICIO_AMBOS]:
        if tipo_servicio == TIPO_SERVICIO_CLOACAS_SOLO:
            val = datos.get("poblacion_urbana_cloacas")
            resumen_lineas.append(f"*Casillero 16:* Población urbana: {val if val is not None else '(no cargado)'}")

        val = datos.get("conexiones_cloacas")
        resumen_lineas.append(f"*Casillero 7:* Conexiones cloacales residenciales: {val if val is not None else '(no cargado)'}")

        val = datos.get("conexiones_cloacas_com_ind")
        resumen_lineas.append(f"*Casillero 8:* Conexiones comerciales/industriales: {val if val is not None else '(no cargado)'}")

        val = datos.get("habitantes_cloacas")
        resumen_lineas.append(f"*Casillero 9:* Población servida (cloacas): {val if val is not None else '(no cargado)'}")

        val = datos.get("longitud_red_cloacas_km")
        resumen_lineas.append(f"*Casillero 10:* Longitud red cloacas (km): {val if val is not None else '(no cargado)'}")

        val = datos.get("caudal_cloacas_media")
        resumen_lineas.append(f"*Casillero 11:* Caudal cloacal (m³/día): {val if val is not None else '(no cargado)'}")

    # Casilleros de Reclamos
    if tipo_servicio in [TIPO_SERVICIO_AGUA_SOLO, TIPO_SERVICIO_AMBOS]:
        val = datos.get("reclamos_falta_presion")
        resumen_lineas.append(f"*Casillero 12:* Reclamos falta presión: {val if val is not None else '(no cargado)'}")

        val = datos.get("reclamos_escape_calzada_vereda")
        resumen_lineas.append(f"*Casillero 13:* Reclamos escapes/fugas: {val if val is not None else '(no cargado)'}")

    if tipo_servicio in [TIPO_SERVICIO_CLOACAS_SOLO, TIPO_SERVICIO_AMBOS]:
        val = datos.get("reclamos_obstruccion_cloacal")
        resumen_lineas.append(f"*Casillero 14:* Reclamos obstrucción cloacal: {val if val is not None else '(no cargado)'}")

    # Cortes (para todos)
    val = datos.get("cortes_servicio_falta_pago")
    resumen_lineas.append(f"*Casillero 15:* Cortes por falta de pago: {val if val is not None else '(no cargado)'}")

    resumen_lineas.append("\n¿Los datos son correctos?")
    resumen_lineas.append("👉 Respondé *ENVIAR* para finalizar")
    resumen_lineas.append("👉 O respondé el número del casillero que querés corregir (Ej: 4)")

    prompt = "\n".join(resumen_lineas)
    return 25, prompt

# ============================================================================
# PROCESAMIENTO DE RESPUESTAS
# ============================================================================

def procesar_respuesta(datos, respuesta_usuario):
    """
    Procesa la respuesta del usuario según el paso actual.
    Retorna: (éxito: bool, mensaje_respuesta: str)
    """
    paso = datos["paso_actual"]

    # PASO 0: PEDIR_ID (Validación por Padrón Oficial + Candado Electrónico)
    if paso == 0:
        es_valido, nombre_oficial = validar_id_prestador(respuesta_usuario)

        if not es_valido:
            return False, (
                "❌ El ID ingresado no existe en el padrón oficial. "
                "Por favor, verificá el número e intentá de nuevo."
            )

        # Verificar si ya está completo (Candado Electrónico)
        existe, estado = obtener_estado_prestador(respuesta_usuario.strip())
        if existe and estado == "Completo":
            datos["bloqueado_por_completitud"] = True
            datos["id_prestador"] = respuesta_usuario.strip()
            datos["nombre_prestador"] = nombre_oficial
            guardar_datos(datos)
            return True, (
                f"⚠️ El prestador *{nombre_oficial}* ya completó su relevamiento.\n\n"
                "¿Qué necesitás hacer?\n"
                "1 - Dejar una consulta de soporte/corrección\n"
                "2 - Salir"
            )

        # No está bloqueado: registrar ID y pasar al Menú Inicial (Paso 0.1)
        datos["id_prestador"] = respuesta_usuario.strip()
        datos["nombre_prestador"] = nombre_oficial
        datos["paso_actual"] = 0.1
        guardar_datos(datos)
        return True, ""

    # PASO 0.1: Menú de Opciones Inicial (NUEVO)
    elif paso == 0.1:
        if not es_opcion_valida(respuesta_usuario, ["1", "2"]):
            return False, "❌ Por favor, respondé con 1 o 2."

        opcion = respuesta_usuario.strip()

        if opcion == "1":
            # Iniciar el cuestionario completo
            datos["paso_actual"] = 1
            guardar_datos(datos)
            return True, "🚀 ¡Excelente! Iniciamos el cuestionario."

        elif opcion == "2":
            # Ir a dejar consulta técnica
            datos["paso_actual"] = 0.2
            guardar_datos(datos)
            return True, ""

    # PASO 0.2: Dejar Consulta Técnica (NUEVO)
    elif paso == 0.2:
        consulta = respuesta_usuario.strip()
        if not consulta:
            return False, "❌ Por favor, escribí tu consulta técnica."

        # Guardar consulta y cambiar estado
        datos["consulta_soporte"] = consulta
        datos["estado_registro"] = "Consulta_Soporte"
        datos["paso_actual"] = 0.1
        guardar_datos(datos)
        return True, (
            "✅ ¡Gracias! Tu consulta ha sido registrada. "
            "Un asesor se comunicará con vos a la brevedad. 📞\n\n"
            "¿Deseas hacer algo más?"
        )

    # PASO 1: Localidad
    elif paso == 1:
        localidad = respuesta_usuario.strip()
        if not localidad:
            return False, "❌ Por favor, escribí la localidad."
        datos["localidad"] = localidad
        datos["paso_actual"] = 2
        guardar_datos(datos)
        return True, "✅ Anotado."

    # PASO 2: Referente
    elif paso == 2:
        referente = respuesta_usuario.strip()
        if not referente:
            return False, "❌ Por favor, escribí el nombre del referente."
        datos["referente"] = referente
        datos["paso_actual"] = 3
        guardar_datos(datos)
        return True, "✅ Anotado."

    # PASO 3: Tipo de Servicio
    elif paso == 3:
        if not es_opcion_valida(respuesta_usuario, ["1", "2", "3"]):
            return False, "❌ Por favor, respondé con 1, 2 o 3."
        datos["tipo_servicio"] = int(respuesta_usuario.strip())
        datos["paso_actual"] = 3.1
        guardar_datos(datos)
        return True, "✅ Registrado."

    # PASO 3.1: Agua Tarifado
    elif paso == 3.1:
        if not es_opcion_valida(respuesta_usuario, ["1", "2"]):
            return False, "❌ Respondé con 1 (Sí) o 2 (No)."
        datos["agua_tarifado"] = int(respuesta_usuario.strip())
        datos["paso_actual"] = 3.2
        guardar_datos(datos)
        return True, "✅ Registrado."

    # PASO 3.2: Cloacas Tarifado
    elif paso == 3.2:
        if not es_opcion_valida(respuesta_usuario, ["1", "2"]):
            return False, "❌ Respondé con 1 (Sí) o 2 (No)."
        datos["cloacas_tarifado"] = int(respuesta_usuario.strip())
        datos["paso_actual"] = 3.3
        guardar_datos(datos)
        return True, "✅ Registrado."

    # PASO 3.3: Módulo de Personal (paso UNIFICADO con Doble Afectación)
    elif paso == 3.3:
        exito, mensaje = procesar_respuesta_personal(datos, respuesta_usuario)
        if not exito:
            return False, mensaje
        return True, "✅ Anotado."

    # PASO 4: Conexiones de Agua
    elif paso == 4:
        if datos.get("en_modo_edicion"):
            # Estamos editando desde paso 25
            if es_saltar(respuesta_usuario):
                datos["conexiones_agua"] = None
            else:
                valido, valor = es_numero_valido(respuesta_usuario)
                if not valido:
                    return False, "❌ Por favor, escribí un número válido (o 'siguiente' para saltear)."
                datos["conexiones_agua"] = valor
            # NO avanzar; volver a paso 25
            datos["en_modo_edicion"] = False
            guardar_datos(datos)
            return True, "✅ Actualizado. Volvemos al resumen..."
        else:
            if es_saltar(respuesta_usuario):
                datos["conexiones_agua"] = None
            else:
                valido, valor = es_numero_valido(respuesta_usuario)
                if not valido:
                    return False, "❌ Por favor, escribí un número válido (o 'siguiente' para saltear)."
                datos["conexiones_agua"] = valor
            datos["paso_actual"] = 5
            guardar_datos(datos)
            return True, "✅ Anotado."

    # PASO 5: Habitantes Agua
    elif paso == 5:
        if datos.get("en_modo_edicion"):
            if es_saltar(respuesta_usuario):
                datos["habitantes_agua"] = None
            else:
                valido, valor = es_numero_valido(respuesta_usuario)
                if not valido:
                    return False, "❌ Por favor, escribí un número válido (o 'siguiente' para saltear)."
                datos["habitantes_agua"] = valor
            datos["en_modo_edicion"] = False
            guardar_datos(datos)
            return True, "✅ Actualizado. Volvemos al resumen..."
        else:
            if es_saltar(respuesta_usuario):
                datos["habitantes_agua"] = None
            else:
                valido, valor = es_numero_valido(respuesta_usuario)
                if not valido:
                    return False, "❌ Por favor, escribí un número válido (o 'siguiente' para saltear)."
                datos["habitantes_agua"] = valor
            datos["paso_actual"] = 6
            guardar_datos(datos)
            return True, "✅ Anotado."

    # PASO 6: Caudal Agua
    elif paso == 6:
        if datos.get("en_modo_edicion"):
            if es_saltar(respuesta_usuario):
                datos["caudal_agua_m3dia"] = None
            else:
                valido, valor = es_numero_valido(respuesta_usuario)
                if not valido:
                    return False, "❌ Por favor, escribí un número válido (o 'siguiente' para saltear)."
                datos["caudal_agua_m3dia"] = valor
            datos["en_modo_edicion"] = False
            guardar_datos(datos)
            return True, "✅ Actualizado. Volvemos al resumen..."
        else:
            if es_saltar(respuesta_usuario):
                datos["caudal_agua_m3dia"] = None
            else:
                valido, valor = es_numero_valido(respuesta_usuario)
                if not valido:
                    return False, "❌ Por favor, escribí un número válido (o 'siguiente' para saltear)."
                datos["caudal_agua_m3dia"] = valor
            datos["paso_actual"] = 7
            guardar_datos(datos)
            return True, "✅ Anotado."

    # PASO 7: Flag - Fuente Captación
    elif paso == 7:
        if not es_opcion_valida(respuesta_usuario, ["1", "2"]):
            return False, "❌ Respondé con 1 (Sí) o 2 (No)."
        datos["tiene_fuente_captacion_compleja"] = (respuesta_usuario.strip() == "1")
        datos["paso_actual"] = 8
        guardar_datos(datos)
        return True, "✅ Anotado."

    # PASO 8: Flag - Medidores Nuevos
    elif paso == 8:
        if not es_opcion_valida(respuesta_usuario, ["1", "2"]):
            return False, "❌ Respondé con 1 (Sí) o 2 (No)."
        datos["tiene_medidores_nuevos_año"] = (respuesta_usuario.strip() == "1")
        datos["paso_actual"] = 9
        guardar_datos(datos)
        return True, "✅ Anotado."

    # PASO 9: Flag - Análisis Laboratorio
    elif paso == 9:
        if not es_opcion_valida(respuesta_usuario, ["1", "2"]):
            return False, "❌ Respondé con 1 (Sí) o 2 (No)."
        datos["tiene_analisis_laboratorio_autocontrol"] = (respuesta_usuario.strip() == "1")
        datos["paso_actual"] = 10
        guardar_datos(datos)
        return True, "✅ Anotado."

    # PASO 10: Flag - Balance Hídrico
    elif paso == 10:
        if not es_opcion_valida(respuesta_usuario, ["1", "2"]):
            return False, "❌ Respondé con 1 (Sí) o 2 (No)."
        datos["tiene_balance_hidrico_mensual"] = (respuesta_usuario.strip() == "1")
        datos["paso_actual"] = 11
        guardar_datos(datos)
        return True, "✅ Anotado."

    # PASO 11: Macromedidores Operativos
    elif paso == 11:
        if es_saltar(respuesta_usuario):
            datos["macromedidores_operativos_agua"] = None
        else:
            valido, valor = es_numero_valido(respuesta_usuario)
            if not valido:
                return False, "❌ Por favor, escribí un número válido (o 'siguiente' para saltear)."
            datos["macromedidores_operativos_agua"] = valor
        datos["paso_actual"] = 12
        guardar_datos(datos)
        return True, "✅ Anotado."

    # PASO 12: Longitud Red Agua
    elif paso == 12:
        if es_saltar(respuesta_usuario):
            datos["longitud_red_agua_km"] = None
        else:
            valido, valor = es_numero_valido(respuesta_usuario)
            if not valido:
                return False, "❌ Por favor, escribí un número válido (o 'siguiente' para saltear)."
            datos["longitud_red_agua_km"] = valor
        datos["paso_actual"] = 13
        guardar_datos(datos)
        return True, "✅ Anotado."

    # PASO 13: Capacidad Almacenamiento
    elif paso == 13:
        if es_saltar(respuesta_usuario):
            datos["capacidad_almacenamiento_m3"] = None
        else:
            valido, valor = es_numero_valido(respuesta_usuario)
            if not valido:
                return False, "❌ Por favor, escribí un número válido (o 'siguiente' para saltear)."
            datos["capacidad_almacenamiento_m3"] = valor
        datos["paso_actual"] = 14
        guardar_datos(datos)
        return True, "✅ Anotado."

    # PASO 14: Población Urbana Cloacas
    elif paso == 14:
        if datos["tipo_servicio"] == TIPO_SERVICIO_CLOACAS_SOLO:
            if es_saltar(respuesta_usuario):
                datos["poblacion_urbana_cloacas"] = None
            else:
                valido, valor = es_numero_valido(respuesta_usuario)
                if not valido:
                    return False, "❌ Por favor, escribí un número válido (o 'siguiente' para saltear)."
                datos["poblacion_urbana_cloacas"] = valor
        datos["paso_actual"] = 15
        guardar_datos(datos)
        return True, "✅ Anotado."

    # PASO 15: Conexiones Cloacales Residenciales
    elif paso == 15:
        if es_saltar(respuesta_usuario):
            datos["conexiones_cloacas"] = None
        else:
            valido, valor = es_numero_valido(respuesta_usuario)
            if not valido:
                return False, "❌ Por favor, escribí un número válido (o 'siguiente' para saltear)."
            datos["conexiones_cloacas"] = valor
        datos["paso_actual"] = 16
        guardar_datos(datos)
        return True, "✅ Anotado."

    # PASO 16: Conexiones Cloacales Comerciales
    elif paso == 16:
        if es_saltar(respuesta_usuario):
            datos["conexiones_cloacas_com_ind"] = None
        else:
            valido, valor = es_numero_valido(respuesta_usuario)
            if not valido:
                return False, "❌ Por favor, escribí un número válido (o 'siguiente' para saltear)."
            datos["conexiones_cloacas_com_ind"] = valor
        datos["paso_actual"] = 17
        guardar_datos(datos)
        return True, "✅ Anotado."

    # PASO 17: Habitantes Cloacas
    elif paso == 17:
        if es_saltar(respuesta_usuario):
            datos["habitantes_cloacas"] = None
        else:
            valido, valor = es_numero_valido(respuesta_usuario)
            if not valido:
                return False, "❌ Por favor, escribí un número válido (o 'siguiente' para saltear)."
            datos["habitantes_cloacas"] = valor
        datos["paso_actual"] = 18
        guardar_datos(datos)
        return True, "✅ Anotado."

    # PASO 18: Longitud Red Cloacas
    elif paso == 18:
        if es_saltar(respuesta_usuario):
            datos["longitud_red_cloacas_km"] = None
        else:
            valido, valor = es_numero_valido(respuesta_usuario)
            if not valido:
                return False, "❌ Por favor, escribí un número válido (o 'siguiente' para saltear)."
            datos["longitud_red_cloacas_km"] = valor
        datos["paso_actual"] = 19
        guardar_datos(datos)
        return True, "✅ Anotado."

    # PASO 19: Caudal Cloacas
    elif paso == 19:
        if es_saltar(respuesta_usuario):
            datos["caudal_cloacas_media"] = None
        else:
            valido, valor = es_numero_valido(respuesta_usuario)
            if not valido:
                return False, "❌ Por favor, escribí un número válido (o 'siguiente' para saltear)."
            datos["caudal_cloacas_media"] = valor
        datos["paso_actual"] = 20
        guardar_datos(datos)
        return True, "✅ Anotado."

    # PASO 20: Flag - Infraestructura Cloacal Compleja
    elif paso == 20:
        if not es_opcion_valida(respuesta_usuario, ["1", "2"]):
            return False, "❌ Respondé con 1 (Sí) o 2 (No)."
        datos["tiene_infraestructura_cloacal_compleja"] = (respuesta_usuario.strip() == "1")
        datos["paso_actual"] = 21
        guardar_datos(datos)
        return True, "✅ Anotado."

    # PASO 21: Reclamos Falta de Presión
    elif paso == 21:
        if es_saltar(respuesta_usuario):
            datos["reclamos_falta_presion"] = None
        else:
            valido, valor = es_numero_valido(respuesta_usuario)
            if not valido:
                return False, "❌ Por favor, escribí un número válido (o 'siguiente' para saltear)."
            datos["reclamos_falta_presion"] = valor
        datos["paso_actual"] = 22
        guardar_datos(datos)
        return True, "✅ Anotado."

    # PASO 22: Reclamos Escapes
    elif paso == 22:
        if es_saltar(respuesta_usuario):
            datos["reclamos_escape_calzada_vereda"] = None
        else:
            valido, valor = es_numero_valido(respuesta_usuario)
            if not valido:
                return False, "❌ Por favor, escribí un número válido (o 'siguiente' para saltear)."
            datos["reclamos_escape_calzada_vereda"] = valor
        datos["paso_actual"] = 23
        guardar_datos(datos)
        return True, "✅ Anotado."

    # PASO 23: Reclamos Obstrucción Cloacal
    elif paso == 23:
        if es_saltar(respuesta_usuario):
            datos["reclamos_obstruccion_cloacal"] = None
        else:
            valido, valor = es_numero_valido(respuesta_usuario)
            if not valido:
                return False, "❌ Por favor, escribí un número válido (o 'siguiente' para saltear)."
            datos["reclamos_obstruccion_cloacal"] = valor
        datos["paso_actual"] = 24
        guardar_datos(datos)
        return True, "✅ Anotado."

    # PASO 24: Cortes por Falta de Pago
    elif paso == 24:
        if es_saltar(respuesta_usuario):
            datos["cortes_servicio_falta_pago"] = None
        else:
            valido, valor = es_numero_valido(respuesta_usuario)
            if not valido:
                return False, "❌ Por favor, escribí un número válido (o 'siguiente' para saltear)."
            datos["cortes_servicio_falta_pago"] = valor
        datos["paso_actual"] = 25
        datos["en_modo_edicion"] = False
        guardar_datos(datos)
        return True, "✅ ¡Perfecto! Vamos al resumen final..."

    # PASO 25: Resumen y Edición Final (Interactivo)
    elif paso == 25:
        respuesta_limpia = respuesta_usuario.strip().upper()

        # Si responde ENVIAR: finalizar
        if respuesta_limpia == "ENVIAR":
            datos["estado_registro"] = "Completo"
            guardar_datos(datos)
            _, mensaje_final = generar_mensaje_final(datos)
            return True, mensaje_final

        # Si responde un número de casillero: entrar en modo edición
        if respuesta_limpia in CASILLEROS_EDICION:
            clave_campo, descripcion = CASILLEROS_EDICION[respuesta_limpia]

            # Mapeo inverso: qué paso corresponde a cada casillero
            mapeo_paso = {
                "conexiones_agua": 4,
                "habitantes_agua": 5,
                "caudal_agua_m3dia": 6,
                "macromedidores_operativos_agua": 11,
                "longitud_red_agua_km": 12,
                "capacidad_almacenamiento_m3": 13,
                "poblacion_urbana_cloacas": 14,
                "conexiones_cloacas": 15,
                "conexiones_cloacas_com_ind": 16,
                "habitantes_cloacas": 17,
                "longitud_red_cloacas_km": 18,
                "caudal_cloacas_media": 19,
                "reclamos_falta_presion": 21,
                "reclamos_escape_calzada_vereda": 22,
                "reclamos_obstruccion_cloacal": 23,
                "cortes_servicio_falta_pago": 24,
            }

            paso_original = mapeo_paso.get(clave_campo)
            if paso_original:
                datos["en_modo_edicion"] = True
                datos["paso_edicion_previo"] = paso_original
                datos["paso_actual"] = paso_original
                guardar_datos(datos)
                return True, f"✅ Editando: {descripcion}"
            else:
                return False, "❌ Casillero no encontrado. Por favor, respondé un número válido (1-16) o 'ENVIAR'."

        return False, "❌ Respondé 'ENVIAR' para finalizar o el número del casillero a corregir (1-16)."

    return False, "Error: paso desconocido."

def generar_mensaje_final(datos):
    """
    Genera el mensaje final de despedida.
    Verifica si hay flags complejos y personaliza el mensaje.
    Retorna: (paso_numero, mensaje_final)
    """
    flags_complejos = [
        datos.get("tiene_fuente_captacion_compleja", False),
        datos.get("tiene_medidores_nuevos_año", False),
        datos.get("tiene_balance_hidrico_mensual", False),
        datos.get("tiene_analisis_laboratorio_autocontrol", False),
        datos.get("tiene_infraestructura_cloacal_compleja", False),
    ]

    if any(flags_complejos):
        mensaje = (
            "¡Gracias! 🎉 Los datos del relevamiento anual fueron registrados correctamente.\n\n"
            "Notamos que tu institución cuenta con módulos técnicos detallados "
            "(como balances hídricos, muestreos de laboratorio o plantas de tratamiento). "
            "Para completar el 100% del Anexo I, en las próximas horas nos comunicaremos "
            "con el referente para coordinar el envío de las planillas Excel complementarias. "
            "¡Muchas gracias por tu tiempo y colaboración! 👋"
        )
    else:
        mensaje = (
            "¡Gracias! 🎉 Los datos del relevamiento anual fueron registrados correctamente "
            "en la base de datos. Si necesitás cargar otro prestador, simplemente escribí *hola* "
            "para volver a comenzar."
        )

    return 25, mensaje

# ============================================================================
# FUNCIÓN PRINCIPAL DEL MOTOR
# ============================================================================

def procesar_mensaje(telefono, mensaje_usuario, sesion_actual=None):
    """
    Función principal que coordina todo el flujo conversacional.

    Args:
        telefono: Número de teléfono del usuario (identificador único)
        mensaje_usuario: El texto que escribió el usuario
        sesion_actual: Diccionario de sesión actual (opcional; si no existe, se crea uno nuevo)

    Returns:
        diccionario con:
        {
            "exito": bool,
            "mensaje_respuesta": str,
            "mensaje_proximo_prompt": str,
            "datos_sesion": dict,
        }
    """
    if sesion_actual is None:
        sesion_actual = crear_sesion_nueva(telefono)

    paso_actual = sesion_actual["paso_actual"]

    # Casos especiales: reinicio o continuación
    if paso_actual == 0 and mensaje_usuario.strip().lower() in ["hola", "hi", "hey", "inicio", "comenzar"]:
        _, prompt = obtener_proximo_paso(sesion_actual)
        return {
            "exito": True,
            "mensaje_respuesta": "",
            "mensaje_proximo_prompt": prompt,
            "datos_sesion": sesion_actual,
        }

    if paso_actual == 25 and mensaje_usuario.strip().lower() == "hola":
        sesion_actual = crear_sesion_nueva(telefono)
        _, prompt = obtener_proximo_paso(sesion_actual)
        return {
            "exito": True,
            "mensaje_respuesta": "",
            "mensaje_proximo_prompt": prompt,
            "datos_sesion": sesion_actual,
        }

    # Procesar respuesta
    exito, mensaje_respuesta = procesar_respuesta(sesion_actual, mensaje_usuario)

    if not exito:
        _, prompt = obtener_proximo_paso(sesion_actual)
        return {
            "exito": False,
            "mensaje_respuesta": mensaje_respuesta,
            "mensaje_proximo_prompt": prompt,
            "datos_sesion": sesion_actual,
        }

    # Si estamos saliendo de edición, volver a paso 25 (resumen)
    if sesion_actual.get("en_modo_edicion") and sesion_actual["paso_actual"] != 25:
        # Después de la corrección, volver al resumen
        sesion_actual["paso_actual"] = 25
        sesion_actual["en_modo_edicion"] = False
        guardar_datos(sesion_actual)

    _, proximo_prompt = obtener_proximo_paso(sesion_actual)

    return {
        "exito": True,
        "mensaje_respuesta": mensaje_respuesta,
        "mensaje_proximo_prompt": proximo_prompt,
        "datos_sesion": sesion_actual,
    }

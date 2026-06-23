# motor.py — Máquina de Estados para Bot Conversacional de WhatsApp
# Relevamiento Anual de Prestadores (ANEXO I)
# Versión: 3.1 - Corregida la sincronización del módulo de Personal

import json
from persistencia import guardar_datos

# ============================================================================
# CONSTANTES Y CONFIGURACIÓN
# ============================================================================

PERFILES_PERSONAL = ["Profesionales", "Técnicos", "Administrativos", "Obreros", "Otros"]
TIPO_SERVICIO_AGUA_SOLO = 1
TIPO_SERVICIO_CLOACAS_SOLO = 2
TIPO_SERVICIO_AMBOS = 3

# ============================================================================
# INICIALIZACIÓN DE SESIÓN
# ============================================================================

def crear_sesion_nueva(telefono):
    """
    Crea un diccionario de sesión inicial para un prestador.
    Inicializa todos los campos requeridos con valores None y estado "Incompleto".
    """
    return {
        "telefono": telefono,
        "estado_registro": "Incompleto",
        "paso_actual": 0,
        "paso_personal_actual": None,  # Para iterar sobre PERFILES_PERSONAL (dependencia, contratados, afectacion)
        "perfil_personal_index": 0,    # Índice del perfil actual (0-4)
        
        # Datos básicos
        "nombre_prestador": None,
        "localidad": None,
        "referente": None,
        "tipo_servicio": None,
        
        # Comercialización
        "agua_tarifado": None,
        "cloacas_tarifado": None,
        
        # Personal (diccionario anidado)
        "personal": {
            "Profesionales": {"dependencia": None, "contratados": None, "afectacion": None},
            "Técnicos": {"dependencia": None, "contratados": None, "afectacion": None},
            "Administrativos": {"dependencia": None, "contratados": None, "afectacion": None},
            "Obreros": {"dependencia": None, "contratados": None, "afectacion": None},
            "Otros": {"dependencia": None, "contratados": None, "afectacion": None},
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
    
    # PASO 0: Presentación y Razón Social
    if paso == 0:
        prompt = (
            "¡Hola! 👋 Te damos la bienvenida al asistente virtual para el Relevamiento Anual de Prestadores. "
            "Este año queremos ayudarte a cargar los datos de forma rápida. ¿Arrancamos? \n\n"
            "Vamos a registrar algunos datos. Para empezar, escribí el *Nombre o Razón Social* de la institución prestadora.\n\n"
            "💡 Tip: Si en alguna de las preguntas técnicas o numéricas no tenés el dato exacto a mano, "
            "no te preocupes; podés responder con la palabra *'siguiente'* para saltarla y continuar con el cuestionario."
        )
        return paso, prompt
    
    # PASO 1: Localidad
    elif paso == 1:
        prompt = "¿A qué *Localidad o Paraje* pertenece?"
        return paso, prompt
    
    # PASO 2: Referente
    elif paso == 2:
        prompt = "¿Cuál es el nombre del *referente o contacto principal* de la carga?"
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
    
    # PASO 3.3: Iniciar Personal (Paso unificado)
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
    
    # PASO 25: Final / Despedida
    elif paso == 25:
        return generar_mensaje_final(datos)
    
    return paso, "Error: paso desconocido."

def obtener_paso_personal(datos):
    """
    Maneja el módulo dinámico de Personal.
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
    
    elif paso_personal == "afectacion":
        # Verificar si hay personal en este perfil
        personal_datos = datos["personal"][perfil_actual]
        total_personal = (personal_datos["dependencia"] or 0) + (personal_datos["contratados"] or 0)
        
        # Si el total es 0 o tipo_servicio es único (no ambos), saltear el % de afectación
        if total_personal == 0 or tipo_servicio != TIPO_SERVICIO_AMBOS:
            datos["personal"][perfil_actual]["afectacion"] = 100 if total_personal > 0 else 0
            
            # Avanzar al siguiente perfil o terminar personal
            datos["perfil_personal_index"] += 1
            if datos["perfil_personal_index"] < len(PERFILES_PERSONAL):
                datos["paso_personal_actual"] = "dependencia"
                # NO modificamos paso_actual, permanece en 3.3
                return obtener_paso_personal(datos)
            else:
                # Personal completado, transicionar al paso 4
                datos["paso_actual"] = 4
                datos["paso_personal_actual"] = None  # Limpiar para evitar confusiones
                return obtener_proximo_paso(datos)
        
        # Si hay personal y tipo_servicio es AMBOS, preguntar el %
        prompt = f"*{perfil_actual}*: ¿Qué % de afectación al servicio? (0-100)"
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
        # paso_actual permanece en 3.3
    
    elif paso_personal == "contratados":
        datos["personal"][perfil_actual]["contratados"] = valor
        datos["paso_personal_actual"] = "afectacion"
        
        total_personal = (datos["personal"][perfil_actual]["dependencia"] or 0) + (valor if valor is not None else 0)
        
        # Si no hay personal o servicio no es ambos, asignar automáticamente y avanzar de perfil
        if total_personal == 0 or tipo_servicio != TIPO_SERVICIO_AMBOS:
            datos["personal"][perfil_actual]["afectacion"] = 100 if total_personal > 0 else 0
            datos["perfil_personal_index"] += 1
            
            if datos["perfil_personal_index"] < len(PERFILES_PERSONAL):
                datos["paso_personal_actual"] = "dependencia"
                # paso_actual permanece en 3.3
            else:
                # Personal completado, transicionar al paso 4
                datos["paso_actual"] = 4
                datos["paso_personal_actual"] = None
    
    elif paso_personal == "afectacion":
        if valor is not None:
            if valor < 0 or valor > 100:
                return False, "❌ El porcentaje debe estar entre 0 y 100."
        
        datos["personal"][perfil_actual]["afectacion"] = valor
        datos["perfil_personal_index"] += 1
        
        if datos["perfil_personal_index"] < len(PERFILES_PERSONAL):
            datos["paso_personal_actual"] = "dependencia"
            # paso_actual permanece en 3.3
        else:
            # Personal completado, transicionar al paso 4
            datos["paso_actual"] = 4
            datos["paso_personal_actual"] = None
    
    guardar_datos(datos)
    return True, None

# ============================================================================
# PROCESAMIENTO DE RESPUESTAS
# ============================================================================

def procesar_respuesta(datos, respuesta_usuario):
    """
    Procesa la respuesta del usuario según el paso actual.
    Retorna: (éxito: bool, mensaje_respuesta: str)
    """
    paso = datos["paso_actual"]
    
    # PASO 0: Nombre del Prestador
    if paso == 0:
        nombre = respuesta_usuario.strip()
        if not nombre:
            return False, "❌ Por favor, escribí el nombre de la institución."
        datos["nombre_prestador"] = nombre
        datos["paso_actual"] = 1
        guardar_datos(datos)
        return True, f"✅ Perfecto, {nombre}. Continuemos..."
    
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
    
    # PASO 3.3: Módulo de Personal (paso UNIFICADO)
    elif paso == 3.3:
        exito, mensaje = procesar_respuesta_personal(datos, respuesta_usuario)
        if not exito:
            return False, mensaje
        return True, "✅ Anotado."
    
    # PASO 4: Conexiones de Agua
    elif paso == 4:
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
        datos["estado_registro"] = "Completo"
        guardar_datos(datos)
        return True, "✅ ¡Perfecto!"
    
    # PASO 25: Mensaje Final
    elif paso == 25:
        _, mensaje_final = generar_mensaje_final(datos)
        return True, mensaje_final
    
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
    
    _, proximo_prompt = obtener_proximo_paso(sesion_actual)
    
    return {
        "exito": True,
        "mensaje_respuesta": mensaje_respuesta,
        "mensaje_proximo_prompt": proximo_prompt,
        "datos_sesion": sesion_actual,
    }

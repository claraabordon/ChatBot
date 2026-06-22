# motor.py — v6 COMPLETO con guardado incremental y soporte para "No Sabe" (ns)
import json
from persistencia import guardar_datos

# Estado global de sesiones
sesiones = {}

# Lista ordenada de perfiles de personal según el ANEXO I
PERFILES_PERSONAL = ["Profesionales", "Técnicos", "Administrativos", "Obreros", "Otros"]

# -------------------------------------------------------------------
# Helpers de validación y conversión
# -------------------------------------------------------------------

def es_numero_entero_positivo(texto, incluir_cero=False):
    """Devuelve True si el texto es un entero válido."""
    texto = texto.strip()
    if not texto.isdigit():
        return False
    val = int(texto)
    if incluir_cero:
        return val >= 0
    return val >= 1

def extraer_primer_digito(texto):
    """Extrae el primer carácter si es dígito. Ej: '1- Agua' → '1'."""
    texto = texto.strip()
    if texto and texto[0].isdigit():
        return texto[0]
    return None

# -------------------------------------------------------------------
# Lógica de saltos condicionales generales
# -------------------------------------------------------------------

def calcular_siguiente_paso(paso_actual, tipo_servicio):
    """Determina el próximo paso principal según el tipo de servicio."""
    siguiente = paso_actual + 1

    while siguiente < 15:
        # Filtros de Infraestructura de Agua (4-7)
        if siguiente in {4, 5, 6, 7} and tipo_servicio == 2:
            siguiente += 1
        # Filtros de Reclamos específicos de Agua (11, 12)
        elif siguiente in {11, 12} and tipo_servicio == 2:
            siguiente += 1
            
        # Filtros de Infraestructura de Cloacas (8-10)
        elif siguiente in {8, 9, 10} and tipo_servicio == 1:
            siguiente += 1
        # Filtros de Reclamos específicos de Cloacas (13)
        elif siguiente in {13} and tipo_servicio == 1:
            siguiente += 1
            
        else:
            break

    return siguiente

# -------------------------------------------------------------------
# Inicialización de sesión
# -------------------------------------------------------------------

def inicializar_sesion(telefono):
    """Crea una sesión limpia para el teléfono dado."""
    sesiones[telefono] = {
        "paso": 0,
        "sub_paso_personal": 0,
        "indice_perfil_personal": 0,
        "datos": {"telefono": telefono},
        "finalizada": False,
        "esperando_confirmacion_reinicio": False,
    }

# -------------------------------------------------------------------
# Procesador principal
# -------------------------------------------------------------------

def procesar_mensaje(telefono, mensaje):
    mensaje = mensaje.strip()
    sesion_existe = telefono in sesiones
    
    # Mensaje de bienvenida unificado con tu texto modificado
    SALUDO_INICIAL = (
        "¡Hola! 👋 Te damos la bienvenida al asistente virtual para el Relevamiento Anual de Prestadores. "
        "Este año queremos ayudarte a cargar los datos de forma rápida. ¿Arrancamos? \n\n"
        "Vamos a registrar algunos datos. Para empezar, escribí el *Nombre o Razón Social* de la institución prestadora."
    )

    # Manejo de reinicio seguro de la sesión
    if mensaje.lower() in ("hola", "inicio", "reiniciar"):
        if sesion_existe and not sesiones[telefono].get("finalizada", True) and sesiones[telefono].get("paso", 0) > 0:
            sesiones[telefono]["esperando_confirmacion_reinicio"] = True
            return (
                "Tenés un relevamiento en curso. ¿Querés descartarlo y empezar de nuevo?\n"
                "Respondé *sí* para reiniciar o *no* para continuar donde dejaste."
            )
        inicializar_sesion(telefono)
        return SALUDO_INICIAL

    if sesion_existe and sesiones[telefono].get("esperando_confirmacion_reinicio"):
        if mensaje.lower() in ("sí", "si", "s", "yes"):
            inicializar_sesion(telefono)
            return "Sesión reiniciada.\n\n" + SALUDO_INICIAL
        elif mensaje.lower() in ("no", "n"):
            sesiones[telefono]["esperando_confirmacion_reinicio"] = False
            paso_actual = sesiones[telefono]["paso"]
            return "Perfecto, continuamos donde estabas. 👇\n\n" + avanzar_y_obtener_pregunta(telefono, solo_repetir=True)
        else:
            return "No entendí tu respuesta. Escribí *sí* para reiniciar o *no* para continuar."

    if not sesion_existe:
        inicializar_sesion(telefono)
        return SALUDO_INICIAL

    sesion = sesiones[telefono]
    paso = sesion["paso"]
    datos = sesion["datos"]

    if sesion.get("finalizada"):
        return "Este relevamiento ya fue completado. Escribí *hola* si querés registrar otro prestador."

    # --- FLUJO DE PASOS GENERALES (0 al 3) ---
    
    if paso == 0:
        datos["nombre_prestador"] = mensaje
        datos["estado_registro"] = "Incompleto"
        guardar_datos(datos)
        sesion["paso"] = 1
        return "¿A qué *Localidad o Paraje* pertenece?"

    elif paso == 1:
        datos["localidad"] = mensaje
        datos["estado_registro"] = "Incompleto"
        guardar_datos(datos)
        sesion["paso"] = 2
        return "¿Cuál es el nombre del *referente o contacto principal*?"

    elif paso == 2:
        datos["referente"] = mensaje
        datos["estado_registro"] = "Incompleto"
        guardar_datos(datos)
        sesion["paso"] = 3
        return (
            "¿Qué tipo de servicio brinda?\n"
            "1 - Solo Agua\n"
            "2 - Solo Cloacas\n"
            "3 - Ambos\n\n"
            "Respondé solo con el número (por ejemplo: 1)."
        )

    elif paso == 3:
        digito = extraer_primer_digito(mensaje)
        if digito not in ("1", "2", "3"):
            return "Opción no reconocida. Respondé solo con 1, 2 o 3.\n\n1 - Solo Agua\n2 - Solo Cloacas\n3 - Ambos"
        datos["tipo_servicio"] = int(digito)
        
        sesion["paso"] = "PERSONAL"
        sesion["indice_perfil_personal"] = 0
        sesion["sub_paso_personal"] = 0
        return f"Perfecto. Ahora pasamos a la sección de *Personal / Recursos Humanos* 👥.\n\n¿Cuántos empleados *PROFESIONALES* tienen en **relación de dependencia**? (Si no tienen o no saben, respondé 0)."

    # --- MÓDULO DINÁMICO DE PERSONAL ---
    elif paso == "PERSONAL":
        idx_perfil = sesion["indice_perfil_personal"]
        sub_paso = sesion["sub_paso_personal"]
        perfil_actual = PERFILES_PERSONAL[idx_perfil]
        prefijo_clave = f"personal_{perfil_actual.lower()}"

        # FIX 1: Corrección de sintaxis en el sub_paso == 0
        if sub_paso == 0:
            if not es_numero_entero_positivo(mensaje, incluir_cero=True):
                return f"Por favor, ingresá un número válido.\n\n¿Cuántos empleados *{perfil_actual.upper()}* tienen en **relación de dependencia**? (Respondé un número o 0)."
            datos[f"{prefijo_clave}_dependencia"] = int(mensaje)
            
            # FIX 2: Guardado incremental en personal
            datos["estado_registro"] = "Incompleto"
            guardar_datos(datos)
            
            sesion["sub_paso_personal"] = 1
            return f"¿Cuántos empleados *{perfil_actual.upper()}* tienen **contratados**? (Respondé un número o 0)."

        elif sub_paso == 1:
            if not es_numero_entero_positivo(mensaje, incluir_cero=True):
                return f"Por favor, ingresá un número válido.\n\n¿Cuántos empleados *{perfil_actual.upper()}* tienen **contratados**? (Respondé un número o 0)."
            datos[f"{prefijo_clave}_contratados"] = int(mensaje)
            
            # FIX 2: Guardado incremental en personal
            datos["estado_registro"] = "Incompleto"
            guardar_datos(datos)
            
            total_perfil = datos[f"{prefijo_clave}_dependencia"] + datos[f"{prefijo_clave}_contratados"]
            
            if total_perfil > 0:
                sesion["sub_paso_personal"] = 2
                return f"¿Qué **porcentaje (%) de afectación** promedio tienen los empleados *{perfil_actual.upper()}* asignado a los servicios sanitarios? (Ej: 80)."
            else:
                datos[f"{prefijo_clave}_afectacion_pct"] = 0
                guardar_datos(datos)
                return avanzar_perfil_personal(sesion, datos)

        elif sub_paso == 2:
            if not es_numero_entero_positivo(mensaje, incluir_cero=True) or int(mensaje) > 100:
                return f"Por favor, ingresá un porcentaje válido entre 0 y 100.\n\n¿Qué **porcentaje (%) de afectación** promedio tienen los empleados *{perfil_actual.upper()}*?"
            datos[f"{prefijo_clave}_afectacion_pct"] = int(mensaje)
            
            # FIX 2: Guardado incremental en personal
            datos["estado_registro"] = "Incompleto"
            guardar_datos(datos)
            
            return avanzar_perfil_personal(sesion, datos)

    # --- PASOS NUMÉRICOS TÉCNICOS Y RECLAMOS (4 al 14) ---
    elif paso in range(4, 15):
        # FIX 3: Soportar la palabra "ns" o "no sabe" como equivalente a 0 para no trabar el flujo
        valor_procesado = mensaje.lower().strip()
        if valor_procesado in ("ns", "no sabe", "no se"):
            valor_numerico = 0
        elif es_numero_entero_positivo(mensaje, incluir_cero=True):
            valor_numerico = int(mensaje)
        else:
            return "Ese valor no parece válido. Por favor ingresá un número entero, 0 o escribí *ns* si no sabés el dato.\n\n" + avanzar_y_obtener_pregunta(telefono, solo_repetir=True)

        claves = {
            4:  "conexiones_agua",
            5:  "habitantes_agua",
            6:  "caudal_agua_m3dia",
            7:  "empleados_agua",
            8:  "conexiones_cloacas",
            9:  "habitantes_cloacas",
            10: "caudal_cloacas_m3dia",
            11: "reclamos_falta_presion",
            12: "reclamos_escape_calzada_vereda",
            13: "reclamos_obstruccion_desborde_cloacal",
            14: "cortes_servicio_falta_pago"
        }
        datos[claves[paso]] = valor_numerico

        tipo_servicio = datos.get("tipo_servicio", 3)
        siguiente = calcular_siguiente_paso(paso, tipo_servicio)
        sesion["paso"] = siguiente

        if siguiente == 15:
            datos["estado_registro"] = "Completo"
            guardar_datos(datos)
            sesion["finalizada"] = True
            return (
                "¡Gracias! 🎉 Los datos del relevamiento anual (incluyendo el módulo de atención al usuario) fueron registrados correctamente.\n\n"
                "Si necesitás cargar otro prestador, simplemente escribí *hola* para volver a comenzar."
            )
            
        # Si no es el último paso, guardamos el avance como Incompleto y seguimos
        datos["estado_registro"] = "Incompleto"
        guardar_datos(datos)

        return avanzar_y_obtener_pregunta(telefono, solo_repetir=True)

    return "No entendí tu mensaje. Escribí *hola* para comenzar."

# -------------------------------------------------------------------
# Helpers de navegación interna
# -------------------------------------------------------------------

def avanzar_perfil_personal(sesion, datos):
    sesion["indice_perfil_personal"] += 1
    sesion["sub_paso_personal"] = 0
    idx = sesion["indice_perfil_personal"]

    if idx < len(PERFILES_PERSONAL):
        siguiente_perfil = PERFILES_PERSONAL[idx]
        return f"Entendido. Pasemos al siguiente perfil.\n\n¿Cuántos empleados *{siguiente_perfil.upper()}* tienen en **relación de dependencia**? (Si no tienen, respondé 0)."
    else:
        tipo_servicio = datos.get("tipo_servicio", 3)
        primer_paso_tecnico = calcular_siguiente_paso(3, tipo_servicio)
        sesion["paso"] = primer_paso_tecnico
        return avanzar_y_obtener_pregunta(sesion["datos"]["telefono"], solo_repetir=True)

def avanzar_y_obtener_pregunta(telefono, solo_repetir=False):
    sesion = sesiones[telefono]
    paso = sesion["paso"]
    
    prompts = {
        4:  "¿Cuántas *conexiones de agua* activas tiene el sistema actualmente?",
        5:  "¿A cuántos *habitantes* abastece efectivamente con agua potable?",
        6:  "¿Cuál es el *caudal diario de agua* promedio liberado a la red (en m³/día)?",
        7:  "¿Cuántos empleados trabajan específicamente en el día a día operativo del área de agua?",
        8:  "¿Cuántas *conexiones cloacales* activas tiene la red actualmente?",
        9:  "¿Cuántos *habitantes* están conectados efectivamente a la red de desagües cloacales?",
        10: "¿Cuál es el *caudal diario cloacal* promedio recolectado/tratado (en m³/día)?",
        11: "Pasamos al módulo de Reclamos. 📞 ¿Cuántos reclamos registraron en el último año por *Falta de presión de agua*? (Si fue ninguno o no sabés, respondé 0 o *ns*).",
        12: "¿Cuántos reclamos registraron en el último año por *Escapes o Fugas de agua* en calzada o vereda?",
        13: "¿Cuántos reclamos registraron en el último año por *Obstrucciones domiciliarias o desbordes cloacales*?",
        14: "Por último, en relación a Facturación: ¿Cuántos *cortes efectivos del servicio por falta de pago* realizaron en el último año?"
    }
    return prompts.get(paso, "Procediendo con el cuestionario...")

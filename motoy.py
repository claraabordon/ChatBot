# motor.py — v2 con fixes de validación, reinicio seguro y control de cero

import json
from persistencia import guardar_datos

# -------------------------------------------------------------------
# Estado global de sesiones
# { telefono: { "paso": int, "datos": {}, "finalizada": bool,
#               "esperando_confirmacion_reinicio": bool } }
# -------------------------------------------------------------------
sesiones = {}
<br/>

# -------------------------------------------------------------------
# Helpers de validación
# -------------------------------------------------------------------

def es_numero_entero_positivo(texto):
    """
    Devuelve True si el texto es un entero >= 1.
    Rechaza cero, negativos, decimales y texto libre.
    """
    texto = texto.strip()
    if not texto.isdigit():
        return False
    return int(texto) >= 1
<br/>

def extraer_primer_digito(texto):
    """Extrae el primer carácter si es dígito. Ej: '1- Agua' → '1'."""
    texto = texto.strip()
    if texto and texto[0].isdigit():
        return texto[0]
    return None
<br/>

# -------------------------------------------------------------------
# Prompts por paso
# -------------------------------------------------------------------

def obtener_prompt(paso, datos=None):
    """Devuelve el texto de pregunta correspondiente al paso."""
    if datos is None:
        datos = {}

    prompts = {
        0: (
            "¡Hola! 👋 Te damos la bienvenida al asistente virtual para el Relevamiento Anual de Prestadores. Este año queremos ayudarte a cargar los datos de forma rápida. ¿Arrancamos? \n"
            "Vamos a registrar algunos datos. Para empezar, escribí el Nombre o Razón Social de la institución prestadora."
        ),
        1: "¿A qué Localidad o Paraje pertenece?",
        2: "¿Cuál es el nombre del referente o contacto principal?",
        3: (
            "¿Qué tipo de servicio brinda?\n"
            "1 - Solo Agua\n"
            "2 - Solo Cloacas\n"
            "3 - Ambos\n\n"
            "Respondé con el número (por ejemplo: 1)."
        ),
        4:  "¿Cuántas conexiones de agua tiene actualmente?",
        5:  "¿Cuántos habitantes abastece con agua?",
        6:  "¿Cuál es el caudal diario de agua (en m³/día)?",
        7:  "¿Cuántos empleados trabajan en el área de agua?",
        8:  "¿Cuántas conexiones cloacales tiene actualmente?",
        9:  "¿Cuántos habitantes están conectados a la red cloacal?",
        10: "¿Cuál es el caudal diario cloacal (en m³/día)?",
        11: (
            "¡Gracias! 🎉 Los datos fueron registrados correctamente.\n"
            "Si necesitás hacer otro relevamiento, escribí hola para comenzar."
        ),
    }
    return prompts.get(paso, "Paso no reconocido.")
<br/>

# -------------------------------------------------------------------
# Mensajes de error reutilizables
# -------------------------------------------------------------------

ERROR_NUMERICO = (
    "Ese valor no parece válido. Por favor ingresá un número entero mayor a cero "
    "(por ejemplo: 150).\n\n"
)

ERROR_TIPO_SERVICIO = (
    "Opción no reconocida. Respondé solo con 1, 2 o 3 (por ejemplo: 1).\n\n"
    "1 - Solo Agua\n"
    "2 - Solo Cloacas\n"
    "3 - Ambos"
)
<br/>

# -------------------------------------------------------------------
# Lógica de saltos condicionales
# -------------------------------------------------------------------

def calcular_siguiente_paso(paso_actual, tipo_servicio):
    """
    Determina el próximo paso según el tipo de servicio:
      1 = Solo Agua    → pasos 4–7, salta 8–10
      2 = Solo Cloacas → salta 4–7, pasos 8–10
      3 = Ambos        → pasos 4–10
    """
    pasos_agua    = {4, 5, 6, 7}
    pasos_cloacas = {8, 9, 10}

    siguiente = paso_actual + 1

    while siguiente < 11:
        if siguiente in pasos_agua and tipo_servicio == 2:
            siguiente += 1
        elif siguiente in pasos_cloacas and tipo_servicio == 1:
            siguiente += 1
        else:
            break

    return siguiente
<br/>

# -------------------------------------------------------------------
# Inicialización de sesión
# -------------------------------------------------------------------

def inicializar_sesion(telefono):
    """Crea una sesión limpia para el teléfono dado."""
    sesiones[telefono] = {
        "paso": 0,
        "datos": {"telefono": telefono},
        "finalizada": False,
        "esperando_confirmacion_reinicio": False,
    }
<br/>

# -------------------------------------------------------------------
# Procesador principal
# -------------------------------------------------------------------

def procesar_mensaje(telefono, mensaje):
    """
    Punto de entrada principal.
    Recibe el teléfono del usuario y el texto del mensaje.
    Devuelve el texto que debe enviarse como respuesta.
    """
    mensaje = mensaje.strip()
    sesion_existe = telefono in sesiones
    sesion = sesiones.get(telefono, {})

    # --- FIX 3: Confirmación antes de reiniciar sesión activa ---
    if mensaje.lower() in ("hola", "inicio", "reiniciar"):
        sesion_activa = (
            sesion_existe
            and not sesion.get("finalizada", True)
            and sesion.get("paso", 0) > 0
        )
        if sesion_activa:
            sesiones[telefono]["esperando_confirmacion_reinicio"] = True
            return (
                "Tenés un relevamiento en curso. "
                "¿Querés descartarlo y empezar de nuevo?\n"
                "Respondé sí para reiniciar o no para continuar donde dejaste."
            )
        # Sin sesión activa: iniciar directamente
        inicializar_sesion(telefono)
        return obtener_prompt(0)

    # --- Manejo de respuesta a confirmación de reinicio ---
    if sesion.get("esperando_confirmacion_reinicio"):
        if mensaje.lower() in ("sí", "si", "s", "yes"):
            inicializar_sesion(telefono)
            return obtener_prompt(0)
        elif mensaje.lower() in ("no", "n"):
            sesiones[telefono]["esperando_confirmacion_reinicio"] = False
            paso_actual = sesiones[telefono]["paso"]
            return (
                "Perfecto, continuamos donde estabas. 👇\n\n"
                + obtener_prompt(paso_actual, sesiones[telefono]["datos"])
            )
        else:
            return (
                "No entendí tu respuesta. "
                "Escribí sí para reiniciar o no para continuar."
            )

    # --- Sin sesión: iniciar ---
    if not sesion_existe:
        inicializar_sesion(telefono)
        return obtener_prompt(0)

    paso  = sesion["paso"]
    datos = sesion["datos"]

    # --- Sesión ya finalizada ---
    if sesion.get("finalizada"):
        return (
            "Este relevamiento ya fue completado. "
            "Escribí hola si querés registrar otro prestador."
        )

    # --- Paso 0: Nombre del prestador ---
    if paso == 0:
        datos["nombre_prestador"] = mensaje
        sesion["paso"] = 1
        return obtener_prompt(1)

    # --- Paso 1: Localidad ---
    elif paso == 1:
        datos["localidad"] = mensaje
        sesion["paso"] = 2
        return obtener_prompt(2)

    # --- Paso 2: Nombre del referente ---
    elif paso == 2:
        datos["referente"] = mensaje
        sesion["paso"] = 3
        return obtener_prompt(3)

    # --- Paso 3: Tipo de servicio ---
    elif paso == 3:
        digito = extraer_primer_digito(mensaje)
        if digito not in ("1", "2", "3"):
            return ERROR_TIPO_SERVICIO  # no avanza el paso
        tipo = int(digito)
        datos["tipo_servicio"] = tipo
        siguiente = calcular_siguiente_paso(3, tipo)
        sesion["paso"] = siguiente
        return obtener_prompt(siguiente, datos)

    # --- Pasos 4–10: Datos numéricos ---
    elif paso in range(4, 11):
        # FIX 1 y 2: valida entero mayor a cero
        if not es_numero_entero_positivo(mensaje):
            return ERROR_NUMERICO + obtener_prompt(paso, datos)  # no avanza

        claves = {
            4:  "conexiones_agua",
            5:  "habitantes_agua",
            6:  "caudal_agua_m3dia",
            7:  "empleados_agua",
            8:  "conexiones_cloacas",
            9:  "habitantes_cloacas",
            10: "caudal_cloacas_m3dia",
        }
        datos[claves[paso]] = int(mensaje)

        tipo_servicio = datos.get("tipo_servicio", 3)
        siguiente = calcular_siguiente_paso(paso, tipo_servicio)
        sesion["paso"] = siguiente

        if siguiente == 11:
            guardar_datos(datos)
            sesion["finalizada"] = True
            return obtener_prompt(11)

        return obtener_prompt(siguiente, datos)

    # --- Fallback ---
    return "No entendí tu mensaje. Escribí hola para comenzar."

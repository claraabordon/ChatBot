# persistencia.py — v2 con Guardado Incremental Inteligente
import json
import os

def guardar_datos(datos):
    """
    Guarda o actualiza las respuestas de un prestador en un archivo JSON local.
    Si el teléfono ya existe, sobrescribe sus datos para mantener un único registro por prestador.
    """
    archivo = "respuestas_prestadores.json"
    
    # 1. Definir el estado del registro según el paso actual en el motor
    # Si el motor ya marcó la sesión como finalizada, es "Completo", sino es "Incompleto"
    # Nota: También podés pasar un parámetro extra, pero chequear el flag 'finalizada' es súper seguro.
    
    # 2. Leer los datos existentes del archivo
    if os.path.exists(archivo):
        with open(archivo, "r", encoding="utf-8") as f:
            try:
                lista_datos = json.load(f)
            except json.JSONDecodeError:
                lista_datos = []
    else:
        lista_datos = []

    # 3. Buscar si este número de teléfono ya empezó a cargar datos antes
    telefono_actual = datos.get("telefono")
    encontrado = False
    
    for i, registro in enumerate(lista_datos):
        if registro.get("telefono") == telefono_actual:
            # ¡Ya existe! Actualizamos los datos acumulados sobre la misma fila
            # Mantenemos lo que ya tenía y le acoplamos lo nuevo
            lista_datos[i].update(datos)
            encontrado = True
            break
            
    if not encontrado:
        # Es la primera pregunta que responde: creamos un registro nuevo
        lista_datos.append(datos)
    
    # 4. Escribir los cambios de forma ordenada en el disco
    with open(archivo, "w", encoding="utf-8") as f:
        json.dump(lista_datos, f, ensure_ascii=False, indent=4)

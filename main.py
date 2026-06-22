from motor import procesar_mensaje

def simular_chat():
    # Usamos un número de teléfono de prueba simulado
    telefono_prueba = "5493421234567"
    
    print("==================================================")
    print("   SIMULADOR DE BOT DE WHATSAPP (RELEVAMIENTO)    ")
    print("==================================================")
    print("Escribí 'hola' para arrancar o 'salir' para cerrar.\n")
    
    while True:
        mensaje_usuario = input("Tú: ")
        
        if mensaje_usuario.strip().lower() == "salir":
            print("Simulación terminada.")
            break
            
        # Llamamos al procesador del motor
        respuesta_bot = procesar_mensaje(telefono_prueba, mensaje_usuario)
        
        print(f"\nBot: {respuesta_bot}\n")
        print("--------------------------------------------------")

if __name__ == "__main__":
    simular_chat()

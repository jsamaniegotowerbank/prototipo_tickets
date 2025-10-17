import streamlit as st
import google.generativeai as genai
import os
from datetime import datetime
from dotenv import load_dotenv
from conexion_api_jira import crear_ticket_jira, obtener_tipos_issue

# Cargar variables de entorno
load_dotenv()

# Configurar la página
st.set_page_config(page_title="Chatbot de Soporte", page_icon="🤖")

# Configurar Gemini
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
model = genai.GenerativeModel('gemini-2.0-flash-exp')

def inicializar_chat():
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": "¡Hola! Soy tu asistente de soporte. ¿En qué puedo ayudarte hoy?"}
        ]
    if "ticket_creado" not in st.session_state:
        st.session_state.ticket_creado = False

def mostrar_panel_tickets():
    st.sidebar.title("📋 Tipos de Tickets")
    tipos = obtener_tipos_issue()
    
    for tipo_id, tipo_nombre in tipos.items():
        st.sidebar.write(f"**{tipo_nombre}** - ID: `{tipo_id}`")
    
    st.sidebar.info("Los problemas se escalan automáticamente como 'Incidencia Tecnológica'")

def determinar_tipo_issue(problema: str) -> str:
    """
    Función simple para determinar el tipo de issue basado en el problema
    """
    problema_lower = problema.lower()
    
    if any(palabra in problema_lower for palabra in ['acceso', 'permiso', 'login', 'contraseña']):
        return "10117"  # Acceso
    elif any(palabra in problema_lower for palabra in ['aws', 'cloud', 'nube']):
        return "10149"  # Solicitudes de AWS
    elif any(palabra in problema_lower for palabra in ['red', 'conexión', 'wifi', 'internet']):
        return "10150"  # Redes
    elif any(palabra in problema_lower for palabra in ['servidor', 'server']):
        return "10146"  # Solicitudes para servidores
    elif any(palabra in problema_lower for palabra in ['certificado', 'ssl', 'seguridad']):
        return "10147"  # Certificado de Seguridad
    else:
        return "10103"  # Incidencia Tecnológica (por defecto)

def generar_respuesta_gemini(prompt_usuario: str, historial: list) -> str:
    """
    Generar respuesta usando Gemini y crear ticket si es necesario
    """
    try:
        # Construir contexto para Gemini - PRIMERA RESPUESTA
        contexto_inicial = f"""
        Eres un asistente de soporte técnico. Analiza este problema y:
        1. Intenta dar una solución si es simple
        2. Si el problema es complejo, ofrece ayuda y sugiere crear un ticket
        
        Problema: {prompt_usuario}
        
        Responde de manera útil en español, siendo amable y profesional.
        """
        
        response = model.generate_content(contexto_inicial)
        respuesta_inicial = response.text
        
        # Determinar si necesita ticket
        necesita_ticket = any(palabra in prompt_usuario.lower() for palabra in 
                            ['error', 'no funciona', 'bug', 'problema', 'incidente', 'falla', 'roto', 'no prende', 'no enciende'])
        
        if necesita_ticket and not st.session_state.ticket_creado:
            # GENERAR RESUMEN PROFESIONAL PARA EL TICKET
            contexto_resumen = f"""
            Eres un técnico de soporte. Basándote en el siguiente problema reportado por el usuario, 
            genera un resumen técnico profesional para un ticket de Jira.
            
            PROBLEMA ORIGINAL: {prompt_usuario}
            RESPUESTA INICIAL DEL ASISTENTE: {respuesta_inicial}
            
            Instrucciones para el resumen:
            1. Crea un título claro y conciso (máximo 10 palabras)
            2. Escribe una descripción técnica profesional
            3. Incluye los síntomas específicos mencionados
            4. No incluyas saludos ni lenguaje informal
            5. Usa un tono profesional para que el equipo técnico entienda el problema
            
            Formato de respuesta:
            TÍTULO: [aquí el título resumido]
            DESCRIPCIÓN: [aquí la descripción técnica detallada]
            """
            
            response_resumen = model.generate_content(contexto_resumen)
            resumen_completo = response_resumen.text
            
            # Extraer título y descripción del resumen
            lineas = resumen_completo.split('\n')
            titulo = "Problema reportado por usuario"
            descripcion = resumen_completo
            
            for linea in lineas:
                if linea.startswith('TÍTULO:') or linea.startswith('TITULO:'):
                    titulo = linea.replace('TÍTULO:', '').replace('TITULO:', '').strip()
                elif linea.startswith('DESCRIPCIÓN:') or linea.startswith('DESCRIPCION:'):
                    descripcion = linea.replace('DESCRIPCIÓN:', '').replace('DESCRIPCION:', '').strip()
            
            # Si no se encontraron las secciones, usar el resumen completo como descripción
            if titulo == "Problema reportado por usuario":
                descripcion = resumen_completo
            
            # Determinar el tipo de issue
            tipo_issue_id = determinar_tipo_issue(prompt_usuario)
            
            # Crear el ticket con el resumen profesional
            resultado = crear_ticket_jira(
                summary=titulo[:100],  # Máximo 100 caracteres para el summary
                description=descripcion,
                issuetype_id=tipo_issue_id
            )
            
            if resultado["success"]:
                st.session_state.ticket_creado = True
                respuesta_final = f"{respuesta_inicial}\n\n🎫 **{resultado['message']}**"
                respuesta_final += f"\n\n📋 **Resumen del ticket:** {titulo}"
            else:
                respuesta_final = f"{respuesta_inicial}\n\n⚠️ **No pude crear el ticket. Error: {resultado['error']}**"
        else:
            respuesta_final = respuesta_inicial
        
        return respuesta_final
        
    except Exception as e:
        return f"Lo siento, ocurrió un error: {str(e)}"

def main():
    inicializar_chat()
    mostrar_panel_tickets()
    
    st.title("💬 Chatbot de Soporte - TowerBank")
    
    # Mostrar historial del chat
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Input del usuario
    if prompt := st.chat_input("Describe tu problema..."):
        # Agregar mensaje del usuario
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Generar respuesta
        with st.chat_message("assistant"):
            with st.spinner("Analizando el problema..."):
                respuesta = generar_respuesta_gemini(prompt, st.session_state.messages)
                st.markdown(respuesta)
                st.session_state.messages.append({"role": "assistant", "content": respuesta})

if __name__ == "__main__":
    main()
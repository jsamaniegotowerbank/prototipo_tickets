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
            {"role": "assistant", "content": "¡Hola! Soy tu asistente de soporte. Por favor, describe tu problema técnico."}
        ]
    if "ticket_creado" not in st.session_state:
        st.session_state.ticket_creado = False
    if "contador_mensajes" not in st.session_state:
        st.session_state.contador_mensajes = 0


def determinar_tipo_issue(descripcion_completa: str) -> str:
    """
    Determinar el tipo de issue basado en la descripción completa con lógica mejorada
    """
    descripcion_lower = descripcion_completa.lower()
    
    # PRIORIDAD: Problemas de hardware/equipos físicos
    if any(palabra in descripcion_lower for palabra in [
        'pc no prende', 'no enciende', 'no power', 'no enciende luces', 
        'fuente de alimentación', 'hardware', 'componente interno',
        'dell', 'optiplex', 'torre', 'computadora', 'equipo', 'laptop',
        'botón de encendido', 'cable de alimentación', 'interruptor trasero',
        'reinicio de energía', 'power cycle', 'no da señales de vida'
    ]):
        return "10103"  # Incidencia Tecnológica
    
    # REDES - solo si hay términos específicos de red
    elif any(palabra in descripcion_lower for palabra in [
        'wifi', 'red inalámbrica', 'ethernet', 'conexión de red', 
        'network', 'ping', 'latencia', 'velocidad de internet',
        'router', 'modem', 'switch', 'conectividad de red'
    ]) and not any(palabra in descripcion_lower for palabra in ['pc no prende', 'no enciende']):
        return "10150"  # Redes
    
    # ACCESO
    elif any(palabra in descripcion_lower for palabra in [
        'acceso', 'permiso', 'login', 'contraseña', 'credenciales',
        'usuario', 'password', 'cuenta', 'autenticación'
    ]):
        return "10117"  # Acceso
    
    # AWS
    elif any(palabra in descripcion_lower for palabra in [
        'aws', 'cloud', 'nube', 'bucket', 'ec2', 's3', 'lambda'
    ]):
        return "10149"  # Solicitudes de AWS
    
    # SERVIDORES
    elif any(palabra in descripcion_lower for palabra in [
        'servidor', 'server', 'apache', 'nginx', 'iis', 'base de datos'
    ]):
        return "10146"  # Solicitudes para servidores
    
    # SEGURIDAD
    elif any(palabra in descripcion_lower for palabra in [
        'certificado', 'ssl', 'seguridad', 'https', 'tls', 'encriptación'
    ]):
        return "10147"  # Certificado de Seguridad
    
    # POR DEFECTO - Incidencia Tecnológica
    else:
        return "10103"  # Incidencia Tecnológica

def generar_respuesta_gemini(prompt_usuario: str, historial: list) -> str:
    """
    Generar respuesta usando Gemini - VERSIÓN SIMPLIFICADA Y DIRECTA
    """
    try:
        # VERIFICAR PRIMERO si el usuario pide EXPLÍCITAMENTE crear ticket
        usuario_pide_ticket = any(phrase in prompt_usuario.lower() for phrase in 
                                 ['crea el ticket', 'crea ticket', 'crear ticket', 'haz el ticket', 
                                  'genera el ticket', 'abre un ticket', 'si, crea el ticket', 
                                  'si crea el ticket', 'confirmo', 'sí', 'si'])

        # Si el usuario pide ticket EXPLÍCITAMENTE, CREARLO INMEDIATAMENTE
        if usuario_pide_ticket and not st.session_state.ticket_creado:
            return crear_ticket_inmediato(historial, prompt_usuario)

        # Si YA se creó un ticket, no continuar la conversación
        if st.session_state.ticket_creado:
            return "El ticket ya fue creado. Nuestro equipo técnico se contactará contigo pronto."

        # Construir contexto conversacional MÁS DIRECTO
        contexto = f"""
        Eres un asistente de soporte técnico. Tu objetivo es:
        1. Hacer preguntas para entender el problema
        2. Proporcionar soluciones paso a paso
        3. Después de 3-4 intercambios, OFRECER crear un ticket claramente
        4. NO divagar - ser directo y útil

        Historial reciente:
        {historial[-4:]}  # Solo últimos 4 mensajes para contexto

        Último mensaje del usuario: {prompt_usuario}

        Responde de manera CONCISA y DIRECTA en español.
        Si es momento de ofrecer un ticket, di claramente: "¿Te gustaría que cree un ticket de soporte?"
        """

        response = model.generate_content(contexto)
        respuesta = response.text

        # Lógica SIMPLIFICADA para ofrecer ticket
        deberia_ofrecer_ticket = (
            st.session_state.contador_mensajes >= 3 and
            not st.session_state.ticket_creado and
            not usuario_pide_ticket and
            any(palabra in prompt_usuario.lower() for palabra in 
                ['sigue igual', 'no funciona', 'no sirve', 'persiste', 'no se soluciona'])
        )

        # Si es momento de OFRECER ticket, asegurarse de que la respuesta lo ofrezca
        if deberia_ofrecer_ticket and "ticket" not in respuesta.lower():
            respuesta += "\n\n¿Te gustaría que cree un ticket de soporte técnico para que un especialista revise tu caso?"

        return respuesta

    except Exception as e:
        return f"Lo siento, ocurrió un error: {str(e)}"
    
def crear_ticket_inmediato(historial: list, prompt_usuario: str) -> str:
    """
    Función para crear el ticket INMEDIATAMENTE - VERSIÓN MÁS ROBUSTA
    """
    try:
        # EXTRAER TODA LA CONVERSACIÓN
        conversacion_completa = "CONVERSACIÓN COMPLETA:\n"
        for mensaje in historial:
            rol = "Asistente" if mensaje["role"] == "assistant" else "Usuario"
            conversacion_completa += f"{rol}: {mensaje['content']}\n"
        
        conversacion_completa += f"Usuario: {prompt_usuario}"

        # GENERAR RESUMEN MÁS DIRECTO
        contexto_resumen = f"""
        ANALIZA esta conversación y crea un resumen para ticket técnico:

        {conversacion_completa}

        GENERA SOLO 2 LÍNEAS:
        LÍNEA 1: TÍTULO: [máximo 6 palabras]
        LÍNEA 2: DESCRIPCIÓN: [descripción técnica concisa]

        Ejemplo:
        TÍTULO: Problema conexión WiFi en Windows
        DESCRIPCIÓN: Usuario no puede conectarse a ninguna red WiFi. Se verificaron adaptador, controladores y configuración sin éxito. Equipo: Windows.
        """

        response_resumen = model.generate_content(contexto_resumen)
        resumen_completo = response_resumen.text

        # EXTRAER TÍTULO Y DESCRIPCIÓN DE FORMA MÁS SIMPLE
        titulo = "Problema técnico reportado"
        descripcion = conversacion_completa  # Por defecto, toda la conversación

        if "TÍTULO:" in resumen_completo:
            partes = resumen_completo.split("TÍTULO:")
            if len(partes) > 1:
                titulo_parte = partes[1].split("DESCRIPCIÓN:")[0].strip()
                titulo = titulo_parte
                
                if "DESCRIPCIÓN:" in resumen_completo:
                    desc_parte = resumen_completo.split("DESCRIPCIÓN:")[1].strip()
                    descripcion = desc_parte

        # CREAR EL TICKET REAL
        resultado = crear_ticket_jira(
            summary=titulo[:80],
            description=descripcion,
            issuetype_id="10103"  # Incidencia Tecnológica por defecto
        )

        if resultado["success"]:
            st.session_state.ticket_creado = True
            return f"✅ **Ticket creado: {resultado['ticket_key']}**\n\n**Asunto:** {titulo}\n\n**Descripción:** {descripcion[:150]}...\n\n🔧 **Nuestro equipo técnico te contactará pronto.**"
        else:
            return f"❌ **Error:** No se pudo crear el ticket. {resultado['error']}"

    except Exception as e:
        return f"❌ **Error:** No se pudo procesar la solicitud. {str(e)}"

def main():
    inicializar_chat()
    
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
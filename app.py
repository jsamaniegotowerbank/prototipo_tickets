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
            {"role": "assistant", "content": "¡Hola! Soy tu asistente de soporte técnico. Estoy aquí para ayudarte a resolver problemas con tus equipos y sistemas. Por favor, descríbeme el problema que estás experimentando con todo detalle."}
        ]
    if "ticket_creado" not in st.session_state:
        st.session_state.ticket_creado = False
    if "problema_detectado" not in st.session_state:
        st.session_state.problema_detectado = False
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
    Generar respuesta usando Gemini de manera conversacional y proactiva
    """
    try:
        # Incrementar contador de mensajes
        st.session_state.contador_mensajes += 1
        
        # Construir contexto conversacional MEJORADO
        contexto = f"""
        Eres un asistente de soporte técnico conversacional. Tu objetivo es:
        1. Hacer preguntas para entender completamente el problema
        2. Intentar soluciones paso a paso
        3. Ser proactivo y ofrecer crear un ticket cuando el problema sea complejo
        4. No esperar a que el usuario te pida crear el ticket
        5. Ser amable, paciente y profesional
        
        Historial de la conversación:
        {historial}
        
        Último mensaje del usuario: {prompt_usuario}
        
        Responde en español continuando la conversación naturalmente. 
        Si el problema es complejo y requiere intervención técnica, OFRECE crear un ticket.
        No digas "voy a crear el ticket" sin antes ofrecerlo al usuario.
        """
        
        response = model.generate_content(contexto)
        respuesta = response.text
        
        # Lógica MEJORADA para crear ticket - más proactiva
        deberia_ofrecer_ticket = (
            st.session_state.contador_mensajes >= 4 and  # Mínimo 4 intercambios
            not st.session_state.ticket_creado and
            any(palabra in (prompt_usuario.lower() + respuesta.lower()) for palabra in 
                ['complejo', 'técnico', 'hardware', 'fuente de alimentación', 'componente interno', 
                 'revisión técnica', 'equipo especializado', 'no funciona', 'no sirve', 'no se soluciona'])
        )
        
        # Verificar si Gemini OFRECE crear ticket (no solo lo menciona)
        ofrece_ticket_gemini = any(phrase in respuesta.lower() for phrase in 
                                  ['puedo crear un ticket', 'te gustaría que cree', 'puedo generar un ticket', 
                                   'deseas que cree', 'quieres que cree', 'puedo abrir un ticket'])
        
        # Verificar si el usuario EXPLÍCITAMENTE pide crear ticket
        usuario_pide_ticket = any(phrase in prompt_usuario.lower() for phrase in 
                                 ['crea el ticket', 'crea ticket', 'crear ticket', 'haz el ticket', 
                                  'genera el ticket', 'abre un ticket'])
        
        # CREAR TICKET si el usuario lo pide explícitamente O si es momento apropiado
        if (usuario_pide_ticket or (deberia_ofrecer_ticket and ofrece_ticket_gemini)) and not st.session_state.ticket_creado:
            # GENERAR RESUMEN COMPLETO DE LA CONVERSACIÓN
            contexto_resumen = f"""
            Eres un técnico de soporte. Analiza toda esta conversación y genera un resumen profesional para un ticket.
            
            CONVERSACIÓN COMPLETA:
            {historial}
            ÚLTIMO MENSAJE: {prompt_usuario}
            
            Instrucciones:
            1. Crea un TÍTULO claro y conciso (máximo 8 palabras)
            2. Escribe una DESCRIPCIÓN técnica que incluya:
               - Síntomas del problema específicos
               - Todos los pasos de solución ya intentados
               - Información del equipo/hardware
               - Datos de contacto del usuario si están disponibles
            3. Usa lenguaje técnico profesional
            4. Sé específico sobre los síntomas (ej: "no enciende luces" vs "no funciona")
            
            Formato de respuesta:
            TÍTULO: [título aquí]
            DESCRIPCIÓN: [descripción técnica detallada aquí]
            """
            
            response_resumen = model.generate_content(contexto_resumen)
            resumen_completo = response_resumen.text
            
            # Extraer título y descripción
            lineas = resumen_completo.split('\n')
            titulo = "Problema técnico reportado por usuario"
            descripcion = resumen_completo
            
            for linea in lineas:
                if linea.startswith('TÍTULO:') or linea.startswith('TITULO:'):
                    titulo = linea.replace('TÍTULO:', '').replace('TITULO:', '').strip()
                elif linea.startswith('DESCRIPCIÓN:') or linea.startswith('DESCRIPCION:'):
                    descripcion = linea.replace('DESCRIPCIÓN:', '').replace('DESCRIPCION:', '').strip()
            
            # Determinar tipo de issue MEJORADO
            tipo_issue_id = determinar_tipo_issue(descripcion + " " + str(historial))
            
            # Crear el ticket inmediatamente
            resultado = crear_ticket_jira(
                summary=titulo[:100],
                description=descripcion,
                issuetype_id=tipo_issue_id
            )
            
            if resultado["success"]:
                st.session_state.ticket_creado = True
                st.session_state.problema_detectado = True
                
                # Respuesta inmediata y directa
                respuesta = f"✅ **Ticket creado exitosamente: {resultado['ticket_key']}**\n\n"
                respuesta += f"📋 **Asunto:** {titulo}\n\n"
                respuesta += f"👤 **Reportado por:** Juan Samaniego\n"
                respuesta += f"📞 **Contacto:** 6221-5592\n"
                respuesta += f"💻 **Equipo:** Dell OptiPlex 3020\n\n"
                respuesta += f"⏰ **Nuestro equipo técnico se contactará contigo pronto.**\n\n"
                respuesta += f"🔧 **Tipo de incidencia:** {resultado.get('ticket_type', 'Incidencia Tecnológica')}"
            else:
                respuesta += f"\n\n❌ **Error al crear ticket:** {resultado['error']}"
        
        return respuesta
        
    except Exception as e:
        return f"Lo siento, ocurrió un error en el sistema: {str(e)}"

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
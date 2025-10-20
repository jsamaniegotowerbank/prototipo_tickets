import requests
import os
import json
from datetime import datetime
from typing import Dict, Any

def crear_ticket_jira(summary: str, description: str, issuetype_id: str = "10103") -> Dict[str, Any]:
    """
    Función para crear un ticket en Jira usando IDs específicos
    
    Args:
        summary: Título/resumen del ticket
        description: Descripción detallada del problema
        issuetype_id: ID del tipo de issue (por defecto: 10103 - Incidencia Tecnológica)
    
    Returns:
        Dict con el resultado de la operación
    """
    url = f"{os.getenv('JIRA_URL')}/rest/api/3/issue/"
    auth = (os.getenv('JIRA_EMAIL'), os.getenv('JIRA_API_TOKEN'))
    headers = {"Content-Type": "application/json"}
    
    fecha_creacion = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Mapeo de tipos de issue para referencia
    tipos_issue = {
        "10103": "Incidencia Tecnológica",
        "10118": "Solicitud Básica", 
        "10101": "Pase",
        "10052": "Reporte",
        "10117": "Acceso",
        "10146": "Solicitudes para servidores",
        "10147": "Certificado de Seguridad",
        "10149": "Solicitudes de AWS",
        "10150": "Redes",
        "10151": "Desarrollo operativo",
        "10346": "Estabilización",
        "10018": "Subtarea"
    }
    
    # 🔥 CORRECCIÓN: Limpiar el summary de saltos de línea
    summary_limpio = summary.replace('\n', ' ').replace('\r', ' ').strip()
    # También limitar la longitud por si acaso
    summary_limpio = summary_limpio[:100]
    
    # Payload corregido con la estructura exacta de Jira
    payload = {
        "fields": {
            "project": {
                "key": os.getenv('JIRA_PROJECT_KEY')
            },
            "summary": summary_limpio,  # 🔥 Usar el summary limpio aquí
            "description": {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [
                            {
                                "type": "text",
                                "text": description
                            }
                        ]
                    }
                ]
            },
            "issuetype": {
                "id": issuetype_id
            }
        }
    }
    
    try:
        print(f"[DEBUG] Creando ticket tipo: {tipos_issue.get(issuetype_id, issuetype_id)}")
        print(f"[DEBUG] Summary: {summary_limpio}")  # 🔥 Para debug
        response = requests.post(url, json=payload, auth=auth, headers=headers)
        
        if response.status_code == 201:
            data = response.json()
            return {
                "success": True,
                "ticket_id": data['id'],
                "ticket_key": data['key'],
                "ticket_type": tipos_issue.get(issuetype_id, issuetype_id),
                "message": f"✅ Ticket {data['key']} creado exitosamente - Tipo: {tipos_issue.get(issuetype_id, issuetype_id)}"
            }
        else:
            error_msg = f"Error {response.status_code}"
            try:
                error_data = response.json()
                error_msg += f": {error_data}"
            except:
                error_msg += f": {response.text}"
            
            return {
                "success": False,
                "error": error_msg
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": f"Error de conexión: {str(e)}"
        }

# Función auxiliar para obtener los tipos de issue disponibles
def obtener_tipos_issue():
    """
    Retorna diccionario con los tipos de issue disponibles
    """
    return {
        "10103": "Incidencia Tecnológica",
        "10118": "Solicitud Básica", 
        "10101": "Pase",
        "10052": "Reporte",
        "10117": "Acceso",
        "10146": "Solicitudes para servidores",
        "10147": "Certificado de Seguridad",
        "10149": "Solicitudes de AWS",
        "10150": "Redes",
        "10151": "Desarrollo operativo",
        "10346": "Estabilización",
        "10018": "Subtarea"
    }
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
INTEGRACIÓN GOOGLE CALENDAR
Sincroniza producciones planificadas y muestra disponibilidad de stock
"""

from datetime import datetime, timedelta
import os
import json

class IntegradorGoogleCalendar:
    """
    Integración con Google Calendar para planificación de producciones

    Requiere:
    - google-auth-oauthlib
    - google-auth-httplib2
    - google-api-python-client

    Setup:
    1. pip install google-auth-oauthlib google-auth-httplib2 google-api-python-client
    2. Crear proyecto en Google Cloud Console
    3. Descargar credentials.json
    4. Ejecutar script una vez para autorizar
    """

    def __init__(self, credentials_file='credentials.json'):
        self.credentials_file = credentials_file
        self.calendar_id = os.getenv('GOOGLE_CALENDAR_ID', 'primary')
        self.service = None
        self._inicializar()

    def _inicializar(self):
        """Inicializa la conexión con Google Calendar"""
        try:
            from google.auth.transport.requests import Request
            from google.oauth2.service_account import Credentials

            if os.path.exists(self.credentials_file):
                creds = Credentials.from_service_account_file(
                    self.credentials_file,
                    scopes=['https://www.googleapis.com/auth/calendar']
                )
                from googleapiclient.discovery import build
                self.service = build('calendar', 'v3', credentials=creds)
                print("✅ Google Calendar conectado")
            else:
                print("⚠️ credentials.json no encontrado. Ver documentación.")
        except Exception as e:
            print(f"⚠️ Error conectando Google Calendar: {e}")

    def crear_evento_produccion(self, producto, cantidad_kg, fecha_inicio, duración_horas=2):
        """
        Crea un evento en Google Calendar para una producción planificada

        Args:
            producto: Nombre del producto a producir
            cantidad_kg: Cantidad en kg
            fecha_inicio: datetime object o string ISO
            duración_horas: Duración estimada de la producción
        """
        if not self.service:
            return {'error': 'Google Calendar no configurado'}

        if isinstance(fecha_inicio, str):
            fecha_inicio = datetime.fromisoformat(fecha_inicio)

        fecha_fin = fecha_inicio + timedelta(hours=duración_horas)

        evento = {
            'summary': f'🏭 Producción: {producto} ({cantidad_kg} kg)',
            'description': f'''
Producción Planificada
Producto: {producto}
Cantidad: {cantidad_kg} kg
Duración estimada: {duración_horas} horas

Sistema: ÁNIMUS Lab + Espagiria
            ''',
            'start': {
                'dateTime': fecha_inicio.isoformat(),
                'timeZone': 'America/Bogota'
            },
            'end': {
                'dateTime': fecha_fin.isoformat(),
                'timeZone': 'America/Bogota'
            },
            'colorId': '11',  # Tomato color
            'reminders': {
                'useDefault': False,
                'overrides': [
                    {'method': 'email', 'minutes': 24 * 60},  # 1 día antes
                    {'method': 'popup', 'minutes': 30}  # 30 min antes
                ]
            }
        }

        try:
            evento_creado = self.service.events().insert(
                calendarId=self.calendar_id,
                body=evento
            ).execute()
            return {
                'exito': True,
                'evento_id': evento_creado['id'],
                'html_link': evento_creado['htmlLink']
            }
        except Exception as e:
            return {'error': str(e)}

    def obtener_producciones_planificadas(self, dias=30):
        """Obtiene las producciones planificadas de los próximos días"""
        if not self.service:
            return []

        ahora = datetime.now()
        fecha_inicio = ahora.isoformat() + 'Z'
        fecha_fin = (ahora + timedelta(days=dias)).isoformat() + 'Z'

        try:
            eventos = self.service.events().list(
                calendarId=self.calendar_id,
                timeMin=fecha_inicio,
                timeMax=fecha_fin,
                q='Producción',
                singleEvents=True,
                orderBy='startTime'
            ).execute()

            producciones = []
            for evento in eventos.get('items', []):
                producciones.append({
                    'titulo': evento['summary'],
                    'fecha': evento['start'].get('dateTime', evento['start'].get('date')),
                    'descripcion': evento.get('description', ''),
                    'link': evento.get('htmlLink', '')
                })

            return producciones
        except Exception as e:
            print(f"Error obteniendo eventos: {e}")
            return []

    def calcular_disponibilidad_stock(self, inventario, producciones_planificadas, formulas):
        """
        Calcula disponibilidad de stock para las producciones planificadas

        Returns: {
            'disponible': True/False,
            'fecha_disponible': datetime cuando hay stock disponible,
            'materiales_faltantes': [...]
        }
        """
        disponibilidad = []

        for produccion in producciones_planificadas:
            # Parsear producto y cantidad de la descripción
            # Formato: "Producto: XXX\nCantidad: YYY kg"
            desc = produccion.get('descripcion', '')
            lineas = desc.split('\n')

            producto = None
            cantidad_kg = 0

            for linea in lineas:
                if 'Producto:' in linea:
                    producto = linea.split('Producto:')[1].strip()
                if 'Cantidad:' in linea:
                    cantidad_kg = float(linea.split('Cantidad:')[1].split('kg')[0].strip())

            if not producto or producto not in formulas:
                continue

            # Verificar si hay stock para esta producción
            formula = formulas[producto]
            materiales_faltantes = []

            for ingrediente in formula:
                codigo = ingrediente['codigo']
                cantidad_requerida = ingrediente['cantidad'] * (cantidad_kg / 12.0)

                if codigo not in inventario or inventario[codigo] < cantidad_requerida:
                    stock_actual = inventario.get(codigo, 0)
                    materiales_faltantes.append({
                        'nombre': ingrediente['nombre'],
                        'codigo': codigo,
                        'requerido': cantidad_requerida,
                        'actual': stock_actual,
                        'falta': cantidad_requerida - stock_actual
                    })

            disponibilidad.append({
                'produccion': produccion,
                'disponible': len(materiales_faltantes) == 0,
                'materiales_faltantes': materiales_faltantes
            })

        return disponibilidad

    def mostrar_alerta_si_falta_stock(self, disponibilidad):
        """Genera alertas si no hay stock para producciones planificadas"""
        alertas = []

        for item in disponibilidad:
            if not item['disponible']:
                fecha = item['produccion']['fecha']
                produccion = item['produccion']['titulo']
                materiales = item['materiales_faltantes']

                alerta = {
                    'criticidad': 'CRÍTICA',
                    'titulo': f'Stock insuficiente para {produccion}',
                    'fecha': fecha,
                    'materiales_faltantes': materiales,
                    'accion': 'Requiere compra urgente antes de esta fecha'
                }
                alertas.append(alerta)

        return alertas

    def sugerir_fecha_produccion(self, producto, cantidad_kg, formulas, inventario):
        """
        Sugiere la fecha más próxima en que se puede producir un producto
        basado en la disponibilidad de stock
        """
        if producto not in formulas:
            return {'error': 'Producto no encontrado'}

        formula = formulas[producto]
        dias_requerido = 0

        # Encontrar el material más crítico (el que tarde más en reabastecerse)
        for ingrediente in formula:
            codigo = ingrediente['codigo']
            cantidad_requerida = ingrediente['cantidad'] * (cantidad_kg / 12.0)
            stock_actual = inventario.get(codigo, 0)

            if stock_actual < cantidad_requerida:
                falta = cantidad_requerida - stock_actual
                # Asumir ~50kg por día de reabastecimiento
                dias_falta = int((falta / 1000) / 50) + 1
                dias_requerido = max(dias_requerido, dias_falta)

        fecha_sugerida = datetime.now() + timedelta(days=dias_requerido)

        return {
            'producto': producto,
            'cantidad_kg': cantidad_kg,
            'fecha_sugerida': fecha_sugerida.isoformat(),
            'dias_espera': dias_requerido,
            'razon': f'Reabastecimiento esperado en {dias_requerido} días'
        }


# Ejemplo de uso
if __name__ == '__main__':
    integrador = IntegradorGoogleCalendar()

    # Crear evento de producción
    resultado = integrador.crear_evento_produccion(
        producto='RENOVA C',
        cantidad_kg=12,
        fecha_inicio=datetime.now() + timedelta(days=1),
        duración_horas=2
    )
    print(f"Evento creado: {resultado}")

    # Obtener producciones planificadas
    producciones = integrador.obtener_producciones_planificadas(dias=30)
    print(f"Producciones planificadas: {len(producciones)}")

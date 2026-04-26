#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SISTEMA DE NOTIFICACIONES POR EMAIL
Para alertas de stock bajo, producciones completadas, etc.
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from datetime import datetime
import logging
import os
import threading

logger = logging.getLogger('notificaciones')

class SistemaNotificaciones:
    def __init__(self, email_remitente="", contraseña="", smtp_server="", smtp_port=0):
        """
        Inicializa el sistema de notificaciones.
        Lee env vars en orden de prioridad:
          EMAIL_REMITENTE > SMTP_EMAIL  (remitente)
          EMAIL_PASSWORD  > SMTP_PASSWORD  (contrasena)
          SMTP_SERVER  (default smtp.gmail.com)
          SMTP_PORT    (default 587)
        Genera 'Contrasena de Aplicacion' en:
          https://myaccount.google.com/apppasswords
        """
        self.email_remitente = (
            email_remitente
            or os.getenv('EMAIL_REMITENTE', '')
            or os.getenv('SMTP_EMAIL', '')
        )
        self.contraseña = (
            contraseña
            or os.getenv('EMAIL_PASSWORD', '')
            or os.getenv('SMTP_PASSWORD', '')
        )
        self.smtp_server = (
            smtp_server
            or os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        )
        self.smtp_port = (
            smtp_port
            or int(os.getenv('SMTP_PORT', '587'))
        )
        self.historial = []

    def enviar_alerta_stock_bajo(self, material_nombre, codigo, stock_actual_kg, umbral_kg=10):
        """Envía alerta cuando el stock cae por debajo del umbral"""
        asunto = f"🚨 ALERTA: Stock bajo de {material_nombre}"

        body = f"""
        <html>
        <body style="font-family: Arial, sans-serif;">
            <div style="background: #ffebee; padding: 20px; border-radius: 8px;">
                <h2 style="color: #c62828;">⚠️ ALERTA DE STOCK BAJO</h2>

                <p><strong>Material:</strong> {material_nombre}</p>
                <p><strong>Código:</strong> {codigo}</p>
                <p><strong>Stock Actual:</strong> {stock_actual_kg:.1f} kg</p>
                <p><strong>Umbral:</strong> {umbral_kg} kg</p>
                <p><strong>Fecha/Hora:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>

                <hr>
                <p style="color: #666; font-size: 12px;">
                    Este es un mensaje automático del Sistema de Inventarios ÁNIMUS Lab + Espagiria.<br>
                    Por favor revisa el inventario y considera hacer una compra urgente.
                </p>
            </div>
        </body>
        </html>
        """

        self._enviar_email(asunto, body)
        self.historial.append({
            'tipo': 'stock_bajo',
            'material': material_nombre,
            'timestamp': datetime.now().isoformat()
        })

    def enviar_notificacion_produccion(self, producto, cantidad_kg, materiales_deducidos):
        """Notifica cuando se registra una producción"""
        asunto = f"✅ Producción Completada: {producto}"

        materiales_html = ''.join([
            f"<li>{m['nombre']}: -{m['cantidad_deducida']:.1f}g</li>"
            for m in materiales_deducidos
        ])

        body = f"""
        <html>
        <body style="font-family: Arial, sans-serif;">
            <div style="background: #e8f5e9; padding: 20px; border-radius: 8px;">
                <h2 style="color: #2e7d32;">✅ PRODUCCIÓN REGISTRADA</h2>

                <p><strong>Producto:</strong> {producto}</p>
                <p><strong>Cantidad:</strong> {cantidad_kg} kg</p>
                <p><strong>Fecha/Hora:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>

                <h3>Materiales Deducidos:</h3>
                <ul>
                    {materiales_html}
                </ul>

                <hr>
                <p style="color: #666; font-size: 12px;">
                    Sistema Automático de Inventarios ÁNIMUS Lab + Espagiria
                </p>
            </div>
        </body>
        </html>
        """

        self._enviar_email(asunto, body)
        self.historial.append({
            'tipo': 'produccion',
            'producto': producto,
            'timestamp': datetime.now().isoformat()
        })

    def enviar_reporte_inventario(self, estadisticas):
        """Envía reporte diario/semanal de inventario"""
        asunto = f"📊 Reporte de Inventario - {datetime.now().strftime('%Y-%m-%d')}"

        body = f"""
        <html>
        <body style="font-family: Arial, sans-serif;">
            <div style="background: #e3f2fd; padding: 20px; border-radius: 8px;">
                <h2 style="color: #1565c0;">📊 REPORTE DE INVENTARIO</h2>

                <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
                    <tr style="background: #f5f5f5;">
                        <td style="padding: 10px; border: 1px solid #ddd;"><strong>Métrica</strong></td>
                        <td style="padding: 10px; border: 1px solid #ddd;"><strong>Valor</strong></td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; border: 1px solid #ddd;">Total Items</td>
                        <td style="padding: 10px; border: 1px solid #ddd;">{estadisticas.get('total_items', 0)}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; border: 1px solid #ddd;">Stock Total (kg)</td>
                        <td style="padding: 10px; border: 1px solid #ddd;">{estadisticas.get('total_kg', 0):.1f}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; border: 1px solid #ddd;">Valor Aproximado</td>
                        <td style="padding: 10px; border: 1px solid #ddd;">USD ${estadisticas.get('total_valor', 0):,.0f}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; border: 1px solid #ddd;">Productos Disponibles</td>
                        <td style="padding: 10px; border: 1px solid #ddd;">{estadisticas.get('productos', 0)}</td>
                    </tr>
                </table>

                <p style="color: #666; font-size: 12px;">
                    Reporte generado automáticamente por el Sistema de Inventarios<br>
                    ÁNIMUS Lab + Espagiria Laboratorio
                </p>
            </div>
        </body>
        </html>
        """

        self._enviar_email(asunto, body)

    def enviar_alerta_compra_urgente(self, materiales_criticos):
        """Alerta cuando múltiples materiales están bajos"""
        asunto = "🛒 COMPRA URGENTE RECOMENDADA"

        materiales_html = ''.join([
            f"<li><strong>{m['nombre']}</strong> ({m['codigo']}): {m['stock']} kg</li>"
            for m in materiales_criticos
        ])

        body = f"""
        <html>
        <body style="font-family: Arial, sans-serif;">
            <div style="background: #fff3e0; padding: 20px; border-radius: 8px;">
                <h2 style="color: #e65100;">🛒 COMPRA URGENTE RECOMENDADA</h2>

                <p>Los siguientes materiales requieren reorden inmediato:</p>

                <ul>
                    {materiales_html}
                </ul>

                <p><strong>Acción Recomendada:</strong> Contacta a proveedores e inicia proceso de compra</p>

                <hr>
                <p style="color: #666; font-size: 12px;">
                    Sistema de Inventarios ÁNIMUS Lab + Espagiria
                </p>
            </div>
        </body>
        </html>
        """

        self._enviar_email(asunto, body)

    def _enviar_email(self, asunto, body, destinatarios=None, attachments=None,
                      reply_to=None):
        """Envía un email (método interno).

        attachments: lista de tuplas (filename, bytes, mimetype). Si mimetype
                     no se especifica, se asume 'application/pdf'.
        reply_to:    email donde el destinatario verá responder (útil para
                     comprobantes que salen de la cuenta de facturación).
        """
        if not self.email_remitente or not self.contraseña:
            logger.warning("Email no configurado: EMAIL_REMITENTE/EMAIL_PASSWORD ausentes")
            return False

        destinatarios = destinatarios or [self.email_remitente]
        # Si solo viene texto plano, lo metemos en alternative; si hay
        # adjuntos, usamos 'mixed' como contenedor raíz.
        try:
            if attachments:
                msg = MIMEMultipart('mixed')
                cuerpo = MIMEMultipart('alternative')
                cuerpo.attach(MIMEText(body, 'html'))
                msg.attach(cuerpo)
                for att in attachments:
                    if not att or len(att) < 2:
                        continue
                    fname = att[0]
                    data = att[1]
                    mime = att[2] if len(att) > 2 and att[2] else 'application/pdf'
                    maintype, subtype = mime.split('/', 1) if '/' in mime else ('application', 'octet-stream')
                    if maintype == 'application' and subtype == 'pdf':
                        part = MIMEApplication(data, _subtype='pdf')
                    else:
                        part = MIMEApplication(data, _subtype=subtype)
                    part.add_header('Content-Disposition', 'attachment', filename=fname)
                    msg.attach(part)
            else:
                msg = MIMEMultipart('alternative')
                msg.attach(MIMEText(body, 'html'))

            msg['Subject'] = asunto
            msg['From'] = self.email_remitente
            msg['To'] = ', '.join(destinatarios)
            if reply_to:
                msg['Reply-To'] = reply_to

            with smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=30) as server:
                server.starttls()
                server.login(self.email_remitente, self.contraseña)
                server.send_message(msg)

            logger.info("Email enviado: %s → %s", asunto, destinatarios)
            return True

        except Exception as e:
            logger.error("Error enviando email '%s' → %s: %s", asunto, destinatarios, e)
            return False

    # ── COMPROBANTES DE EGRESO (HHA) ─────────────────────────────────────────
    def enviar_comprobante_egreso(self, destinatario, numero_ce, beneficiario,
                                  total_pagado, pdf_bytes, fecha_emision='',
                                  numero_oc='', empresa='Espagiria'):
        """Envía el comprobante de egreso PDF al beneficiario.

        Args:
            destinatario: email destino (string).
            numero_ce: 'CE-2026-0042'
            beneficiario: nombre del influencer/proveedor
            total_pagado: float (COP)
            pdf_bytes: bytes del PDF (no base64)
            fecha_emision: 'YYYY-MM-DD' (opcional, defaults today)
            numero_oc: opcional, OC asociada
            empresa: 'Espagiria' o 'Animus'

        Returns:
            True si se envió, False si falló o no hay config SMTP.
        """
        if not destinatario or '@' not in destinatario:
            logger.warning("enviar_comprobante_egreso: destinatario inválido (%r)", destinatario)
            return False
        fecha_str = fecha_emision or datetime.now().strftime('%Y-%m-%d')
        try:
            total_fmt = f"${total_pagado:,.0f}".replace(',', '.')
        except Exception:
            total_fmt = str(total_pagado)
        asunto = f"Comprobante de pago {numero_ce} — {empresa}"
        body = f"""
        <html>
        <body style="font-family: Arial, Helvetica, sans-serif; color: #1a1a1a;">
          <div style="max-width: 600px; margin: 0 auto; padding: 24px;
                      border-top: 4px solid #1F5F5B;">
            <h2 style="color:#1F5F5B; margin: 0 0 8px 0;">Comprobante de pago emitido</h2>
            <p style="color:#666; margin: 0 0 24px 0; font-size: 13px;">
              {empresa.upper()} — Documento soporte de egreso
            </p>
            <p>Hola <strong>{beneficiario}</strong>,</p>
            <p>Hemos generado y registrado el comprobante de pago por los servicios
               prestados. Adjunto encontrarás el PDF formal con el desglose completo
               (subtotal, retenciones aplicadas e IVA si corresponde).</p>
            <table style="width:100%; border-collapse: collapse; margin: 16px 0;
                          background:#f7f7f5; border-radius: 6px; overflow:hidden;">
              <tr>
                <td style="padding:10px 14px; color:#666; font-size: 12px;
                           text-transform: uppercase; letter-spacing: .5px;">Comprobante</td>
                <td style="padding:10px 14px; font-weight: 700;">{numero_ce}</td>
              </tr>
              <tr>
                <td style="padding:10px 14px; color:#666; font-size: 12px;
                           text-transform: uppercase; letter-spacing: .5px;
                           border-top: 1px solid #e6e6e0;">Fecha</td>
                <td style="padding:10px 14px; border-top: 1px solid #e6e6e0;">{fecha_str}</td>
              </tr>
              {f'<tr><td style="padding:10px 14px; color:#666; font-size: 12px; text-transform: uppercase; letter-spacing: .5px; border-top: 1px solid #e6e6e0;">OC asociada</td><td style="padding:10px 14px; border-top: 1px solid #e6e6e0;">{numero_oc}</td></tr>' if numero_oc else ''}
              <tr>
                <td style="padding:10px 14px; color:#666; font-size: 12px;
                           text-transform: uppercase; letter-spacing: .5px;
                           border-top: 1px solid #e6e6e0;">Total pagado</td>
                <td style="padding:10px 14px; font-weight: 700; color:#1F5F5B;
                           border-top: 1px solid #e6e6e0;">{total_fmt}</td>
              </tr>
            </table>
            <p style="font-size: 13px; color:#444;">
              Si tienes alguna pregunta sobre este pago o necesitas un certificado
              adicional, por favor responde a este correo.
            </p>
            <hr style="border: none; border-top: 1px solid #e6e6e0; margin: 24px 0;">
            <p style="font-size: 11px; color:#888; line-height: 1.6;">
              Este mensaje fue generado automáticamente por el sistema de gestión
              HHA Group. El comprobante adjunto es un Documento Soporte de Pago
              conforme al Estatuto Tributario (art. 1.6.1.4.12).<br>
              Por favor verifica que tus datos bancarios sean los correctos.
            </p>
          </div>
        </body>
        </html>
        """
        attachments = [(f"{numero_ce}.pdf", pdf_bytes, 'application/pdf')]
        ok = self._enviar_email(asunto, body, destinatarios=[destinatario],
                                attachments=attachments)
        self.historial.append({
            'tipo': 'comprobante_egreso',
            'numero_ce': numero_ce,
            'destinatario': destinatario,
            'enviado': ok,
            'timestamp': datetime.now().isoformat(),
        })
        return ok

    def enviar_en_background(self, funcion, *args, **kwargs):
        """Ejecuta el envío en un thread separado (no bloquea la app)"""
        thread = threading.Thread(target=funcion, args=args, kwargs=kwargs, daemon=True)
        thread.start()


# Ejemplo de uso
if __name__ == '__main__':
    # Configuración (reemplazar con valores reales)
    notificador = SistemaNotificaciones(
        email_remitente="tu_email@gmail.com",
        contraseña="app_password_generada"
    )

    # Enviar alerta de stock bajo
    notificador.enviar_alerta_stock_bajo(
        material_nombre="CARBOPOL",
        codigo="MP001",
        stock_actual_kg=5.2,
        umbral_kg=10
    )

    # Enviar notificación de producción
    notificador.enviar_notificacion_produccion(
        producto="RENOVA C",
        cantidad_kg=12,
        materiales_deducidos=[
            {'nombre': 'AGUA DESIONIZADA', 'cantidad_deducida': 5.7},
            {'nombre': 'CARBOPOL', 'cantidad_deducida': 0.024}
        ]
    )

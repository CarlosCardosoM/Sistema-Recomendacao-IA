import smtplib
import random
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
import os

load_dotenv()

EMAIL_REMETENTE = os.getenv("EMAIL_REMETENTE")
EMAIL_SENHA_APP = os.getenv("EMAIL_SENHA_APP")


def gerar_token() -> str:
    
    return str(random.randint(100000, 999999))


def enviar_email_verificacao(email_destino: str, token: str, nome: str):

    mensagem = MIMEMultipart("alternative")
    mensagem["Subject"] = "Seu código de acesso — SabIÁ"
    mensagem["From"]    = EMAIL_REMETENTE
    mensagem["To"]      = email_destino

    # Corpo do email em texto simples
    corpo_texto = f"""
Olá, {nome}!

Seu código de acesso ao SabIÁ é:

{token}

Este código é válido por 10 minutos.
Se você não solicitou este código, ignore este email.

SabIÁ — Chatboot Educacional
    """

    # Corpo do email em HTML
    corpo_html = f"""
    <html>
      <body style="font-family: Arial, sans-serif; padding: 20px;">
        <h2 style="color: #4A90D9;">SabIÁ — Chatboot Educacional</h2>
        <p>Olá, <strong>{nome}</strong>!</p>
        <p>Seu código de acesso é:</p>
        <h1 style="letter-spacing: 8px; color: #333;">{token}</h1>
        <p style="color: #888;">Este código é válido por <strong>10 minutos</strong>.</p>
        <hr/>
        <p style="color: #aaa; font-size: 12px;">
          Se você não solicitou este código, ignore este email.
        </p>
      </body>
    </html>
    """

    mensagem.attach(MIMEText(corpo_texto, "plain"))
    mensagem.attach(MIMEText(corpo_html,  "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as servidor:
        servidor.login(EMAIL_REMETENTE, EMAIL_SENHA_APP)
        servidor.sendmail(EMAIL_REMETENTE, email_destino, mensagem.as_string())
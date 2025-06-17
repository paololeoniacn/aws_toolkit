import os
import requests
from dotenv import load_dotenv

load_dotenv()

SEND_MAIL_URL = os.getenv("SEND_MAIL_URL")
MAILING_LIST = os.getenv("MAILING_LIST", "").split(",")
ENV = os.getenv("ENV", "dev")

def send_alert_email(identifier: str, description: str, error_message: str = ""):
    """Invia una mail HTML via servizio HTTP esterno"""
    
    if not SEND_MAIL_URL or not MAILING_LIST:
        print("❌ SEND_MAIL_URL o MAILING_LIST non configurati.")
        return

    subject = f"[{ENV}] Errore su identifier: {identifier}"
    body_html = f"""
    <html><body>
    <p>⚠️ Si è verificato un errore durante l'elaborazione della <strong>{identifier}</strong>.</p>
    <p><strong>Descrizione:</strong> {description}</p>
    <p>Non è stato possibile trovare un riferimento della stessa richiesta andato a buon fine, si consiglia di controllare</p>
    {"<p><strong>Errore:</strong> " + error_message + "</p>" if error_message else ""}
    <p>Ambiente: <strong>{ENV}</strong></p>
    </body></html>
    """

    payload = {
        "from": "noreply@italia.it",
        "to": MAILING_LIST,
        "subject": subject,
        "contentType": "text/html",
        "bodyText": body_html
    }

    try:
        response = requests.post(SEND_MAIL_URL.rstrip("/") + "/api/send-mail", json=payload)
        response.raise_for_status()
        print(f"📧 Email inviata a {MAILING_LIST}")
    except Exception as e:
        print(f"❌ Errore invio email: {e}")

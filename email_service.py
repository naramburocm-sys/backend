import resend
import os

resend.api_key = os.getenv("RESEND_API_KEY", "re_tu_api_key")

def send_welcome_email(user_email: str, username: str):
    try:
        params = {
            "from": "Plataforma <onboarding@resend.dev>",
            "to": [user_email],
            "subject": "¡Bienvenido a tu plataforma de autoestudio!",
            "html": f"<h2>¡Hola, {username}!</h2><p>Tu cuenta ha sido creada con éxito.</p>"
        }
        resend.Emails.send(params)
    except Exception as e:
        print(f"Error de correo: {e}")
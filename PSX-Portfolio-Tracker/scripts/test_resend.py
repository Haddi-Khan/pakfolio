import os
import resend
from dotenv import load_dotenv

# Load env from backend/.env
dotenv_path = os.path.join(os.path.dirname(__file__), "..", "backend", ".env")
load_dotenv(dotenv_path)

api_key = os.getenv("RESEND_API_KEY")
resend.api_key = api_key

print(f"Using API Key starting with: {api_key[:10]}...")

try:
    r = resend.Emails.send({
        "from": "Pakfolio <help@pakfolio.pk>",
        "to": "nasir-41@hotmail.com",
        "subject": "Resend Test",
        "html": "<p>This is a test email from the setup script.</p>"
    })
    print("Send result:", r)
except Exception as e:
    print("Error sending email:", e)

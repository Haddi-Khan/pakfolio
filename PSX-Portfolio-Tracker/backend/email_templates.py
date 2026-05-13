from datetime import datetime
import os

def get_email_template(title, body_html, button_text=None, button_url=None):
    """
    Returns a professional, branded HTML email template for Pakfolio.
    """
    frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:5173")
    button_html = f"""
        <tr>
            <td align="center" style="padding: 20px 0;">
                <table border="0" cellspacing="0" cellpadding="0">
                    <tr>
                        <td align="center" style="border-radius: 12px;" bgcolor="#6366f1">
                            <a href="{button_url}" target="_blank" style="font-size: 16px; font-family: 'Inter', Helvetica, Arial, sans-serif; color: #ffffff; text-decoration: none; border-radius: 12px; padding: 14px 32px; border: 1px solid #6366f1; display: inline-block; font-weight: bold;">{button_text}</a>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    """ if button_text and button_url else ""

    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
        body {{
            margin: 0;
            padding: 0;
            background-color: #050505;
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            -webkit-font-smoothing: antialiased;
        }}
        .container {{
            max-width: 600px;
            margin: 40px auto;
            background-color: #0f0f0f;
            border-radius: 24px;
            overflow: hidden;
            border: 1px solid #1f1f1f;
        }}
        .header {{
            padding: 40px 40px 20px;
            text-align: center;
        }}
        .logo {{
            width: 48px;
            height: 48px;
            margin-bottom: 20px;
        }}
        .content {{
            padding: 0 40px 40px;
            color: #a3a3a3;
            line-height: 1.6;
            font-size: 16px;
        }}
        h1 {{
            color: #ffffff;
            font-size: 24px;
            font-weight: 700;
            margin: 0 0 16px;
        }}
        .footer {{
            padding: 30px 40px;
            background-color: #0a0a0a;
            border-top: 1px solid #1f1f1f;
            text-align: center;
            font-size: 13px;
            color: #525252;
        }}
        .accent {{
            color: #6366f1;
        }}
        .btn {{
            display: inline-block;
            padding: 14px 32px;
            background-color: #6366f1;
            color: #ffffff !important;
            text-decoration: none;
            border-radius: 12px;
            font-weight: 600;
            margin: 20px 0;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h2 style="color: #6366f1; font-weight: 900; margin: 0; font-size: 28px; letter-spacing: -1px;">PAK<span style="color: #ffffff;">FOLIO</span></h2>
        </div>
        <div class="content">
            <h1>{title}</h1>
            {body_html}
            <table border="0" cellspacing="0" cellpadding="0" style="width: 100%;">
                {button_html}
            </table>
            <p style="margin-top: 30px; font-size: 14px;">If you didn't request this email, you can safely ignore it.</p>
        </div>
        <div class="footer">
            <p>© {datetime.now().year} Pakfolio. All rights reserved.</p>
            <p>Empowering investors in the Pakistan Stock Exchange.</p>
            <div style="margin-top: 20px;">
                <a href="{frontend_url}/support" style="color: #6366f1; text-decoration: none; margin: 0 10px;">Support</a>
                <a href="{frontend_url}/terms" style="color: #6366f1; text-decoration: none; margin: 0 10px;">Terms</a>
            </div>
        </div>
    </div>
</body>
</html>
"""

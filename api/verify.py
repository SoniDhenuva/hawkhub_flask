import os
import random
import smtplib
import threading
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from flask import Blueprint, jsonify, request

verify_api = Blueprint('verify_api', __name__, url_prefix='/api/verify')

_store = {}
_lock = threading.Lock()
OTP_TTL = 600  # 10 minutes


def _is_placeholder(val: str | None) -> bool:
    if not val:
        return True
    v = val.strip()
    return v.startswith('xxxx') or v == 'your-gmail@gmail.com' or set(v) <= set('x-')


def _send_email(to_addr: str, code: str) -> bool:
    user = os.environ.get('EMAIL_USER')
    pw = os.environ.get('EMAIL_APP_PASSWORD')
    if _is_placeholder(user) or _is_placeholder(pw):
        # Dev fallback — no SMTP configured
        print(f"[DEV OTP] {to_addr} → {code}")
        return True
    msg = MIMEMultipart('alternative')
    msg['Subject'] = 'HawkHub — Your Verification Code'
    msg['From'] = user
    msg['To'] = to_addr
    html = f"""
    <html><body style="font-family:Arial,sans-serif;background:#0a1628;color:#cfe8ff;padding:2rem;margin:0">
      <h2 style="color:#00d8ff;margin-bottom:.5rem">HawkHub Verification</h2>
      <p style="color:#7aa5ca;margin-bottom:1.5rem">Enter this code to complete your account creation:</p>
      <div style="font-size:2.4rem;font-weight:700;letter-spacing:10px;color:#00f08b;
                  background:rgba(0,240,139,.08);border:1px solid rgba(0,240,139,.25);
                  border-radius:10px;padding:1rem 2rem;display:inline-block">{code}</div>
      <p style="color:#5a8ab0;margin-top:1.5rem;font-size:.9rem">Expires in 10 minutes. If you did not request this, ignore this email.</p>
    </body></html>"""
    msg.attach(MIMEText(html, 'html'))
    try:
        with smtplib.SMTP('smtp.gmail.com', 587) as s:
            s.starttls()
            s.login(user, pw)
            s.sendmail(user, to_addr, msg.as_string())
        return True
    except Exception as exc:
        print(f"[EMAIL ERROR] {exc}")
        return False


@verify_api.route('/send', methods=['POST'])
def send_code():
    data = request.get_json() or {}
    email = data.get('email', '').strip().lower()
    if not email or '@' not in email:
        return jsonify({'error': 'Valid email required'}), 400
    code = str(random.randint(100000, 999999))
    with _lock:
        _store[email] = {'code': code, 'exp': time.time() + OTP_TTL}
    if _send_email(email, code):
        return jsonify({'message': 'Code sent'}), 200
    return jsonify({'error': 'Email delivery failed — check server EMAIL_USER / EMAIL_APP_PASSWORD'}), 500


@verify_api.route('/check', methods=['POST'])
def check_code():
    data = request.get_json() or {}
    email = data.get('email', '').strip().lower()
    code = str(data.get('code', '')).strip()
    with _lock:
        entry = _store.get(email)
        if not entry:
            return jsonify({'valid': False, 'error': 'No pending code for this email'}), 400
        if time.time() > entry['exp']:
            del _store[email]
            return jsonify({'valid': False, 'error': 'Code expired — request a new one'}), 400
        if entry['code'] != code:
            return jsonify({'valid': False, 'error': 'Incorrect code'}), 400
        del _store[email]
    return jsonify({'valid': True}), 200

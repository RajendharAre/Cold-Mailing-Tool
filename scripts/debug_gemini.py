import os
import requests
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).resolve().parents[1] / '.env')
key = os.getenv('GEMINI_API_KEY')
print('KEY_PRESENT', bool(key))
print('KEY_PREFIX', key[:10] if key else None)
payload = {
    'contents': [{'parts': [{'text': 'Say hello in one short sentence.'}]}],
    'generationConfig': {'temperature': 0.2},
}
url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={key}"
resp = requests.post(url, json=payload, timeout=30)
print('STATUS', resp.status_code)
print(resp.text)

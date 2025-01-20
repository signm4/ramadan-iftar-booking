import os
from dotenv import load_dotenv

load_dotenv()
cert_url = os.getenv('CERT_URL')
print(cert_url)
import os
from google import genai

# Mimic ADK environment
os.environ['GOOGLE_GENAI_USE_VERTEXAI'] = '1'
os.environ['GOOGLE_CLOUD_PROJECT'] = 'qwiklabs-gcp-00-e1f76201cd8f'
os.environ['GOOGLE_CLOUD_LOCATION'] = 'us-central1'

print("Attempting to initialize Vertex AI Client...")
try:
    client = genai.Client(vertexai=True, project='qwiklabs-gcp-00-e1f76201cd8f', location='us-central1')
    response = client.models.generate_content(model='gemini-1.5-flash', contents='Testing Vertex AI connection')
    print("SUCCESS: Connection established.")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"FAILURE: {e}")

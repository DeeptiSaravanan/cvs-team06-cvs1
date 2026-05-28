from google import genai
from google.genai import types
import os

client = genai.Client(
    vertexai=True,
    project='qwiklabs-gcp-00-e1f76201cd8f',
    location='us-central1'
)

try:
    response = client.models.generate_content(
        model='gemini-2.0-flash',
        contents='Hello'
    )
    print(f"Success: {response.text}")
except Exception as e:
    print(f"Error: {e}")

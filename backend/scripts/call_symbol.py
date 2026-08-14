from fastapi.testclient import TestClient
from fastapi_server import app

client = TestClient(app)

url = "/api/v1/graph/1059826317/symbol/ChatMessage"
resp = client.get(url)
print('URL:', url)
print('Status:', resp.status_code)
print('Response JSON:')
print(resp.json())

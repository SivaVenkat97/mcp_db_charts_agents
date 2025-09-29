## Minimal FastAPI Project

This is a tiny FastAPI app with one POST endpoint.

### Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Run

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Test the POST endpoint

```bash
curl -X POST http://localhost:8000/items -H 'Content-Type: application/json' -d '{"name":"world"}'
```

Expected response:

```json
{"message":"Received: world"}
```

# AI Code Interpreter

FastAPI endpoint that executes Python code and calls AI Pipe only when code fails.

## 1. Create and activate a virtual environment (Windows PowerShell)

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## 2. Configure the AI Pipe token

```powershell
$env:AIPIPE_TOKEN="YOUR_ACTUAL_TOKEN"
```

Get your token from https://aipipe.org/login. Keep it private; never commit it to GitHub.

## 3. Run locally

```powershell
uvicorn main:app --reload
```

Open http://127.0.0.1:8000/docs and test `POST /code-interpreter`.

## 4. Request example

```json
{
  "code": "x = 5\ny = 10\nprint(x + y)"
}
```

Expected response:

```json
{
  "error": [],
  "result": "15\n"
}
```

## 5. Deploy

For a Render web service:
- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- Add `AIPIPE_TOKEN` as a secret environment variable in the hosting dashboard.

After deployment, submit the public URL ending in `/code-interpreter`.

## Security warning

This educational implementation uses Python `exec()` and is **not safe for public execution of arbitrary/untrusted code**. Do not expose it publicly without a proper isolated sandbox, execution timeouts, and resource limits.

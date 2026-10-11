import os
import sys
import traceback
from io import StringIO
from typing import List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
from pydantic import BaseModel, Field

app = FastAPI(title="AI Code Interpreter")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class CodeRequest(BaseModel):
    code: str


class CodeResponse(BaseModel):
    error: List[int]
    result: str


class ErrorAnalysis(BaseModel):
    error_lines: List[int] = Field(
        description="1-based line numbers responsible for the error"
    )


def execute_python_code(code: str) -> dict:
    """Execute code and return captured output or the original traceback.

    WARNING: exec() is unsafe for untrusted code. Use a properly isolated
    sandbox with time and resource limits before exposing this publicly.
    """
    old_stdout, old_stderr = sys.stdout, sys.stderr
    stdout_buffer, stderr_buffer = StringIO(), StringIO()

    try:
        sys.stdout, sys.stderr = stdout_buffer, stderr_buffer
        exec(compile(code, "<string>", "exec"), {})
        output = stdout_buffer.getvalue() + stderr_buffer.getvalue()
        return {"success": True, "output": output}
    except Exception:
        return {"success": False, "output": traceback.format_exc()}
    finally:
        sys.stdout, sys.stderr = old_stdout, old_stderr


def analyze_error_with_ai(code: str, error_traceback: str) -> List[int]:
    token = os.environ.get("AIPIPE_TOKEN")
    if not token:
        raise RuntimeError("AIPIPE_TOKEN is not configured")

    client = OpenAI(
        api_key=token,
        base_url="https://aipipe.org/openrouter/v1",
    )

    response = client.beta.chat.completions.parse(
        model="openai/gpt-4.1-nano",
        messages=[
            {
                "role": "system",
                "content": (
                    "Analyze Python execution errors. Return only 1-based "
                    "source line numbers responsible for the exception. "
                    "Use the traceback as primary evidence. Do not invent "
                    "line numbers; return an empty list if uncertain."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"PYTHON CODE:\n{code}\n\n"
                    f"TRACEBACK:\n{error_traceback}"
                ),
            },
        ],
        response_format=ErrorAnalysis,
    )

    analysis = response.choices[0].message.parsed
    if analysis is None:
        raise RuntimeError("AI returned no structured analysis")

    code_line_count = len(code.splitlines())
    return sorted({
        line for line in analysis.error_lines
        if 1 <= line <= code_line_count
    })


@app.post("/code-interpreter", response_model=CodeResponse)
def code_interpreter(request: CodeRequest):
    execution = execute_python_code(request.code)

    if execution["success"]:
        return CodeResponse(error=[], result=execution["output"])

    try:
        error_lines = analyze_error_with_ai(request.code, execution["output"])
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"AI error analysis failed: {type(exc).__name__}",
        ) from exc

    return CodeResponse(error=error_lines, result=execution["output"])


@app.get("/")
def home():
    return {"message": "AI Code Interpreter is running"}

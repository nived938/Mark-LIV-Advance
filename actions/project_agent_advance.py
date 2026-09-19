from pathlib import Path
import os
import re
import subprocess
import time

try:
    from ddgs import DDGS
except Exception:
    DDGS = None

SAFE_ROOTS = [
    Path.home(),
    Path("G:/Coding"),
    Path("G:/Projects"),
]

PROJECT_MARKERS = {
    "pyproject.toml": 8,
    "requirements.txt": 7,
    "setup.py": 7,
    "Pipfile": 6,
    "uv.lock": 6,
    "poetry.lock": 5,
    "main.py": 5,
    "app.py": 4,
    "run.py": 4,
    "manage.py": 5,
}

def _safe(p):
    try:
        p = Path(p).expanduser().resolve()
        return any(p == r.resolve() or p.is_relative_to(r.resolve()) for r in SAFE_ROOTS)
    except Exception:
        return False

def _find_projects(root=None, limit=8):
    roots = [Path(root).expanduser()] if root else SAFE_ROOTS
    candidates = {}
    for base in roots:
        if not _safe(base) or not base.exists():
            continue
        try:
            for marker, weight in PROJECT_MARKERS.items():
                for f in base.rglob(marker):
                    if not f.is_file():
                        continue
                    parent = f.parent
                    if any(part.lower() in {".git", "node_modules", ".venv", "venv", "__pycache__"} for part in parent.parts):
                        continue
                    score = weight
                    try:
                        if (parent / ".git").exists():
                            score += 3
                        py_count = sum(1 for _ in parent.glob("*.py"))
                        score += min(py_count, 5)
                        score += min(int((time.time() - parent.stat().st_mtime) / -86400) if parent.stat().st_mtime else 0, 5)
                    except Exception:
                        pass
                    candidates[str(parent.resolve())] = max(candidates.get(str(parent.resolve()), 0), score)
        except Exception:
            continue
    return sorted(candidates.items(), key=lambda x: x[1], reverse=True)[:limit]

def _choose_project(task, root):
    projects = _find_projects(root)
    if not projects:
        return None, []
    low = (task or "").lower()
    explicit = []
    for path, score in projects:
        name = Path(path).name.lower()
        if name and name in low:
            explicit.append((path, score + 20))
    if explicit:
        explicit.sort(key=lambda x: x[1], reverse=True)
        return explicit[0][0], projects
    return projects[0][0], projects

def _run_command(project):
    p = Path(project)
    if (p / "main.py").exists():
        return "python main.py"
    if (p / "app.py").exists():
        return "python app.py"
    if (p / "run.py").exists():
        return "python run.py"
    if (p / "manage.py").exists():
        return "python manage.py runserver"
    if (p / "pyproject.toml").exists():
        return "python -m pip install -e . && python -m project"
    py = list(p.glob("*.py"))
    if len(py) == 1:
        return f'python "{py[0].name}"'
    return ""

def _web_search(error):
    if not DDGS or not error:
        return []
    try:
        with DDGS() as d:
            return list(d.text(f"{error} Python Windows fix", max_results=5))
    except Exception:
        return []

def project_agent_advance(task: str, root: str = "", run: str = "true"):
    if not task:
        return "A task description is required."

    project, candidates = _choose_project(task, root or None)
    if not project:
        return "No Python project was found in the configured safe roots."

    p = Path(project)
    command = _run_command(project)
    if not command:
        return (
            f"Found Python project: {project}\n"
            "I could not determine a safe run command. "
            "Tell me which Python entry file to run."
        )

    try:
        os.startfile(p)
    except Exception:
        pass

    result = {
        "project": str(p),
        "command": command,
        "output": "",
        "error": "",
        "web_results": [],
    }

    if str(run).lower() not in ("true", "1", "yes", "run"):
        return f"Found project: {p}\nSuggested command: {command}"

    try:
        proc = subprocess.Popen(
            ["powershell.exe", "-NoProfile", "-Command", command],
            cwd=str(p),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        try:
            output, _ = proc.communicate(timeout=25)
        except subprocess.TimeoutExpired:
            proc.kill()
            output, _ = proc.communicate()
            output += "\n[Process stopped after 25 seconds to avoid hanging the assistant.]"
        result["output"] = output[-12000:]
        if proc.returncode != 0:
            result["error"] = output[-5000:]
    except Exception as e:
        result["error"] = str(e)

    if not result["error"]:
        error_lines = [x for x in result["output"].splitlines() if re.search(
            r"Traceback|Error:|Exception|ModuleNotFoundError|ImportError|SyntaxError|NameError|FileNotFoundError",
            x,
            re.I,
        )]
        if error_lines:
            result["error"] = "\n".join(error_lines[-20:])

    if result["error"]:
        result["web_results"] = _web_search(result["error"][-1500:])

    text = [
        f"Python project: {result['project']}",
        f"Run command: {result['command']}",
        "PowerShell output:",
        result["output"] or "(no output)",
    ]
    if result["error"]:
        text += ["Detected error:", result["error"]]
        if result["web_results"]:
            text.append("Web search results:")
            for item in result["web_results"]:
                text.append(f"- {item.get('title', '')}: {item.get('href', '')}")
    else:
        text.append("No Python error was detected in the captured output.")
    if len(candidates) > 1:
        text.append("Other detected projects: " + ", ".join(x[0] for x in candidates[1:4]))
    return "\n".join(text)

TOOL = {
    "name": "project_agent_advance",
    "description": (
        "Use this for multi-step developer requests such as: find my Python project, "
        "open it, run it in PowerShell, inspect the error, search the web for the fix, "
        "and report what happened. It performs the whole chain automatically."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "task": {"type": "STRING", "description": "The user's complete developer task"},
            "root": {"type": "STRING", "description": "Optional safe search root"},
            "run": {"type": "STRING", "description": "true to run the detected project, false to only locate it"},
        },
        "required": ["task"],
    },
    "handler": project_agent_advance,
}

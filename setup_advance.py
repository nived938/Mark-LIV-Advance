from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
UPSTREAM = "https://github.com/FatihMakes/Mark-LIV.git"
TEMP = ROOT / ".upstream-mark-liv"

def run(*args):
    print("+", " ".join(map(str, args)))
    subprocess.check_call(args)

def main():
    if (ROOT / "main.py").exists() and (ROOT / "ui.py").exists():
        print("Mark-LIV engine already exists. Nothing to download.")
        return

    if TEMP.exists():
        shutil.rmtree(TEMP)

    print("Downloading the upstream Mark-LIV engine...")
    run("git", "clone", "--depth", "1", UPSTREAM, str(TEMP))

    protected = {
        "README.md",
        "requirements-advance.txt",
        "setup_advance.py",
        ".git",
        ".github",
    }

    for item in TEMP.iterdir():
        destination = ROOT / item.name
        if item.name in protected:
            continue
        if destination.exists():
            if destination.is_dir():
                shutil.copytree(item, destination, dirs_exist_ok=True)
            else:
                shutil.copy2(item, destination)
        else:
            shutil.copytree(item, destination, dirs_exist_ok=True) if item.is_dir() else shutil.copy2(item, destination)

    shutil.rmtree(TEMP, ignore_errors=True)
    print("\nMark-LIV engine installed.")
    print("Now run: python -m pip install -r requirements-advance.txt")
    print("Then: python main.py")

if __name__ == "__main__":
    main()

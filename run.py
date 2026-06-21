import os
import sys
import subprocess
import shutil
import webbrowser
import time

def find_python_interpreter():
    """Finds the path to the virtual environment Python interpreter if available."""
    venv_dir = os.path.join(os.path.dirname(__file__), ".venv")
    if os.path.exists(venv_dir):
        # Windows virtual environment python location
        win_py = os.path.join(venv_dir, "Scripts", "python.exe")
        if os.path.exists(win_py):
            return win_py
        # POSIX virtual environment python location
        posix_py = os.path.join(venv_dir, "bin", "python")
        if os.path.exists(posix_py):
            return posix_py
    return sys.executable

def check_python_version():
    """Ensures Python version is 3.10+."""
    if sys.version_info < (3, 10):
        print("Error: Python 3.10 or higher is required to run TaskForge.")
        sys.exit(1)
    print(f"Python check passed: {sys.version}")

def check_node_dependencies():
    """Checks if node and npm are installed on the host system."""
    if not shutil.which("node"):
        print("Warning: 'node' executable not found in system PATH.")
        return False
    if not shutil.which("npm"):
        print("Warning: 'npm' executable not found in system PATH.")
        return False
    return True

def run_command(args, cwd=None, shell=False):
    """Runs a subprocess command and returns its exit code."""
    try:
        res = subprocess.run(args, cwd=cwd, shell=shell)
        return res.returncode
    except Exception as e:
        print(f"Failed to execute command {' '.join(args)}: {str(e)}")
        return 1

def build_frontend(skip_build):
    """Installs dependencies and compiles the Vue 3 frontend using Vite."""
    frontend_dir = os.path.join(os.path.dirname(__file__), "frontend")
    static_dist_dir = os.path.join(os.path.dirname(__file__), "static_dist")
    index_path = os.path.join(static_dist_dir, "index.html")

    if skip_build:
        print("Skipping frontend build as requested.")
        if os.path.exists(index_path):
            print("Found existing static_dist build.")
            return True
        else:
            print("Warning: static_dist/index.html not found. Proceeding with compilation fallback...")

    print("Checking Node.js environment...")
    has_node = check_node_dependencies()

    if not has_node:
        if os.path.exists(index_path):
            print("Warning: Node.js/npm missing, but existing frontend build found in static_dist/. Using it.")
            return True
        else:
            print("Error: Node.js/npm is missing and no compiled frontend exists in static_dist/.")
            print("Please install Node.js (v18+) to build the frontend.")
            sys.exit(1)

    print("Installing frontend dependencies...")
    pkg_lock = os.path.join(frontend_dir, "package-lock.json")

    # Use npm ci for deterministic builds if package-lock.json is present, else npm install
    # On Windows, npm is sometimes a cmd script, so shell=True might be required.
    is_windows = os.name == 'nt'
    npm_cmd = "npm.cmd" if is_windows else "npm"

    if os.path.exists(pkg_lock):
        print("Found package-lock.json. Running deterministic 'npm ci'...")
        install_code = run_command([npm_cmd, "ci"], cwd=frontend_dir, shell=is_windows)
    else:
        print("Running 'npm install'...")
        install_code = run_command([npm_cmd, "install"], cwd=frontend_dir, shell=is_windows)

    if install_code != 0:
        print("Error: Frontend dependency installation failed.")
        sys.exit(1)

    print("Building frontend Vue SPA via Vite...")
    build_code = run_command([npm_cmd, "run", "build"], cwd=frontend_dir, shell=is_windows)

    if build_code != 0:
        print("Warning: Frontend compilation failed.")
        if os.path.exists(index_path):
            print("Found existing static_dist/index.html. Proceeding with fallback...")
            return True
        else:
            print("Error: Frontend build failed and no existing fallback static_dist assets exist.")
            sys.exit(1)

    print("Frontend build succeeded. Assets output to static_dist/.")
    return True

def main():
    # Parse CLI flags
    skip_build = "--skip-build" in sys.argv or os.environ.get("SKIP_FRONTEND_BUILD") == "1"

    check_python_version()

    # Step 1: Build the frontend
    build_frontend(skip_build)

    # Step 2: Resolve virtual environment Python interpreter
    python_interpreter = find_python_interpreter()
    print(f"Using Python interpreter: {python_interpreter}")

    # Step 3: Run backend FastAPI server via uvicorn
    print("Starting TaskForge backend server on http://localhost:8000...")

    # Automatically open browser after a short delay
    def open_browser():
        time.sleep(2.0)
        print("Opening browser to dashboard at http://localhost:8000...")
        webbrowser.open("http://localhost:8000")

    import threading
    browser_thread = threading.Thread(target=open_browser)
    browser_thread.daemon = True
    browser_thread.start()

    # Start uvicorn
    cmd = [python_interpreter, "-m", "uvicorn", "taskforge.main:app", "--host", "127.0.0.1", "--port", "8000"]
    root_dir = os.path.join(os.path.dirname(__file__), "src")

    # Run server (this blocks until process is terminated)
    try:
        subprocess.run(cmd, cwd=root_dir)
    except KeyboardInterrupt:
        print("\nTaskForge server stopped by user.")

if __name__ == "__main__":
    main()

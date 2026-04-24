
import subprocess
import os
import uuid
import base64
import sys
import tempfile
from typing import Dict, Any, List
from loguru import logger

# Use an external temp workspace so uvicorn --reload does not restart on each generated script.
WORKSPACE_DIR = os.getenv(
    "SANDBOX_WORKSPACE_DIR",
    os.path.join(tempfile.gettempdir(), "finagent-sandbox"),
)

class SandboxService:
    """
    Executes Python code in a local sandbox (subprocess).
    Manages workspace directory for file I/O.
    """

    def __init__(self, workspace: str = WORKSPACE_DIR):
        self.workspace = os.path.abspath(workspace)
        self.allow_local_fallback = os.getenv("SANDBOX_ALLOW_LOCAL_FALLBACK", "true").lower() in {"1", "true", "yes", "on"}
        os.makedirs(self.workspace, exist_ok=True)

    def execute_code(self, code: str) -> Dict[str, Any]:
        """
        Execute Python code and return stdout, stderr, and artifacts.
        """
        # Create a unique filename for this execution
        filename = f"script_{uuid.uuid4().hex}.py"
        filepath = os.path.join(self.workspace, filename)

        # Write code to file
        wrapped_code = self._wrap_code(code)
        self._cleanup_images()

        with open(filepath, "w") as f:
            f.write(wrapped_code)

        logger.info(f"Executing code in sandbox: {filename}")

        try:
            abs_workspace = os.path.abspath(self.workspace)
            docker_network = os.getenv("SANDBOX_DOCKER_NETWORK", "bridge")
            cmd = [
                "docker", "run", "--rm",
                "--network", docker_network,
                "--read-only",
                "--tmpfs", "/tmp:rw,size=256m",
                "--pids-limit", "128",
                "-m", "512m",
                "--workdir", "/app",
                "-e", "HOME=/tmp",
                "-e", "XDG_CACHE_HOME=/tmp",
                "-e", "MPLCONFIGDIR=/tmp/matplotlib",
                "-v", f"{abs_workspace}:/app",
                "finagent-sandbox",
                "python", f"/app/{filename}"
            ]

            logger.info("Attempting Docker execution...")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            stdout = result.stdout
            stderr = result.stderr
            return_code = result.returncode

            stderr_lower = (stderr or "").lower()
            if return_code != 0 and (
                "docker: " in stderr_lower or
                "cannot connect to the docker daemon" in stderr_lower or
                "is the docker daemon running" in stderr_lower or
                "permission denied while trying to connect to the docker api" in stderr_lower or
                "failed to connect to the docker api" in stderr_lower
            ):
                if not self.allow_local_fallback:
                    logger.error("Sandbox execution blocked: Docker is not available and local fallback is disabled")
                    return {
                        "success": False,
                        "stdout": "",
                        "stderr": "Sandbox unavailable: Docker is not running and local fallback is disabled.",
                        "return_code": -1,
                        "images": []
                    }

                logger.warning("Docker unavailable; falling back to local restricted execution")
                local_result = self._execute_local(filepath)
                stdout = local_result["stdout"]
                stderr = local_result["stderr"]
                return_code = local_result["return_code"]

            # Check for generated images
            images = self._collect_images()

            return {
                "success": return_code == 0,
                "stdout": stdout,
                "stderr": stderr,
                "return_code": return_code,
                "images": images
            }

        except Exception as e:
            return {
                "success": False,
                "stderr": f"Execution failed: {str(e)}",
                "stdout": "",
                "return_code": -1,
                "images": [],
            }

        finally:
            if os.path.exists(filepath):
                try:
                    os.remove(filepath)
                except Exception:
                    pass
            self._cleanup_images()

    def _wrap_code(self, code: str) -> str:
        """
        Wrap code to auto-save matplotlib plots if they exist.
        """
        prefix = """
import os
import tempfile

os.environ.setdefault('XDG_CACHE_HOME', tempfile.gettempdir())
os.environ.setdefault('MPLCONFIGDIR', os.path.join(tempfile.gettempdir(), 'matplotlib'))
os.makedirs(os.environ['MPLCONFIGDIR'], exist_ok=True)

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# Disable plt.show() to prevent blocking/clearing
def show_mock(*args, **kwargs):
    pass
plt.show = show_mock
"""
        suffix = """
# Auto-save remaining plots
if plt.get_fignums():
    for i in plt.get_fignums():
        plt.figure(i).savefig(f'plot_{i}.png')
"""
        if "matplotlib" in code or "plt." in code:
            # Avoid duplicate chart artifacts when user code already saves figures.
            if "savefig(" in code:
                return prefix + code
            return prefix + code + suffix
        return code

    def _collect_images(self) -> List[Dict[str, str]]:
        """Collect and encode generated images."""
        images = []
        try:
            files = os.listdir(self.workspace)
            logger.info(f"Checking for images in {self.workspace}. Found files: {files}")
            for file in files:
                if file.endswith(".png"):
                    path = os.path.join(self.workspace, file)
                    logger.info(f"Found image: {path}")
                    with open(path, "rb") as f:
                        data = base64.b64encode(f.read()).decode("utf-8")
                        images.append({"name": file, "base64": data})
                    # Cleanup output image after collection (or keep it? let's keep for debugging for now)
                    # os.remove(path)
        except Exception as e:
            logger.error(f"Error collecting images: {e}")
            raise e
        return images

    def _execute_local(self, filepath: str) -> Dict[str, Any]:
        """
        Execute code locally when Docker sandbox is unavailable.
        This is a development/demo fallback and should not be used in untrusted environments.
        """
        abs_workspace = os.path.abspath(self.workspace)
        env = os.environ.copy()
        env.setdefault("MPLCONFIGDIR", abs_workspace)
        env.setdefault("XDG_CACHE_HOME", abs_workspace)

        absolute_filepath = os.path.abspath(filepath)
        result = subprocess.run(
            [sys.executable, absolute_filepath],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=abs_workspace,
            env=env,
        )
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "return_code": result.returncode,
        }

    def _cleanup_images(self) -> None:
        """Delete generated image artifacts from previous runs."""
        try:
            for file in os.listdir(self.workspace):
                if file.endswith(".png"):
                    os.remove(os.path.join(self.workspace, file))
        except Exception as e:
            logger.warning(f"Image cleanup failed: {e}")

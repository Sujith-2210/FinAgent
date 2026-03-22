import os
import tempfile
from types import SimpleNamespace

from app.services.sandbox import SandboxService


def test_default_workspace_uses_system_temp_directory():
    sandbox = SandboxService()
    assert os.path.abspath(sandbox.workspace).startswith(os.path.abspath(tempfile.gettempdir()))


def test_docker_command_sets_writable_mpl_and_workdir(monkeypatch, tmp_path):
    captured = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    sandbox = SandboxService(workspace=str(tmp_path))
    monkeypatch.setattr("app.services.sandbox.subprocess.run", fake_run)
    monkeypatch.setattr(sandbox, "_collect_images", lambda: [])

    result = sandbox.execute_code("print('ok')")

    assert result["success"] is True
    cmd = captured["cmd"]
    assert "--workdir" in cmd
    assert "/app" in cmd
    assert "--tmpfs" in cmd
    assert "/tmp:rw,size=256m" in cmd
    assert "MPLCONFIGDIR=/tmp/matplotlib" in cmd
    assert "XDG_CACHE_HOME=/tmp" in cmd


def test_falls_back_to_local_on_docker_connection_error(monkeypatch, tmp_path):
    sandbox = SandboxService(workspace=str(tmp_path))

    def fake_run(_cmd, **_kwargs):
        return SimpleNamespace(
            returncode=1,
            stdout="",
            stderr="failed to connect to the docker API at unix:///var/run/docker.sock",
        )

    monkeypatch.setattr("app.services.sandbox.subprocess.run", fake_run)
    monkeypatch.setattr(sandbox, "_execute_local", lambda _filepath: {"stdout": "ok", "stderr": "", "return_code": 0})
    monkeypatch.setattr(sandbox, "_collect_images", lambda: [])

    result = sandbox.execute_code("print('ok')")
    assert result["success"] is True
    assert result["stdout"] == "ok"


def test_wrap_code_skips_autosave_when_savefig_present(tmp_path):
    sandbox = SandboxService(workspace=str(tmp_path))
    code = """
import matplotlib.pyplot as plt
plt.plot([1, 2, 3], [1, 4, 9])
plt.savefig('custom_chart.png')
"""
    wrapped = sandbox._wrap_code(code)
    assert "custom_chart.png" in wrapped
    assert "plot_{i}.png" not in wrapped

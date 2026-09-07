"""The public one-command installer must stay a thin uv + wheel wrapper."""

from pathlib import Path
import subprocess


ROOT = Path(__file__).parents[1]


def test_posix_installer_is_valid_shell_and_installs_the_release_wheel():
    script = ROOT / "scripts" / "install.sh"
    subprocess.run(["sh", "-n", str(script)], check=True)
    text = script.read_text(encoding="utf-8")
    assert "uv tool install --force" in text
    assert "asecli install-skill" in text
    assert "py3-none-any.whl" in text
    assert "astral.sh/uv/install.sh" in text


def test_windows_installer_installs_the_same_release_wheel():
    text = (ROOT / "scripts" / "install.ps1").read_text(encoding="utf-8")
    assert "uv tool install --force" in text
    assert "asecli install-skill" in text
    assert "py3-none-any.whl" in text
    assert "astral.sh/uv/install.ps1" in text

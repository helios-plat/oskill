"""Tests for env_doctor (doctor SKILL 3O 内化)."""

from __future__ import annotations

import pytest

from oskill.env_doctor import (
    DEFAULT_SPECS,
    DepSpec,
    check_dependencies,
    detect_platform,
    install_commands,
    run_doctor,
)


class _ShellResult:
    def __init__(self, stdout: str = "", stderr: str = "", code: int = 0) -> None:
        self.stdout = stdout
        self.stderr = stderr
        self.code = code

    @property
    def ok(self) -> bool:
        return self.code == 0


class TestDetectPlatform:
    def test_windows_tag(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("oskill.env_doctor._platform.system", lambda: "Windows")
        monkeypatch.setattr(
            "oskill.env_doctor.bash_exec",
            lambda command, **_: _ShellResult(stdout="", code=1),
        )
        info = detect_platform()
        assert info["platform_tag"] == "windows"

    def test_linux_tag_with_distro(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("oskill.env_doctor._platform.system", lambda: "Linux")
        monkeypatch.setattr("oskill.env_doctor._read_os_release_id", lambda: "ubuntu")
        monkeypatch.setattr(
            "oskill.env_doctor.bash_exec",
            lambda command, **_: _ShellResult(stdout="", code=1),
        )
        info = detect_platform()
        assert info["platform_tag"] == "linux"
        assert info["distro"] == "ubuntu"


class TestCheckDependencies:
    def test_cmd_present(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "oskill.env_doctor.bash_exec",
            lambda command, **_: _ShellResult(stdout="/usr/bin/python3"),
        )
        results = check_dependencies(
            [DepSpec(name="python3", kind="cmd", check="python3", required=True)]
        )
        assert results[0].status == "ok"
        assert results[0].detail == "/usr/bin/python3"

    def test_cmd_missing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "oskill.env_doctor.bash_exec",
            lambda command, **_: _ShellResult(stdout="", code=1),
        )
        results = check_dependencies(
            [DepSpec(name="python3", kind="cmd", check="python3", required=True)]
        )
        assert results[0].status == "miss"

    def test_pkg_present(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("oskill.env_doctor._import_module", lambda name: object())
        monkeypatch.setattr("oskill.env_doctor._pkg_version", lambda name: "1.26.4")
        results = check_dependencies(
            [DepSpec(name="numpy", kind="pkg", check="numpy", required=False)]
        )
        assert results[0].status == "ok"
        assert results[0].detail == "1.26.4"

    def test_pkg_missing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def raise_import_error(name: str) -> object:
            raise ImportError(name)

        monkeypatch.setattr("oskill.env_doctor._import_module", raise_import_error)
        results = check_dependencies(
            [DepSpec(name="numpy", kind="pkg", check="numpy", required=False)]
        )
        assert results[0].status == "miss"


class TestInstallCommands:
    def test_distro_specific_wins(self) -> None:
        spec = DepSpec(
            name="x",
            kind="cmd",
            check="x",
            installs={
                "linux-ubuntu": ["sudo apt install x"],
                "linux": ["snap install x"],
                "all": ["curl install x"],
            },
        )
        cmds = install_commands(spec, {"platform_tag": "linux", "distro": "ubuntu"})
        assert cmds == ["sudo apt install x"]

    def test_fallback_to_generic(self) -> None:
        spec = DepSpec(
            name="x",
            kind="cmd",
            check="x",
            installs={"linux": ["snap install x"], "all": ["curl install x"]},
        )
        cmds = install_commands(spec, {"platform_tag": "linux", "distro": "ubuntu"})
        assert cmds == ["snap install x"]

    def test_fallback_to_all(self) -> None:
        spec = DepSpec(
            name="x", kind="cmd", check="x", installs={"all": ["pip3 install x"]}
        )
        cmds = install_commands(spec, {"platform_tag": "mac", "distro": ""})
        assert cmds == ["pip3 install x"]

    def test_no_match_returns_empty(self) -> None:
        spec = DepSpec(name="x", kind="cmd", check="x", installs={})
        cmds = install_commands(spec, {"platform_tag": "windows", "distro": ""})
        assert cmds == []


class TestRunDoctor:
    def _specs(self) -> list[DepSpec]:
        return [
            DepSpec(
                name="python3",
                kind="cmd",
                check="python3",
                required=True,
                installs={"all": ["echo install python3"]},
            ),
            DepSpec(
                name="drawio",
                kind="cmd",
                check="drawio",
                required=False,
                installs={"all": ["echo install drawio"]},
            ),
        ]

    def test_report_lists_missing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("oskill.env_doctor._platform.system", lambda: "Linux")
        monkeypatch.setattr(
            "oskill.env_doctor.bash_exec",
            lambda command, **_: _ShellResult(stdout="", code=1),
        )
        report = run_doctor(self._specs())
        assert report.ready is False
        assert "python3" in report.missing_required
        assert "drawio" in report.missing_optional
        assert report.install_commands["python3"] == ["echo install python3"]
        assert report.install_results == {}

    def test_auto_install_runs_and_rechecks(self, monkeypatch: pytest.MonkeyPatch) -> None:
        install_ran: list[str] = []
        installed: set[str] = set()

        def fake_bash_exec(command: str, **_: object) -> _ShellResult:
            if command.startswith("command -v"):
                name = command.split()[-1]
                if name in installed:
                    return _ShellResult(stdout=f"/usr/bin/{name}")
                return _ShellResult(stdout="", code=1)
            if command.startswith("echo install"):
                installed.add(command.split()[-1])
                install_ran.append(command)
                return _ShellResult()
            return _ShellResult()

        monkeypatch.setattr("oskill.env_doctor._platform.system", lambda: "Linux")
        monkeypatch.setattr("oskill.env_doctor.bash_exec", fake_bash_exec)
        report = run_doctor(self._specs(), auto_install=True)
        assert install_ran == ["echo install python3"]
        assert "python3" not in report.missing_required
        assert report.ready is True
        assert "python3" in report.install_results

    def test_default_specs_shape(self) -> None:
        names = {spec.name for spec in DEFAULT_SPECS}
        assert {"python3", "numpy", "pandas", "matplotlib"} <= names
        assert all(spec.kind in ("cmd", "pkg") for spec in DEFAULT_SPECS)

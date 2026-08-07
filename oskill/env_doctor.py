"""oskill.env_doctor — 环境检查与安装向导 (doctor SKILL 3O 内化)。

机制: 平台检测 → 依赖探测 (cmd / python 包) → 结构化报告 → 按平台生成安装
命令 → 用户确认后执行并复检。依赖清单由调用方注入 (DepSpec), 本模块不绑定
任何具体领域工具链; DEFAULT_SPECS 仅提供通用科学计算栈示例。

零 veya 反向依赖: 探测与安装执行走 oprim.bash_exec; 缺失命令返回结构化结果。
"""

from __future__ import annotations

import importlib
import importlib.metadata
import platform as _platform
import shlex
from dataclasses import dataclass, field
from typing import Any, Literal

from oprim._bash_exec import bash_exec

# ── 数据结构 ────────────────────────────────────────────────────────

DepKind = Literal["cmd", "pkg"]


@dataclass(frozen=True)
class DepSpec:
    """单个依赖的声明式描述。

    Attributes:
        name: 依赖名 (报告/安装键)。
        kind: "cmd" = 命令探测 (command -v), "pkg" = python 包探测 (import)。
        check: cmd 时为命令名; pkg 时为 import 名。
        purpose: 用途说明。
        required: 是否必须; False 缺失只列入可选项。
        installs: 平台标签 → 安装命令列表。标签匹配顺序:
            linux-<distro> → linux / windows / mac → all。
    """

    name: str
    kind: DepKind
    check: str
    purpose: str = ""
    required: bool = True
    installs: dict[str, list[str]] = field(default_factory=dict)


@dataclass(frozen=True)
class CheckResult:
    """单个依赖的探测结果。

    Attributes:
        name: 依赖名。
        status: "ok" 或 "miss"。
        detail: 命中时输出 (版本/路径), 缺失时为空。
        required: 是否必须。
    """

    name: str
    status: str
    detail: str
    required: bool


@dataclass
class DoctorReport:
    """环境检查总报告。

    Attributes:
        platform: detect_platform() 输出。
        results: 全部探测结果。
        missing_required: 缺失的必须项。
        missing_optional: 缺失的可选项。
        install_commands: 缺失项 → 当前平台安装命令。
        install_results: auto_install 执行结果 (name → {cmd, ok, code})。
        ready: 必须项全部就绪。
    """

    platform: dict[str, Any]
    results: list[CheckResult]
    missing_required: list[str]
    missing_optional: list[str]
    install_commands: dict[str, list[str]]
    install_results: dict[str, dict[str, Any]] = field(default_factory=dict)
    ready: bool = False


# ── 平台检测 ────────────────────────────────────────────────────────


def _have(bin_name: str) -> bool:
    """探测命令是否存在 (不抛异常)。"""
    result = bash_exec(f"command -v {shlex.quote(bin_name)}")
    return result.ok and bool(result.stdout.strip())


def _read_os_release_id() -> str:
    """读取 /etc/os-release 的 ID 字段 (Linux)。"""
    try:
        for line in open("/etc/os-release", encoding="utf-8"):
            if line.startswith("ID="):
                return line.strip().split("=", 1)[1].strip().strip('"')
    except OSError:
        pass
    return ""


def _import_module(name: str) -> object:
    """importlib 间接层 (便于测试注入)。"""
    return importlib.import_module(name)


def _pkg_version(name: str) -> str:
    """包版本间接层 (便于测试注入)。"""
    return importlib.metadata.version(name)


def detect_platform() -> dict[str, Any]:
    """检测当前平台与可用包管理器。

    Returns:
        {system, platform_tag, distro, pkg_managers}
        platform_tag 为 mac / linux / windows / unknown; distro 仅 Linux 填充
        (来自 /etc/os-release 的 ID, 如 ubuntu/debian/fedora/arch)。
    """
    system = _platform.system().lower()
    if system == "darwin":
        tag = "mac"
    elif system == "linux":
        tag = "linux"
    elif system == "windows":
        tag = "windows"
    else:
        tag = "unknown"

    distro = ""
    if tag == "linux":
        distro = _read_os_release_id()

    pkg_managers = [
        name for name in ("winget", "scoop", "choco", "brew", "apt", "dnf", "pacman")
        if _have(name)
    ]
    return {
        "system": system,
        "platform_tag": tag,
        "distro": distro,
        "pkg_managers": pkg_managers,
    }


# ── 依赖探测 ────────────────────────────────────────────────────────


def check_dependencies(specs: list[DepSpec]) -> list[CheckResult]:
    """探测一组依赖。

    Args:
        specs: 依赖清单。

    Returns:
        每个 spec 一个 CheckResult (顺序与 specs 一致)。

    Example:
        >>> r = check_dependencies([DepSpec(name="python3", kind="cmd", check="python3")])
        >>> r[0].name
        'python3'
    """
    results: list[CheckResult] = []
    for spec in specs:
        if spec.kind == "cmd":
            result = bash_exec(f"command -v {shlex.quote(spec.check)}")
            ok = result.ok and bool(result.stdout.strip())
            detail = result.stdout.strip() if ok else ""
        else:  # pkg
            try:
                _import_module(spec.check)
                ok = True
                try:
                    detail = _pkg_version(spec.check)
                except importlib.metadata.PackageNotFoundError:
                    detail = "installed"
            except ImportError:
                ok = False
                detail = ""
        results.append(
            CheckResult(
                name=spec.name,
                status="ok" if ok else "miss",
                detail=detail,
                required=spec.required,
            )
        )
    return results


# ── 安装命令选择 ────────────────────────────────────────────────────


def install_commands(spec: DepSpec, platform_info: dict[str, Any]) -> list[str]:
    """按平台从 spec.installs 选择安装命令。

    匹配顺序: linux-<distro> (仅 Linux 有 distro) → platform_tag → all。
    未命中返回空列表。

    Args:
        spec: 依赖定义。
        platform_info: detect_platform() 输出。

    Returns:
        安装命令列表 (可能为空)。

    Example:
        >>> spec = DepSpec(name="x", kind="cmd", check="x",
        ...                installs={"linux-ubuntu": ["sudo apt install x"],
        ...                          "linux": ["snap install x"]})
        >>> install_commands(spec, {"platform_tag": "linux", "distro": "ubuntu"})
        ['sudo apt install x']
    """
    tag = platform_info.get("platform_tag", "unknown")
    distro = platform_info.get("distro", "")
    keys: list[str] = []
    if tag == "linux" and distro:
        keys.append(f"linux-{distro}")
    keys.append(tag)
    keys.append("all")
    for key in keys:
        if key in spec.installs:
            return list(spec.installs[key])
    return []


# ── 总入口 ──────────────────────────────────────────────────────────


def run_doctor(
    specs: list[DepSpec],
    *,
    auto_install: bool = False,
) -> DoctorReport:
    """执行完整检查流程: 平台检测 → 探测 → 报告 (可选自动安装必须项并复检)。

    Args:
        specs: 依赖清单。
        auto_install: True 时自动执行缺失**必须项**的安装命令 (按平台选择),
            完成后复检; 可选项只列命令不执行。

    Returns:
        DoctorReport 总报告。

    Example:
        >>> report = run_doctor(DEFAULT_SPECS)
        >>> report.ready in (True, False)
        True
    """
    platform_info = detect_platform()
    results = check_dependencies(specs)
    spec_by_name = {spec.name: spec for spec in specs}

    missing_required = [r.name for r in results if r.status == "miss" and r.required]
    missing_optional = [r.name for r in results if r.status == "miss" and not r.required]
    install_commands_map = {
        r.name: install_commands(spec_by_name[r.name], platform_info)
        for r in results
        if r.status == "miss"
    }

    install_results: dict[str, dict[str, Any]] = {}
    if auto_install and missing_required:
        for name in list(missing_required):
            for cmd in install_commands_map.get(name, []):
                res = bash_exec(cmd, timeout=600)
                install_results[name] = {
                    "cmd": cmd,
                    "ok": res.ok,
                    "code": res.code,
                    "stdout": res.stdout[-500:],
                    "stderr": res.stderr[-500:],
                }
        # 复检缺失必须项
        recheck = check_dependencies(
            [spec for spec in specs if spec.name in missing_required]
        )
        for r in recheck:
            if r.status == "ok" and r.name in missing_required:
                missing_required.remove(r.name)

    return DoctorReport(
        platform=platform_info,
        results=results,
        missing_required=missing_required,
        missing_optional=missing_optional,
        install_commands=install_commands_map,
        install_results=install_results,
        ready=not missing_required,
    )


# ── 内置示例清单 (通用科学计算栈, 非领域绑定) ──────────────────────


DEFAULT_SPECS: list[DepSpec] = [
    DepSpec(
        name="python3",
        kind="cmd",
        check="python3",
        purpose="Python 运行时 (Windows 下可能为 python)",
        required=True,
        installs={
            "mac": ["brew install python"],
            "linux-apt": ["sudo apt install python3 python3-pip"],
            "linux-dnf": ["sudo dnf install python3 python3-pip"],
            "linux-pacman": ["sudo pacman -S python"],
            "windows": ["winget install Python.Python.3"],
        },
    ),
    DepSpec(
        name="numpy",
        kind="pkg",
        check="numpy",
        purpose="数值计算",
        required=True,
        installs={"all": ["pip3 install numpy"]},
    ),
    DepSpec(
        name="pandas",
        kind="pkg",
        check="pandas",
        purpose="数据处理",
        required=True,
        installs={"all": ["pip3 install pandas"]},
    ),
    DepSpec(
        name="matplotlib",
        kind="pkg",
        check="matplotlib",
        purpose="图表生成",
        required=True,
        installs={"all": ["pip3 install matplotlib"]},
    ),
]

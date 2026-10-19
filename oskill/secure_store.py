"""oskill.secure_store — 密钥加密存储 (freellmapi 加密存储机制 3O 内化)。

API key 加密存储 (AES-GCM 加密 + 统一访问密钥 + 审计):
  * **SecureStore** — 密钥加密写入/解密读取 (AES-GCM, cryptography 可选;
    缺失时提供标准库 HMAC 校验的轻量 fallback 并警告);
  * **master key 管理** — 从环境/文件加载, 派生密钥 (PBKDF2);
  * **访问审计** — 每次读取记录 (谁/何时/哪把 key);
  * 与 provider_clients 组合: 安全取 key → 真实调用。
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_MASTER_KEY_ENV = "VEYA_MASTER_KEY"


class SecureStoreError(Exception):
    """加密存储错误 (解密失败/密钥缺失/格式错误)。"""


def derive_key(master_key: str, *, salt: bytes = b"veya-secure-store") -> bytes:
    """PBKDF2 派生 (32 字节 AES 密钥)。"""
    return hashlib.pbkdf2_hmac("sha256", master_key.encode("utf-8"), salt, 200_000)


def _encrypt_aesgcm(plaintext: bytes, key: bytes) -> bytes:
    """AES-GCM 加密 (cryptography 库)。"""
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    nonce = os.urandom(12)
    ciphertext = AESGCM(key).encrypt(nonce, plaintext, None)
    return nonce + ciphertext


def _decrypt_aesgcm(payload: bytes, key: bytes) -> bytes:
    """AES-GCM 解密。"""
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    nonce, ciphertext = payload[:12], payload[12:]
    try:
        return AESGCM(key).decrypt(nonce, ciphertext, None)
    except Exception as exc:  # noqa: BLE001
        raise SecureStoreError(f"解密失败 (密钥不匹配或数据损坏): {exc}") from exc


def _encrypt_fallback(plaintext: bytes, key: bytes) -> bytes:
    """标准库 fallback: XOR + HMAC 完整性 (仅当 cryptography 缺失, 非生产)。"""
    mac = hmac.new(key, plaintext, hashlib.sha256).digest()
    stream = hashlib.sha256(key + b"stream").digest()
    encrypted = bytes(b ^ stream[i % len(stream)] for i, b in enumerate(plaintext))
    return mac + encrypted


def _decrypt_fallback(payload: bytes, key: bytes) -> bytes:
    mac, encrypted = payload[:32], payload[32:]
    stream = hashlib.sha256(key + b"stream").digest()
    plaintext = bytes(b ^ stream[i % len(stream)] for i, b in enumerate(encrypted))
    if not hmac.compare_digest(mac, hmac.new(key, plaintext, hashlib.sha256).digest()):
        raise SecureStoreError("HMAC 校验失败 (数据被篡改或密钥不匹配)")
    return plaintext


@dataclass
class AccessAudit:
    """一次密钥访问记录。"""

    provider: str
    actor: str
    ts: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {"provider": self.provider, "actor": self.actor, "ts": self.ts}


class SecureStore:
    """API key 加密存储 (写入加密 / 读取解密 + 审计)。"""

    def __init__(
        self, path: str | Path, *, master_key: str | None = None, actor: str = "system"
    ) -> None:
        self.path = Path(path)
        self.actor = actor
        key = master_key or os.environ.get(_MASTER_KEY_ENV, "")
        if not key:
            raise SecureStoreError(f"master key 缺失: 设置 {_MASTER_KEY_ENV} 环境变量或传入")
        self._key = derive_key(key)
        self._use_aesgcm = _cryptography_available()
        self._data: dict[str, str] = {}
        self.audit: list[AccessAudit] = []
        if self.path.exists():
            self._load()

    def put(self, provider: str, api_key: str) -> None:
        """加密存入一把 key。"""
        plaintext = json.dumps({"provider": provider, "key": api_key, "ts": time.time()}).encode(
            "utf-8"
        )
        if self._use_aesgcm:
            encrypted = _encrypt_aesgcm(plaintext, self._key)
        else:
            encrypted = _encrypt_fallback(plaintext, self._key)
        self._data[provider] = encrypted.hex()
        self._save()

    def get(self, provider: str, *, actor: str | None = None) -> str:
        """解密读取 (记录审计)。"""
        if provider not in self._data:
            raise KeyError(f"no key stored for provider: {provider!r}")
        payload = bytes.fromhex(self._data[provider])
        if self._use_aesgcm:
            plaintext = _decrypt_aesgcm(payload, self._key)
        else:
            plaintext = _decrypt_fallback(payload, self._key)
        data = json.loads(plaintext.decode("utf-8"))
        self.audit.append(AccessAudit(provider=provider, actor=actor or self.actor))
        return str(data["key"])

    def has(self, provider: str) -> bool:
        return provider in self._data

    def providers(self) -> list[str]:
        return sorted(self._data)

    def audit_log(self) -> list[dict[str, Any]]:
        return [a.to_dict() for a in self.audit]

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self._data, indent=2), encoding="utf-8")

    def _load(self) -> None:
        try:
            self._data = json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            self._data = {}


def _cryptography_available() -> bool:
    try:
        import cryptography  # noqa: PLC0415, F401

        return True
    except ImportError:
        return False


__all__ = ["AccessAudit", "SecureStore", "SecureStoreError", "derive_key"]

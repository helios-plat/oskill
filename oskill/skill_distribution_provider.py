"""Canonical skill distribution provider.

The element owns the protocol for discovering and verifying skills.  A local
directory and a remote protocol client are providers; neither protocol
details nor business context are embedded in a Skill model.  Loading is
progressive: descriptors are level 0, instructions/manifests are level 1,
resources are level 2, and large examples/assets are level 3.
"""

from __future__ import annotations

import hashlib
import json
import re
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from obase.element_contract import ElementContract, zero_authority


class SkillDistributionError(Exception):
    """Base error for malformed, unavailable, or incompatible skills."""


class SkillNotFoundError(SkillDistributionError):
    """The requested skill or version does not exist."""


class SkillConflictError(SkillDistributionError):
    """Dependency constraints cannot be satisfied together."""


class SkillDigestMismatch(SkillDistributionError):
    """A fetched skill/resource does not match its declared digest."""


@dataclass(frozen=True, slots=True)
class SkillDigest:
    value: str
    algorithm: str = "sha256"

    def __post_init__(self) -> None:
        if not self.value:
            raise ValueError("SkillDigest.value must be non-empty")
        if self.algorithm.lower() != "sha256":
            raise ValueError("only sha256 is supported by the native provider")

    def __str__(self) -> str:
        return f"{self.algorithm.lower()}:{self.value}"


@dataclass(frozen=True, slots=True)
class SkillSource:
    kind: str
    ref: str
    version: str = ""
    digest: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "ref": self.ref,
            "version": self.version,
            "digest": self.digest,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> SkillSource:
        return cls(
            kind=str(data.get("kind", "unknown")),
            ref=str(data.get("ref", data.get("uri", ""))),
            version=str(data.get("version", "")),
            digest=str(data.get("digest", "")),
        )


@dataclass(frozen=True, slots=True)
class SkillVersion:
    skill_id: str
    version: str
    digest: str
    manifest_ref: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "skill_id": self.skill_id,
            "version": self.version,
            "digest": self.digest,
            "manifest_ref": self.manifest_ref,
        }


@dataclass(frozen=True, slots=True)
class SkillResource:
    path: str
    digest: str
    size: int = 0
    level: int = 2
    kind: str = "file"

    def __post_init__(self) -> None:
        if not self.path or Path(self.path).is_absolute() or ".." in Path(self.path).parts:
            raise ValueError("SkillResource.path must be a safe relative path")
        if self.level not in {2, 3}:
            raise ValueError("SkillResource.level must be 2 or 3")

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "digest": self.digest,
            "size": self.size,
            "level": self.level,
            "kind": self.kind,
        }


@dataclass(frozen=True, slots=True)
class SkillDependency:
    skill_id: str
    version_constraint: str = "*"
    optional: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "skill_id": self.skill_id,
            "version_constraint": self.version_constraint,
            "optional": self.optional,
        }


@dataclass(frozen=True, slots=True)
class SkillDescriptor:
    skill_id: str
    name: str
    description: str = ""
    latest_version: str = "1.0.0"
    source: SkillSource = field(default_factory=lambda: SkillSource("unknown", ""))
    trust_metadata: Mapping[str, Any] = field(default_factory=dict)

    @property
    def id(self) -> str:
        return self.skill_id

    def to_dict(self) -> dict[str, Any]:
        return {
            "skill_id": self.skill_id,
            "name": self.name,
            "description": self.description,
            "latest_version": self.latest_version,
            "source": self.source.to_dict(),
            "trust_metadata": dict(self.trust_metadata),
        }


@dataclass(frozen=True, slots=True)
class SkillDistributionRef:
    skill_id: str
    version: str = ""
    digest: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "skill_id": self.skill_id,
            "version": self.version,
            "digest": self.digest,
        }


@dataclass(frozen=True, slots=True)
class SkillBundle:
    descriptor: SkillDescriptor
    version: SkillVersion
    instructions: str = ""
    resources: tuple[SkillResource, ...] = ()
    dependencies: tuple[SkillDependency, ...] = ()
    source: SkillSource = field(default_factory=lambda: SkillSource("unknown", ""))
    trust_metadata: Mapping[str, Any] = field(default_factory=dict)
    manifest: Mapping[str, Any] = field(default_factory=dict)
    disclosure_level: int = 1
    loaded_at: float = 0.0

    @property
    def skill_id(self) -> str:
        return self.version.skill_id

    @property
    def digest(self) -> str:
        return self.version.digest

    def ref(self) -> SkillDistributionRef:
        return SkillDistributionRef(self.skill_id, self.version.version, self.digest)

    def to_dict(self) -> dict[str, Any]:
        return {
            "descriptor": self.descriptor.to_dict(),
            "version": self.version.to_dict(),
            "instructions": self.instructions,
            "resources": [item.to_dict() for item in self.resources],
            "dependencies": [item.to_dict() for item in self.dependencies],
            "source": self.source.to_dict(),
            "trust_metadata": dict(self.trust_metadata),
            "manifest": dict(self.manifest),
            "disclosure_level": self.disclosure_level,
            "loaded_at": self.loaded_at,
        }


@runtime_checkable
class SkillDistributionProvider(Protocol):
    """Canonical provider protocol; implementations own transport and cache I/O."""

    async def list(
        self,
        *,
        query: str | None = None,
        business_context: Mapping[str, Any] | None = None,
    ) -> Sequence[SkillDescriptor]: ...

    async def get(
        self,
        skill_id: str,
        version: str | None = None,
        *,
        level: int = 1,
        business_context: Mapping[str, Any] | None = None,
    ) -> SkillBundle: ...

    async def resolve(
        self,
        ref: SkillDistributionRef | str | Mapping[str, Any],
        *,
        level: int = 1,
        business_context: Mapping[str, Any] | None = None,
    ) -> SkillBundle: ...

    async def fetch_resource(
        self, ref: SkillDistributionRef | SkillBundle | str, path: str
    ) -> bytes: ...

    async def verify_digest(
        self,
        value: SkillBundle | SkillDistributionRef | bytes,
        expected_digest: str | None = None,
    ) -> bool: ...

    async def dependencies(
        self, ref: SkillDistributionRef | SkillBundle | str
    ) -> Sequence[SkillDependency]: ...


@runtime_checkable
class SkillCachePort(Protocol):
    async def get(self, ref: SkillDistributionRef) -> SkillBundle | None: ...

    async def put(self, bundle: SkillBundle) -> None: ...


class MemorySkillCache:
    """Offline cache provider used by tests and explicit local deployments."""

    def __init__(self) -> None:
        self._items: dict[tuple[str, str, str], SkillBundle] = {}

    async def get(self, ref: SkillDistributionRef) -> SkillBundle | None:
        key = (ref.skill_id, ref.version, ref.digest)
        if ref.digest:
            return self._items.get(key)
        matches = [
            value
            for (skill_id, version, _), value in self._items.items()
            if skill_id == ref.skill_id and (not ref.version or version == ref.version)
        ]
        return (
            max(matches, key=lambda item: _version_key(item.version.version)) if matches else None
        )

    async def put(self, bundle: SkillBundle) -> None:
        ref = bundle.ref()
        self._items[(ref.skill_id, ref.version, ref.digest)] = bundle


class JsonSkillCache:
    """Versioned JSON cache with atomic replacement and no network dependency."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)

    def _path(self, ref: SkillDistributionRef) -> Path:
        key = hashlib.sha256(f"{ref.skill_id}\0{ref.version}\0{ref.digest}".encode()).hexdigest()
        return self.root / f"{key}.json"

    async def get(self, ref: SkillDistributionRef) -> SkillBundle | None:
        path = self._path(ref)
        try:
            return _bundle_from_dict(json.loads(path.read_text(encoding="utf-8")))
        except (FileNotFoundError, OSError, ValueError, TypeError, KeyError):
            return None

    async def put(self, bundle: SkillBundle) -> None:
        path = self._path(bundle.ref())
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".json.tmp")
        temporary.write_text(_canonical_json(bundle.to_dict()), encoding="utf-8")
        temporary.replace(path)


class LocalSkillDistributionProvider:
    """Read-only local skill provider with dependency and digest validation."""

    name = "local"

    def __init__(self, root: str | Path, *, cache: SkillCachePort | None = None) -> None:
        self.root = Path(root).resolve()
        self.cache = cache

    async def list(
        self,
        *,
        query: str | None = None,
        business_context: Mapping[str, Any] | None = None,
    ) -> Sequence[SkillDescriptor]:
        del business_context
        if not self.root.exists():
            return ()
        descriptors: list[SkillDescriptor] = []
        for candidate in sorted(self.root.iterdir()):
            if not candidate.is_dir() or candidate.name.startswith("."):
                continue
            try:
                versions = self._version_directories(candidate.name)
                if not versions:
                    continue
                bundle = self._read_bundle(candidate.name, _highest_version(versions), level=0)
            except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
                raise SkillDistributionError(f"malformed skill {candidate.name}: {exc}") from exc
            if query:
                haystack = (
                    f"{bundle.descriptor.skill_id} {bundle.descriptor.name} "
                    f"{bundle.descriptor.description}"
                ).lower()
                if query.lower() not in haystack:
                    continue
            descriptors.append(bundle.descriptor)
        return tuple(descriptors)

    async def get(
        self,
        skill_id: str,
        version: str | None = None,
        *,
        level: int = 1,
        business_context: Mapping[str, Any] | None = None,
    ) -> SkillBundle:
        del business_context
        self._validate_skill_id(skill_id)
        try:
            versions = self._version_directories(skill_id)
        except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
            raise SkillDistributionError(f"malformed skill {skill_id}: {exc}") from exc
        selected = version or (_highest_version(versions) if versions else "")
        if self.cache is not None:
            cached = await self.cache.get(SkillDistributionRef(skill_id, selected))
            if cached is not None and (not selected or cached.version.version == selected):
                return _at_level(cached, level)
        if not selected:
            raise SkillNotFoundError(f"skill not found: {skill_id}")
        if selected not in versions:
            raise SkillNotFoundError(f"skill version not found: {skill_id}@{selected}")
        try:
            bundle = self._read_bundle(skill_id, selected, level=level)
        except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
            raise SkillDistributionError(f"malformed skill {skill_id}@{selected}: {exc}") from exc
        if self.cache is not None:
            await self.cache.put(bundle)
        return bundle

    async def resolve(
        self,
        ref: SkillDistributionRef | str | Mapping[str, Any],
        *,
        level: int = 1,
        business_context: Mapping[str, Any] | None = None,
    ) -> SkillBundle:
        del business_context
        normalized = _normalize_ref(ref)
        if _looks_like_constraint(normalized.version):
            versions = self._version_directories(normalized.skill_id)
            selected = _select_version(versions, normalized.version)
            if selected is None:
                if normalized.version == "*":
                    return await self.get(normalized.skill_id, level=level)
                raise SkillConflictError(
                    f"no version satisfies {normalized.skill_id}@{normalized.version}"
                )
            normalized = SkillDistributionRef(normalized.skill_id, selected, normalized.digest)
        bundle = await self.get(normalized.skill_id, normalized.version or None, level=level)
        if normalized.digest and bundle.digest != normalized.digest:
            raise SkillDigestMismatch(
                f"digest mismatch for {bundle.skill_id}@{bundle.version.version}"
            )
        await self._validate_dependency_graph(bundle, stack=())
        return bundle

    async def fetch_resource(
        self, ref: SkillDistributionRef | SkillBundle | str, path: str
    ) -> bytes:
        if isinstance(ref, SkillBundle):
            bundle = (
                ref
                if ref.disclosure_level >= 2
                else await self.get(ref.skill_id, ref.version.version, level=2)
            )
        else:
            bundle = await self.resolve(ref, level=2)
        safe_path = _safe_resource_path(path)
        descriptor = next((item for item in bundle.resources if item.path == safe_path), None)
        if descriptor is None:
            raise SkillNotFoundError(f"resource not declared: {bundle.skill_id}/{safe_path}")
        base = self._base_directory(bundle.skill_id, bundle.version.version)
        candidate = (base / safe_path).resolve()
        if base not in candidate.parents:
            raise SkillDistributionError("resource path escapes skill root")
        try:
            payload = candidate.read_bytes()
        except OSError as exc:
            raise SkillNotFoundError(f"resource unavailable: {safe_path}") from exc
        if _sha256(payload) != _digest_value(descriptor.digest):
            raise SkillDigestMismatch(f"resource digest mismatch: {safe_path}")
        return payload

    async def verify_digest(
        self,
        value: SkillBundle | SkillDistributionRef | bytes,
        expected_digest: str | None = None,
    ) -> bool:
        if isinstance(value, bytes):
            actual = _sha256(value)
            return expected_digest is not None and actual == _digest_value(expected_digest)
        bundle = value if isinstance(value, SkillBundle) else await self.resolve(value, level=2)
        expected = expected_digest or bundle.digest
        actual = self._bundle_digest(bundle.skill_id, bundle.version.version)
        return bool(expected) and actual == _digest_value(expected)

    async def dependencies(
        self, ref: SkillDistributionRef | SkillBundle | str
    ) -> Sequence[SkillDependency]:
        bundle = ref if isinstance(ref, SkillBundle) else await self.resolve(ref, level=1)
        return bundle.dependencies

    async def _validate_dependency_graph(
        self, bundle: SkillBundle, *, stack: tuple[str, ...]
    ) -> None:
        key = f"{bundle.skill_id}@{bundle.version.version}"
        if key in stack:
            raise SkillConflictError(f"cyclic skill dependency: {' -> '.join((*stack, key))}")
        for dependency in bundle.dependencies:
            try:
                target = await self.resolve(
                    SkillDistributionRef(dependency.skill_id, dependency.version_constraint),
                    level=1,
                )
            except SkillDistributionError:
                if dependency.optional:
                    continue
                raise
            await self._validate_dependency_graph(target, stack=(*stack, key))

    def _version_directories(self, skill_id: str) -> dict[str, Path]:
        self._validate_skill_id(skill_id)
        skill_root = (self.root / skill_id).resolve()
        if self.root not in skill_root.parents:
            raise SkillDistributionError("skill path escapes provider root")
        if not skill_root.is_dir():
            return {}
        direct = skill_root / "SKILL.md"
        if direct.is_file():
            return {self._manifest_version(skill_root): skill_root}
        versions: dict[str, Path] = {}
        for candidate in sorted(skill_root.iterdir()):
            if candidate.is_dir() and (candidate / "SKILL.md").is_file():
                versions[self._manifest_version(candidate)] = candidate
        return versions

    def _read_bundle(self, skill_id: str, version: str, *, level: int) -> SkillBundle:
        if level not in {0, 1, 2, 3}:
            raise ValueError("disclosure level must be between 0 and 3")
        base = self._version_directories(skill_id).get(version)
        if base is None:
            raise SkillNotFoundError(f"skill version not found: {skill_id}@{version}")
        manifest = self._read_manifest(base)
        instructions = (base / "SKILL.md").read_text(encoding="utf-8") if level >= 1 else ""
        resources = self._resources(base, manifest, level=level)
        dependencies = tuple(
            SkillDependency(
                skill_id=str(item.get("skill_id", item.get("id", ""))),
                version_constraint=str(item.get("version", item.get("constraint", "*"))),
                optional=bool(item.get("optional", False)),
            )
            for item in manifest.get("dependencies", [])
            if isinstance(item, Mapping)
        )
        if any(not item.skill_id for item in dependencies):
            raise ValueError("skill dependency id must be non-empty")
        source = SkillSource(
            kind=str(manifest.get("source_kind", "local")),
            ref=str(manifest.get("source", str(base))),
            version=version,
            digest=str(manifest.get("digest", "")),
        )
        digest = self._bundle_digest(skill_id, version)
        descriptor = SkillDescriptor(
            skill_id=skill_id,
            name=str(manifest.get("name", skill_id)),
            description=str(manifest.get("description", "")),
            latest_version=version,
            source=source,
            trust_metadata=dict(manifest.get("trust", manifest.get("trust_metadata", {}))),
        )
        return SkillBundle(
            descriptor=descriptor,
            version=SkillVersion(skill_id, version, digest, str(base)),
            instructions=instructions,
            resources=resources,
            dependencies=dependencies,
            source=SkillSource(source.kind, source.ref, version, digest),
            trust_metadata=descriptor.trust_metadata,
            manifest=manifest if level >= 1 else {},
            disclosure_level=level,
            loaded_at=time.time(),
        )

    def _resources(
        self, base: Path, manifest: Mapping[str, Any], *, level: int
    ) -> tuple[SkillResource, ...]:
        declared = manifest.get("resources")
        paths: list[tuple[str, int, str]] = []
        if isinstance(declared, Sequence) and not isinstance(declared, (str, bytes)):
            for item in declared:
                if not isinstance(item, Mapping):
                    raise ValueError("resource manifest entry must be an object")
                path = _safe_resource_path(str(item.get("path", "")))
                resource_level = int(item.get("level", _resource_level(path)))
                paths.append((path, resource_level, str(item.get("kind", "file"))))
        elif level >= 2:
            for candidate in sorted(base.rglob("*")):
                if not candidate.is_file() or candidate.name in {
                    "SKILL.md",
                    "manifest.json",
                    "skill.json",
                }:
                    continue
                path = str(candidate.relative_to(base))
                paths.append((path, _resource_level(path), "file"))
        resources: list[SkillResource] = []
        for path, resource_level, kind in paths:
            if resource_level > level:
                continue
            payload = (base / path).resolve()
            if base not in payload.parents or not payload.is_file():
                raise ValueError(f"resource is missing or escapes skill root: {path}")
            content = payload.read_bytes()
            declared_digest = next(
                (
                    str(item.get("digest", ""))
                    for item in (declared or ())
                    if isinstance(item, Mapping) and str(item.get("path", "")) == path
                ),
                "",
            )
            resources.append(
                SkillResource(
                    path,
                    declared_digest or _sha256(content),
                    len(content),
                    resource_level,
                    kind,
                )
            )
        return tuple(sorted(resources, key=lambda item: item.path))

    def _bundle_digest(self, skill_id: str, version: str) -> str:
        base = self._version_directories(skill_id).get(version)
        if base is None:
            raise SkillNotFoundError(f"skill version not found: {skill_id}@{version}")
        manifest = self._read_manifest(base)
        parts: list[tuple[str, str]] = []
        for candidate in sorted(base.rglob("*")):
            if not candidate.is_file() or candidate.name in {"manifest.json", "skill.json"}:
                continue
            parts.append((str(candidate.relative_to(base)), _sha256(candidate.read_bytes())))
        return _sha256(
            _canonical_json(
                {
                    "skill_id": skill_id,
                    "version": version,
                    "manifest": manifest,
                    "files": parts,
                }
            ).encode()
        )

    @staticmethod
    def _manifest_version(base: Path) -> str:
        manifest = LocalSkillDistributionProvider._read_manifest(base)
        return str(manifest.get("version", "1.0.0"))

    @staticmethod
    def _read_manifest(base: Path) -> dict[str, Any]:
        for name in ("manifest.json", "skill.json"):
            path = base / name
            if path.is_file():
                value = json.loads(path.read_text(encoding="utf-8"))
                if not isinstance(value, dict):
                    raise ValueError("skill manifest must be a JSON object")
                return value
        return {"version": "1.0.0", "name": base.parent.name}

    def _base_directory(self, skill_id: str, version: str) -> Path:
        base = self._version_directories(skill_id).get(version)
        if base is None:
            raise SkillNotFoundError(f"skill version not found: {skill_id}@{version}")
        return base.resolve()

    @staticmethod
    def _validate_skill_id(skill_id: str) -> None:
        if not skill_id or Path(skill_id).is_absolute() or ".." in Path(skill_id).parts:
            raise ValueError("skill_id must be a safe relative id")


@runtime_checkable
class SkillResourceClient(Protocol):
    """Generic remote resource protocol; MCP is one possible adapter."""

    async def list(self, **kwargs: Any) -> Sequence[SkillDescriptor | Mapping[str, Any]]: ...

    async def get(self, **kwargs: Any) -> SkillBundle | Mapping[str, Any]: ...

    async def fetch_resource(self, **kwargs: Any) -> bytes: ...


class McpSkillDistributionProvider:
    """Protocol adapter whose transport is injected and may speak MCP."""

    name = "remote-resource"

    def __init__(self, client: SkillResourceClient) -> None:
        self.client = client

    async def list(
        self,
        *,
        query: str | None = None,
        business_context: Mapping[str, Any] | None = None,
    ) -> Sequence[SkillDescriptor]:
        raw = await self.client.list(query=query, business_context=business_context)
        return tuple(
            item if isinstance(item, SkillDescriptor) else _descriptor_from_dict(item)
            for item in raw
        )

    async def get(
        self,
        skill_id: str,
        version: str | None = None,
        *,
        level: int = 1,
        business_context: Mapping[str, Any] | None = None,
    ) -> SkillBundle:
        raw = await self.client.get(
            skill_id=skill_id,
            version=version,
            level=level,
            business_context=business_context,
        )
        return raw if isinstance(raw, SkillBundle) else _bundle_from_dict(raw)

    async def resolve(
        self,
        ref: SkillDistributionRef | str | Mapping[str, Any],
        *,
        level: int = 1,
        business_context: Mapping[str, Any] | None = None,
    ) -> SkillBundle:
        normalized = _normalize_ref(ref)
        return await self.get(
            normalized.skill_id,
            normalized.version or None,
            level=level,
            business_context=business_context,
        )

    async def fetch_resource(
        self, ref: SkillDistributionRef | SkillBundle | str, path: str
    ) -> bytes:
        normalized = ref.ref() if isinstance(ref, SkillBundle) else _normalize_ref(ref)
        return await self.client.fetch_resource(
            skill_id=normalized.skill_id,
            version=normalized.version,
            digest=normalized.digest,
            path=_safe_resource_path(path),
        )

    async def verify_digest(
        self,
        value: SkillBundle | SkillDistributionRef | bytes,
        expected_digest: str | None = None,
    ) -> bool:
        if isinstance(value, bytes):
            return expected_digest is not None and _sha256(value) == _digest_value(expected_digest)
        bundle = value if isinstance(value, SkillBundle) else await self.resolve(value, level=2)
        expected = expected_digest or bundle.digest
        payload = _canonical_json(bundle.to_dict()).encode("utf-8")
        return bool(expected) and _sha256(payload) == _digest_value(expected)

    async def dependencies(
        self, ref: SkillDistributionRef | SkillBundle | str
    ) -> Sequence[SkillDependency]:
        bundle = ref if isinstance(ref, SkillBundle) else await self.resolve(ref, level=1)
        return bundle.dependencies


ELEMENT_CONTRACT = ElementContract(
    element_id="skill_distribution_provider",
    element_version=1,
    owner_repo="oskill",
    canonical_import="oskill.skill_distribution_provider",
    canonical_export="SkillDistributionProvider",
    input_contract="skill ids, versions, distribution refs and disclosure levels",
    output_contract="SkillDescriptor, SkillBundle, SkillResource and dependency facts",
    dependency_ports=("SkillResourceClient(optional)", "SkillCachePort(optional)"),
    state_model="provider-owned catalog/cache state; no business task state",
    persistence_model="injected cache with optional atomic JSON implementation",
    authority_declaration=zero_authority(),
    async_contract="all provider operations are awaitable; transport owns scheduling",
    failure_semantics="malformed skills, conflicts and digest mismatches are explicit errors",
    recovery_semantics="offline cache may restore a verified bundle; unresolved deps remain errors",
    observability_contract=(
        "source, version, digest, trust metadata and disclosure level are visible"
    ),
    compatibility_contract="MCP is an adapter; core skill semantics remain protocol-owned",
    conformance_suite=(
        "LIST",
        "GET",
        "VERSION_RESOLUTION",
        "DIGEST_VERIFICATION",
        "RESOURCE_FETCH",
        "PROGRESSIVE_DISCLOSURE",
        "DEPENDENCY_RESOLUTION",
        "CONFLICT_DETECTION",
        "OFFLINE_CACHE",
        "MALFORMED_SKILL_REJECTED",
        "BUSINESS_CONTEXT_INJECTABLE",
        "SECOND_EXECUTION_AUTHORITY",
    ),
)


# Put the contract on the canonical protocol itself so consumers importing
# exactly ``SkillDistributionProvider`` can inspect it without learning about
# a second canonical class.
SkillDistributionProvider.ELEMENT_CONTRACT = ELEMENT_CONTRACT  # type: ignore[attr-defined]


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _digest_value(value: str) -> str:
    return value.split(":", 1)[1] if ":" in value else value


def _safe_resource_path(path: str) -> str:
    candidate = Path(path)
    if not path or candidate.is_absolute() or ".." in candidate.parts:
        raise ValueError("resource path must be safe and relative")
    return candidate.as_posix()


def _resource_level(path: str) -> int:
    lowered = path.lower()
    return 3 if lowered.startswith(("examples/", "assets/", "examples\\", "assets\\")) else 2


def _version_key(version: str) -> tuple[int, ...]:
    numbers = [int(item) for item in re.findall(r"\d+", version)]
    return tuple((numbers + [0, 0, 0])[:3])


def _highest_version(versions: Mapping[str, Path]) -> str:
    if not versions:
        raise SkillNotFoundError("skill has no versions")
    return max(versions, key=_version_key)


def _looks_like_constraint(value: str) -> bool:
    return bool(value) and (value == "*" or value[0] in "<>=~^")


def _satisfies(version: str, constraint: str) -> bool:
    if not constraint or constraint == "*":
        return True
    version_key = _version_key(version)
    for part in (piece.strip() for piece in constraint.split(",")):
        if not part or part == "*":
            continue
        operator = next(
            (prefix for prefix in (">=", "<=", ">", "<", "=", "~", "^") if part.startswith(prefix)),
            "=",
        )
        target = part[len(operator) :].strip()
        target_key = _version_key(target)
        if operator == ">=" and version_key < target_key:
            return False
        if operator == "<=" and version_key > target_key:
            return False
        if operator == ">" and version_key <= target_key:
            return False
        if operator == "<" and version_key >= target_key:
            return False
        if operator == "=" and version_key != target_key:
            return False
        if operator == "~" and (version_key < target_key or version_key[:2] != target_key[:2]):
            return False
        if operator == "^" and (version_key < target_key or version_key[0] != target_key[0]):
            return False
    return True


def _select_version(versions: Mapping[str, Path], constraint: str) -> str | None:
    candidates = [version for version in versions if _satisfies(version, constraint)]
    return max(candidates, key=_version_key) if candidates else None


def _normalize_ref(ref: SkillDistributionRef | str | Mapping[str, Any]) -> SkillDistributionRef:
    if isinstance(ref, SkillDistributionRef):
        return ref
    if isinstance(ref, Mapping):
        return SkillDistributionRef(
            str(ref.get("skill_id", ref.get("id", ""))),
            str(ref.get("version", "")),
            str(ref.get("digest", "")),
        )
    value = str(ref)
    skill_id, separator, version = value.partition("@")
    return SkillDistributionRef(skill_id, version if separator else "")


def _at_level(bundle: SkillBundle, level: int) -> SkillBundle:
    if level < 0 or level > 3:
        raise ValueError("disclosure level must be between 0 and 3")
    resources = tuple(item for item in bundle.resources if item.level <= level)
    return SkillBundle(
        descriptor=bundle.descriptor,
        version=bundle.version,
        instructions=bundle.instructions if level >= 1 else "",
        resources=resources if level >= 2 else (),
        dependencies=bundle.dependencies if level >= 1 else (),
        source=bundle.source,
        trust_metadata=bundle.trust_metadata,
        manifest=bundle.manifest if level >= 1 else {},
        disclosure_level=level,
        loaded_at=bundle.loaded_at,
    )


def _descriptor_from_dict(data: Mapping[str, Any]) -> SkillDescriptor:
    source = data.get("source", {})
    return SkillDescriptor(
        skill_id=str(data.get("skill_id", data.get("id", ""))),
        name=str(data.get("name", data.get("skill_id", data.get("id", "")))),
        description=str(data.get("description", "")),
        latest_version=str(data.get("latest_version", data.get("version", "1.0.0"))),
        source=source if isinstance(source, SkillSource) else SkillSource.from_dict(source),
        trust_metadata=dict(data.get("trust_metadata", {})),
    )


def _bundle_from_dict(data: Mapping[str, Any]) -> SkillBundle:
    descriptor_data = data.get("descriptor", {})
    version_data = data.get("version", {})
    descriptor = (
        descriptor_data
        if isinstance(descriptor_data, SkillDescriptor)
        else _descriptor_from_dict(descriptor_data)
    )
    version = (
        version_data
        if isinstance(version_data, SkillVersion)
        else SkillVersion(
            skill_id=str(version_data.get("skill_id", descriptor.skill_id)),
            version=str(version_data.get("version", descriptor.latest_version)),
            digest=str(version_data.get("digest", "")),
            manifest_ref=str(version_data.get("manifest_ref", "")),
        )
    )
    resources = tuple(
        item
        if isinstance(item, SkillResource)
        else SkillResource(
            path=str(item["path"]),
            digest=str(item.get("digest", "")),
            size=int(item.get("size", 0)),
            level=int(item.get("level", 2)),
            kind=str(item.get("kind", "file")),
        )
        for item in data.get("resources", [])
    )
    dependencies = tuple(
        item
        if isinstance(item, SkillDependency)
        else SkillDependency(
            skill_id=str(item.get("skill_id", item.get("id", ""))),
            version_constraint=str(item.get("version_constraint", item.get("version", "*"))),
            optional=bool(item.get("optional", False)),
        )
        for item in data.get("dependencies", [])
    )
    source = data.get("source", {})
    return SkillBundle(
        descriptor=descriptor,
        version=version,
        instructions=str(data.get("instructions", "")),
        resources=resources,
        dependencies=dependencies,
        source=source if isinstance(source, SkillSource) else SkillSource.from_dict(source),
        trust_metadata=dict(data.get("trust_metadata", {})),
        manifest=dict(data.get("manifest", {})),
        disclosure_level=int(data.get("disclosure_level", 1)),
        loaded_at=float(data.get("loaded_at", 0.0)),
    )


__all__ = [
    "JsonSkillCache",
    "LocalSkillDistributionProvider",
    "McpSkillDistributionProvider",
    "MemorySkillCache",
    "SkillBundle",
    "SkillConflictError",
    "SkillDependency",
    "SkillDescriptor",
    "SkillDigest",
    "SkillDigestMismatch",
    "SkillDistributionError",
    "SkillDistributionProvider",
    "ELEMENT_CONTRACT",
    "SkillDistributionRef",
    "SkillNotFoundError",
    "SkillResource",
    "SkillResourceClient",
    "SkillSource",
    "SkillVersion",
]

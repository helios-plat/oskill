"""Tests for oskill.osviking_bridge (OpenViking <-> Veya bridge)."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from oskill.memory_assets import (
    AssetRegistry,
    MemoryAsset,
    Principal,
    ASSET_CODEGRAPH,
    ASSET_CHAT_MEMORY,
    ASSET_SKILL,
    ASSET_WIKI,
    VISIBILITY_PRIVATE,
    VISIBILITY_TEAM,
    VISIBILITY_RESTRICTED,
)
from oskill.osviking_bridge import (
    OvAssetBridge,
    bridge_from_openviking,
    bridge_to_openviking,
    integrate_with_veya,
    integrate_to_openviking,
)


class TestOvAssetBridge:
    """Tests for the OpenViking <-> Veya asset bridge."""

    def test_bridge_from_openviking_v1(self):
        """Test loading OpenViking v1 export into Veya registry."""
        # Create sample OpenViking export
        ov_data = {
            "assets": [
                {
                    "id": "mem_001",
                    "type": "chat_memory",
                    "owner": "alice",
                    "visibility": "private",
                    "title": "User preferences",
                    "content": "Prefers Python, dark mode",
                    "acl": {"users": ["alice"], "roles": [], "agents": []},
                    "version": 1,
                },
                {
                    "id": "skill_001",
                    "type": "skill",
                    "owner": "bob",
                    "visibility": "team",
                    "title": "Code search",
                    "content": "Search code efficiently",
                    "acl": {"users": [], "roles": ["dev"], "agents": []},
                    "version": 1,
                },
                {
                    "id": "wiki_001",
                    "type": "wiki",
                    "owner": "alice",
                    "visibility": "restricted",
                    "title": "API docs",
                    "content": "REST API documentation",
                    "acl": {"users": ["alice", "bob"], "roles": [], "agents": []},
                    "version": 2,
                },
            ]
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            ov_path = Path(tmpdir) / "ov_export.json"
            with open(ov_path, "w") as f:
                json.dump(ov_data, f)

            bridge = OvAssetBridge().from_openviking_v1(ov_path)

        assert bridge.registry is not None
        assert len(bridge.registry.assets) == 3
        assert bridge.mapped_counts["chat_memory"] == 1
        assert bridge.mapped_counts["skill"] == 1
        assert bridge.mapped_counts["wiki"] == 1

        # Check asset mappings
        mem = bridge.registry.assets["mem_001"]
        assert mem.asset_type == ASSET_CHAT_MEMORY
        assert mem.owner == "alice"
        assert mem.visibility == VISIBILITY_PRIVATE

        skill = bridge.registry.assets["skill_001"]
        assert skill.asset_type == ASSET_SKILL
        assert skill.owner == "bob"
        assert skill.visibility == VISIBILITY_TEAM

        wiki = bridge.registry.assets["wiki_001"]
        assert wiki.asset_type == ASSET_WIKI
        assert wiki.owner == "alice"
        assert wiki.visibility == VISIBILITY_RESTRICTED

    def test_bridge_to_openviking_v1(self):
        """Test exporting Veya assets to OpenViking v1 format."""
        registry = AssetRegistry()
        registry.register(MemoryAsset(
            id="veya_mem_1",
            asset_type=ASSET_CHAT_MEMORY,
            owner="alice",
            visibility=VISIBILITY_PRIVATE,
            title="Test memory",
            content="Content here",
        ))
        registry.register(MemoryAsset(
            id="veya_skill_1",
            asset_type=ASSET_SKILL,
            owner="bob",
            visibility=VISIBILITY_TEAM,
            title="Test skill",
            content="Skill content",
        ))

        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = Path(tmpdir) / "ov_import.json"
            bridge = OvAssetBridge(registry=registry).to_openviking_v1(out_path)

            with open(out_path, "r") as f:
                exported = json.load(f)

        assert "assets" in exported
        assert len(exported["assets"]) == 2

        # Check mappings
        mem_exp = next(a for a in exported["assets"] if a["id"] == "veya_mem_1")
        assert mem_exp["type"] == "chat_memory"
        assert mem_exp["owner"] == "alice"
        assert mem_exp["visibility"] == "private"

        skill_exp = next(a for a in exported["assets"] if a["id"] == "veya_skill_1")
        assert skill_exp["type"] == "skill"
        assert skill_exp["owner"] == "bob"
        assert skill_exp["visibility"] == "team"

    def test_roundtrip_bridge(self):
        """Test round-trip: Veya -> OpenViking -> Veya preserves data."""
        from oskill.memory_assets import ACL
        original_registry = AssetRegistry()
        original_registry.register(MemoryAsset(
            id="roundtrip_1",
            asset_type=ASSET_CODEGRAPH,
            owner="alice",
            visibility=VISIBILITY_RESTRICTED,
            title="Roundtrip test",
            content="Roundtrip content",
            acl=ACL(users=["alice"], roles=["admin"], agents=["agent1"]),
            version=5,
        ))

        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = Path(tmpdir) / "roundtrip.json"
            
            # Export Veya -> OpenViking
            OvAssetBridge(registry=original_registry).to_openviking_v1(out_path)
            
            # Import OpenViking -> Veya
            new_registry = AssetRegistry()
            bridge = OvAssetBridge(registry=new_registry).from_openviking_v1(out_path)

        assert len(bridge.registry.assets) == 1
        imported = bridge.registry.assets["roundtrip_1"]
        assert imported.asset_type == ASSET_CODEGRAPH
        assert imported.owner == "alice"
        assert imported.visibility == VISIBILITY_RESTRICTED
        assert imported.title == "Roundtrip test"
        assert imported.content == "Roundtrip content"
        assert imported.acl.users == ["alice"]
        assert imported.acl.roles == ["admin"]
        assert imported.acl.agents == ["agent1"]
        assert imported.version == 5

    def test_convenience_functions(self):
        """Test convenience bridge functions."""
        ov_data = {
            "assets": [
                {
                    "id": "conv_1",
                    "type": "chat_memory",
                    "owner": "test",
                    "visibility": "team",
                    "title": "Convenience test",
                    "content": "Test",
                    "acl": {"users": [], "roles": [], "agents": []},
                    "version": 1,
                }
            ]
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            ov_path = Path(tmpdir) / "ov.json"
            out_path = Path(tmpdir) / "out.json"

            with open(ov_path, "w") as f:
                json.dump(ov_data, f)

            # Test bridge_from_openviking
            bridge = bridge_from_openviking(ov_path)
            reg = bridge.registry
            assert "conv_1" in reg.assets
            assert reg.assets["conv_1"].asset_type == ASSET_CHAT_MEMORY

            # Test bridge_to_openviking
            bridge_to_openviking(reg, out_path)
            with open(out_path, "r") as f:
                exported = json.load(f)
            assert len(exported["assets"]) == 1

    def test_integrate_with_veya(self):
        """Test integrate_with_veya helper."""
        ov_data = {
            "assets": [
                {
                    "id": "int_1",
                    "type": "skill",
                    "owner": "test",
                    "visibility": "team",
                    "title": "Integration test",
                    "content": "Test content",
                    "acl": {"users": [], "roles": [], "agents": []},
                    "version": 1,
                }
            ]
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            ov_path = Path(tmpdir) / "ov.json"
            with open(ov_path, "w") as f:
                json.dump(ov_data, f)
            
            registry = integrate_with_veya(ov_path)
            assert "int_1" in registry.assets
            assert registry.assets["int_1"].asset_type == ASSET_SKILL

    def test_integrate_to_openviking(self):
        """Test integrate_to_openviking helper."""
        registry = AssetRegistry()
        registry.register(MemoryAsset(
            id="int_out_1",
            asset_type=ASSET_WIKI,
            owner="test",
            visibility=VISIBILITY_TEAM,
            title="Wiki integration",
            content="Wiki content",
        ))

        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = Path(tmpdir) / "out.json"
            integrate_to_openviking(registry, out_path)
            
            with open(out_path, "r") as f:
                exported = json.load(f)
            assert len(exported["assets"]) == 1
            assert exported["assets"][0]["type"] == "wiki"

    def test_empty_assets(self):
        """Test bridge with empty assets list."""
        ov_data = {"assets": []}
        with tempfile.TemporaryDirectory() as tmpdir:
            ov_path = Path(tmpdir) / "empty.json"
            with open(ov_path, "w") as f:
                json.dump(ov_data, f)
            
            bridge = OvAssetBridge().from_openviking_v1(ov_path)
            assert len(bridge.registry.assets) == 0
            assert bridge.mapped_counts == {"chat_memory": 0, "skill": 0, "wiki": 0, "codegraph": 0}

    def test_unknown_type_maps_to_codegraph(self):
        """Test that unknown OpenViking types default to codegraph."""
        ov_data = {
            "assets": [
                {
                    "id": "unknown_1",
                    "type": "unknown_type",
                    "owner": "test",
                    "visibility": "team",
                    "title": "Unknown",
                    "content": "Content",
                    "acl": {"users": [], "roles": [], "agents": []},
                    "version": 1,
                }
            ]
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            ov_path = Path(tmpdir) / "unknown.json"
            with open(ov_path, "w") as f:
                json.dump(ov_data, f)
            
            bridge = OvAssetBridge().from_openviking_v1(ov_path)
            asset = bridge.registry.assets["unknown_1"]
            assert asset.asset_type == ASSET_CODEGRAPH

    def test_get_stats(self):
        """Test bridge statistics."""
        ov_data = {
            "assets": [
                {"id": f"mem_{i}", "type": "chat_memory", "owner": "a", "visibility": "team", "title": f"M{i}", "content": "C", "acl": {}, "version": 1}
                for i in range(3)
            ] + [
                {"id": f"skill_{i}", "type": "skill", "owner": "a", "visibility": "team", "title": f"S{i}", "content": "C", "acl": {}, "version": 1}
                for i in range(2)
            ]
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            ov_path = Path(tmpdir) / "stats.json"
            with open(ov_path, "w") as f:
                json.dump(ov_data, f)
            
            bridge = OvAssetBridge().from_openviking_v1(ov_path)
            stats = bridge.get_stats()
            
            assert stats["total_assets"] == 5
            assert stats["mapped_counts"]["chat_memory"] == 3
            assert stats["mapped_counts"]["skill"] == 2
            assert "registry_summary" in stats
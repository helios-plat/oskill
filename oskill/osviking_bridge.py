"""OpenViking <-> Veya AssetRegistry compatibility bridge.

Bridges OpenViking's viking:// protocol with Veya's AssetRegistry system,
allowing seamless interop between the two memory/context databases.

Usage:
    from oskill.osviking_bridge import OvAssetBridge
    
    # Bridge OpenViking resources into Veya registry
    bridge = OvAssetBridge()
    bridge.from_openviking_v1("/path/to/openviking/data")
    # Now assets are available via Veya's AssetRegistry
    
    # Or register Veya assets to OpenViking
    bridge.to_openviking_v1(registry)
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from oskill.memory_assets import (
    ACL,
    AssetRegistry,
    MemoryAsset,
    ASSET_CODEGRAPH,
    ASSET_CHAT_MEMORY,
    ASSET_SKILL,
    ASSET_WIKI,
    VISIBILITY_PRIVATE,
    VISIBILITY_TEAM,
    VISIBILITY_RESTRICTED,
)


@dataclass
class OvAssetBridge:
    """Bridge OpenViking assets into Veya's AssetRegistry system.
    
    Supports loading from OpenViking v1 data format (JSON-based export).
    """
    
    registry: AssetRegistry | None = None
    """Veya AssetRegistry instance to populate (creates default if None)."""
    
    mapped_counts: Dict[str, int] = field(default_factory=dict)
    """Count of assets mapped per type."""
    
    def __post_init__(self) -> None:
        if self.registry is None:
            self.registry = AssetRegistry()
    
    def from_openviking_v1(self, data_path: str | Path) -> "OvAssetBridge":
        """Load assets from OpenViking v1 export format.
        
        OpenViking v1 export format (from `ov export` or manual JSON export):
        {
            "assets": [
                {
                    "id": "memory_id",
                    "type": "chat_memory|skill|wiki|codegraph",
                    "owner": "user_id",
                    "visibility": "private|team|restricted",
                    "title": "asset title",
                    "content": "asset content",
                    "acl": {
                        "users": ["user1", "user2"],
                        "roles": ["role1"],
                        "agents": ["agent1"]
                    },
                    "version": 1
                }
            ]
        }
        """
        data_path = Path(data_path)
        if not data_path.exists():
            raise FileNotFoundError(f"OpenViking data not found: {data_path}")
        
        with open(data_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        assets = data.get("assets", [])
        mapped = {"chat_memory": 0, "skill": 0, "wiki": 0, "codegraph": 0}
        
        for av in assets:
            av_type = av.get("type", "")
            av_id = av.get("id", "")
            av_owner = av.get("owner", "")
            av_visibility = av.get("visibility", "team")
            av_title = av.get("title", "")
            av_content = av.get("content", "")
            av_acl = av.get("acl", {})
            av_version = av.get("version", 1)
            
            # Map OpenViking types to Veya types
            type_map = {
                "chat_memory": ASSET_CHAT_MEMORY,
                "skill": ASSET_SKILL,
                "wiki": ASSET_WIKI,
                "codegraph": ASSET_CODEGRAPH,
            }
            veya_type = type_map.get(av_type, ASSET_CODEGRAPH)  # default to codegraph
            
            # Map visibility
            vis_map = {
                "private": VISIBILITY_PRIVATE,
                "team": VISIBILITY_TEAM,
                "restricted": VISIBILITY_RESTRICTED,
            }
            veya_visibility = vis_map.get(av_visibility, VISIBILITY_TEAM)
            
            # Build ACL
            acl = ACL(
                users=av_acl.get("users", []),
                roles=av_acl.get("roles", []),
                agents=av_acl.get("agents", []),
            )
            
            # Create MemoryAsset
            asset = MemoryAsset(
                id=av_id,
                asset_type=veya_type,
                owner=av_owner,
                visibility=veya_visibility,
                title=av_title,
                content=av_content,
                acl=acl,
                version=av_version,
            )
            
            # Register in Veya registry
            self.registry.register(asset)
            mapped[veya_type] = mapped.get(veya_type, 0) + 1
        
        self.mapped_counts = mapped
        return self
    
    def to_openviking_v1(self, output_path: str | Path) -> "OvAssetBridge":
        """Export Veya assets to OpenViking v1 format.
        
        Writes JSON compatible with OpenViking's `ov import` format.
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        assets = []
        for asset in self.registry.assets.values():
            # Map Veya types to OpenViking types
            type_map = {
                ASSET_CHAT_MEMORY: "chat_memory",
                ASSET_SKILL: "skill",
                ASSET_WIKI: "wiki",
                ASSET_CODEGRAPH: "codegraph",
            }
            ov_type = type_map.get(asset.asset_type, "codegraph")
            
            # Map visibility
            vis_map = {
                VISIBILITY_PRIVATE: "private",
                VISIBILITY_TEAM: "team",
                VISIBILITY_RESTRICTED: "restricted",
            }
            ov_visibility = vis_map.get(asset.visibility, "team")
            
            # Build ACL
            acl = {
                "users": asset.acl.users,
                "roles": asset.acl.roles,
                "agents": asset.acl.agents,
            }
            
            assets.append({
                "id": asset.id,
                "type": ov_type,
                "owner": asset.owner,
                "visibility": ov_visibility,
                "title": asset.title,
                "content": asset.content,
                "acl": acl,
                "version": asset.version,
            })
        
        data = {"assets": assets}
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        return self
    
    def get_stats(self) -> Dict[str, Any]:
        """Get bridge statistics."""
        stats = {
            "total_assets": len(self.registry.assets),
            "mapped_counts": dict(self.mapped_counts),
            "registry_summary": self.registry.summary(),
        }
        return stats


def bridge_from_openviking(data_path: str | Path, registry: Optional[AssetRegistry] = None) -> OvAssetBridge:
    """Convenience function: load OpenViking data into Veya registry."""
    bridge = OvAssetBridge(registry=registry)
    return bridge.from_openviking_v1(data_path)


def bridge_to_openviking(assets: AssetRegistry, output_path: str | Path) -> OvAssetBridge:
    """Convenience function: export Veya assets to OpenViking format."""
    bridge = OvAssetBridge(registry=assets)
    return bridge.to_openviking_v1(output_path)


# Example usage and integration helpers
def integrate_with_veya(ov_data_path: str | Path, vua_registry: Optional[AssetRegistry] = None) -> AssetRegistry:
    """Full integration: load OpenViking assets into Veya registry.
    
    This can be called during Veya startup to pre-populate the registry
    with OpenViking's memory/context data.
    """
    bridge = OvAssetBridge(registry=vua_registry)
    bridge.from_openviking_v1(ov_data_path)
    return bridge.registry


def integrate_to_openviking(vuya_registry: AssetRegistry, ov_output_path: str | Path) -> None:
    """Convenience: export Veya registry to OpenViking format."""
    bridge = OvAssetBridge(registry=vuya_registry)
    bridge.to_openviking_v1(ov_output_path)
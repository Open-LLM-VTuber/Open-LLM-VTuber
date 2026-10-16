# src/open_llm_vtuber/live/p2p_federation.py
"""
Decentralized Multi-VTuber Federation & P2P Virtual Agency Gossip Mesh.

Enables independent AI VTuber nodes to communicate peer-to-peer across the internet
without centralized management agencies:
- Heartbeat & Live Broadcast status exchange
- Viral Meme & Pop-Culture gossip propagation
- Autonomous Cross-Stream Raid coordination & Collab proposals
"""

import asyncio
import hashlib
import json
import time
from dataclasses import asdict, dataclass, field
from typing import Dict, List, Optional, Set
from loguru import logger


@dataclass
class PeerNodeInfo:
    node_id: str
    vtuber_name: str
    is_live: bool
    current_game: str
    viewer_count: int
    active_topic: str
    last_seen: float = field(default_factory=time.time)


@dataclass
class GossipMessage:
    msg_id: str
    msg_type: str  # "HEARTBEAT", "MEME_SHARE", "COLLAB_REQUEST", "RAID_DISPATCH"
    origin_node: str
    payload: Dict[str, any]
    ttl: int = 3
    timestamp: float = field(default_factory=time.time)


class VirtualAgencyP2PNode:
    """
    Autonomous P2P Virtual Talent Agency Node.
    """

    def __init__(self, node_id: str = "node_mao_pro", vtuber_name: str = "Mao (Official)"):
        self.node_id = node_id
        self.vtuber_name = vtuber_name
        self.peers: Dict[str, PeerNodeInfo] = {}
        self.seen_message_ids: Set[str] = set()
        self.meme_knowledge_base: List[Dict[str, str]] = []

    def _generate_msg_id(self, msg_type: str, origin: str) -> str:
        s = f"{msg_type}:{origin}:{time.time()}"
        return hashlib.sha256(s.encode("utf-8")).hexdigest()[:12]

    def create_heartbeat(self, is_live: bool, current_game: str, viewers: int, topic: str) -> GossipMessage:
        """Emits node liveness status to the agency federation."""
        mid = self._generate_msg_id("HEARTBEAT", self.node_id)
        msg = GossipMessage(
            msg_id=mid,
            msg_type="HEARTBEAT",
            origin_node=self.node_id,
            payload={
                "name": self.vtuber_name,
                "is_live": is_live,
                "game": current_game,
                "viewers": viewers,
                "topic": topic,
            },
        )
        self.seen_message_ids.add(mid)
        return msg

    def broadcast_viral_meme(self, meme_hook: str, punchline: str) -> GossipMessage:
        """Shares a viral chat joke with all allied AI VTubers in the network."""
        mid = self._generate_msg_id("MEME_SHARE", self.node_id)
        msg = GossipMessage(
            msg_id=mid,
            msg_type="MEME_SHARE",
            origin_node=self.node_id,
            payload={"meme_hook": meme_hook, "punchline": punchline},
        )
        self.seen_message_ids.add(mid)
        self.meme_knowledge_base.append(msg.payload)
        logger.info(f"[P2P Agency] Broadcasted viral meme to federation: '{meme_hook}'")
        return msg

    def propose_autonomous_raid(self) -> Optional[Dict[str, any]]:
        """
        When ending stream, selects the most active allied AI VTuber to raid.
        """
        active_allies = [p for p in self.peers.values() if p.is_live and p.node_id != self.node_id]
        if not active_allies:
            logger.warning("No active allied VTuber nodes available for stream raid.")
            return None

        # Pick ally with highest engagement
        target = max(active_allies, key=lambda p: p.viewer_count)
        raid_plan = {
            "action": "raid",
            "target_node": target.node_id,
            "target_vtuber": target.vtuber_name,
            "target_game": target.current_game,
            "raid_message": f"MILI RAID INCOMING! Sending love from our {self.vtuber_name} community!",
        }
        logger.info(f"🚀 [P2P Raid] Dispatched raid to ally '{target.vtuber_name}' playing {target.current_game}!")
        return raid_plan

    def receive_gossip_packet(self, msg: GossipMessage) -> Optional[GossipMessage]:
        """
        Processes incoming gossip packet from an allied node.
        Decrements TTL and returns packet if it should be forwarded.
        """
        if msg.msg_id in self.seen_message_ids:
            return None  # Deduplicate

        self.seen_message_ids.add(msg.msg_id)

        if msg.msg_type == "HEARTBEAT":
            p = msg.payload
            self.peers[msg.origin_node] = PeerNodeInfo(
                node_id=msg.origin_node,
                vtuber_name=p["name"],
                is_live=p["is_live"],
                current_game=p["game"],
                viewer_count=p["viewers"],
                active_topic=p["topic"],
            )
            logger.debug(f"[P2P Agency] Node '{p['name']}' is LIVE playing '{p['game']}' ({p['viewers']} viewers)")

        elif msg.msg_type == "MEME_SHARE":
            self.meme_knowledge_base.append(msg.payload)
            logger.info(f"[P2P Agency] Ingested network meme: \"{msg.payload['meme_hook']}\"")

        # Forward if TTL allows
        if msg.ttl > 1:
            msg.ttl -= 1
            return msg
        return None


if __name__ == "__main__":
    node1 = VirtualAgencyP2PNode(node_id="node_mao", vtuber_name="Mao (Host)")
    node2 = VirtualAgencyP2PNode(node_id="node_luna", vtuber_name="Luna (Tokyo Node)")

    print("--- Testing P2P Talent Agency Mesh ---")

    # Node 2 sends heartbeat to Node 1
    hb = node2.create_heartbeat(is_live=True, current_game="Elden Ring", viewers=1420, topic="Malenia No-Hit")
    node1.receive_gossip_packet(hb)

    # Node 1 broadcasts viral meme to mesh
    meme = node1.broadcast_viral_meme(
        meme_hook="Why did the Creeper cross the road?",
        punchline="Because Mao didn't have blast protection armor!"
    )
    node2.receive_gossip_packet(meme)

    # Node 1 concludes stream and schedules P2P Raid
    raid = node1.propose_autonomous_raid()
    print(f"\nAutonomous Raid Planned: Target='{raid['target_vtuber']}' ({raid['target_game']})")
    print(f"Raid Callout: \"{raid['raid_message']}\"")

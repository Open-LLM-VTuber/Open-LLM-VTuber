# src/open_llm_vtuber/live/vrchat_bridge.py
"""
VRChat In-World Presence & OSC Bridge for Real-Time AI VTubers.

Enables the AI Influencer to physically inhabit a 3D avatar inside VRChat:
- Sends real-time viseme parameters (/avatar/parameters/v_*)
- Sends real-time chatbox subtitles (/chatbox/input)
- Triggers custom in-world gestures, dances, and animations (/avatar/parameters/VRCEmote)
- Implements native zero-dependency OSC (Open Sound Control 1.0) UDP packet serializer.
"""

import socket
import struct
import time
from typing import Optional, Union
from loguru import logger


def _pad4(data: bytes) -> bytes:
    """Pads byte data to a multiple of 4 bytes as required by OSC 1.0."""
    rem = len(data) % 4
    if rem > 0:
        data += b"\x00" * (4 - rem)
    return data


def build_osc_message(address: str, *args) -> bytes:
    """
    Constructs a standards-compliant OSC 1.0 packet without external dependencies.
    Supported types: float ('f'), int ('i'), str ('s'), bool ('T' / 'F').
    """
    addr_bytes = _pad4(address.encode("utf-8") + b"\x00")
    type_tags = ","
    payload = bytearray()

    for arg in args:
        if isinstance(arg, bool):
            type_tags += "T" if arg else "F"
        elif isinstance(arg, int):
            type_tags += "i"
            payload.extend(struct.pack(">i", arg))
        elif isinstance(arg, float):
            type_tags += "f"
            payload.extend(struct.pack(">f", float(arg)))
        elif isinstance(arg, str):
            type_tags += "s"
            str_bytes = _pad4(arg.encode("utf-8") + b"\x00")
            payload.extend(str_bytes)
        else:
            raise ValueError(f"Unsupported OSC argument type: {type(arg)}")

    tags_bytes = _pad4(type_tags.encode("utf-8") + b"\x00")
    return addr_bytes + tags_bytes + bytes(payload)


class VRChatBridge:
    """
    Bidirectional VRChat OSC Integration Client.
    Default VRChat OSC port: 9000 (VRChat listens here on 127.0.0.1).
    """

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 9000,
        enable_chatbox_subtitles: bool = True,
    ):
        self.host = host
        self.port = port
        self.enable_chatbox_subtitles = enable_chatbox_subtitles
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        logger.info(f"VRChat OSC Bridge initialized -> {self.host}:{self.port}")

    def send_osc(self, address: str, *args):
        """Sends an OSC message over UDP."""
        try:
            packet = build_osc_message(address, *args)
            self.sock.sendto(packet, (self.host, self.port))
        except Exception as e:
            logger.error(f"Failed to send OSC message to {address}: {e}")

    def sync_visemes(self, mouth_open: float, mouth_form: float = 0.0):
        """
        Maps normalized Live2D/audio visemes to VRChat avatar visemes.
        mouth_open: 0.0 to 1.0 (jaw opening)
        mouth_form: -1.0 (pucker/O) to 1.0 (smile/I)
        """
        open_val = max(0.0, min(1.0, float(mouth_open)))
        form_val = max(-1.0, min(1.0, float(mouth_form)))

        # Standard VRChat Viseme parameters
        # v_aa (Ah), v_oh (Oh), v_ih (Ih), v_ou (Ou)
        if form_val < -0.3:
            # Pucker / Oh sound
            self.send_osc("/avatar/parameters/v_oh", open_val * 0.8)
            self.send_osc("/avatar/parameters/v_ou", open_val * 0.5)
            self.send_osc("/avatar/parameters/v_aa", open_val * 0.2)
        elif form_val > 0.3:
            # Smile / Ee sound
            self.send_osc("/avatar/parameters/v_ih", open_val * 0.7)
            self.send_osc("/avatar/parameters/v_ee", open_val * 0.5)
            self.send_osc("/avatar/parameters/v_aa", open_val * 0.3)
        else:
            # Open Ah sound
            self.send_osc("/avatar/parameters/v_aa", open_val)
            self.send_osc("/avatar/parameters/v_sil", 1.0 - open_val)

        # Standard Jaw Flap fallback
        self.send_osc("/avatar/parameters/JawFlap", open_val)

    def display_chatbox_subtitle(self, text: str, complete: bool = True):
        """
        Displays speech subtitles directly above the avatar's head in VRChat.
        OSC Address: /chatbox/input [s, b, b] (text, direct_send, complete_sound)
        """
        if not self.enable_chatbox_subtitles or not text.strip():
            return
        # Max VRChat chatbox text length is 144 chars
        truncated = text[:140]
        self.send_osc("/chatbox/input", truncated, True, complete)
        logger.debug(f"[VRChat Chatbox] -> {truncated}")

    def trigger_emote(self, emote_id: int):
        """
        Triggers in-game animations or gestures (1 = Wave, 2 = Clap, 3 = Dance, etc.).
        """
        self.send_osc("/avatar/parameters/VRCEmote", int(emote_id))
        logger.info(f"[VRChat] Triggered In-World Emote #{emote_id}")

    def set_custom_parameter(self, param_name: str, value: Union[float, int, bool]):
        """Sets any user-defined VRChat avatar parameter."""
        addr = f"/avatar/parameters/{param_name}"
        self.send_osc(addr, value)

    def close(self):
        try:
            self.sock.close()
        except Exception:
            pass


if __name__ == "__main__":
    bridge = VRChatBridge()
    print("Testing VRChat OSC packet serialization...")

    # Test viseme sync
    bridge.sync_visemes(mouth_open=0.85, mouth_form=0.2)
    # Test chatbox subtitle
    bridge.display_chatbox_subtitle("Hello VRChat! I am an autonomous AI VTuber living in this world!", complete=True)
    # Test emote trigger
    bridge.trigger_emote(1)

    print("VRChat OSC packets sent successfully over UDP 127.0.0.1:9000.")

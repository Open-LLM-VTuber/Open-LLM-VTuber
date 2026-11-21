"""Extract legacy inline stage calls before text reaches chat or speech."""

import json


MARKER = "[local_stage:"


class StageStream:
    def __init__(self):
        self.buffer = ""
        self.arguments = []
        self.discarding = False

    def feed(self, chunk):
        self.buffer += chunk
        visible = []
        while self.buffer:
            if self.discarding:
                end = self.buffer.find("]")
                if end < 0:
                    self.buffer = ""
                    break
                self.buffer = self.buffer[end + 1 :]
                self.discarding = False
                continue
            start = self.buffer.find(MARKER)
            if start < 0:
                n = min(len(self.buffer), len(MARKER) - 1)
                while n and not MARKER.startswith(self.buffer[-n:]):
                    n -= 1
                visible.append(self.buffer[:-n] if n else self.buffer)
                self.buffer = self.buffer[-n:] if n else ""
                break
            visible.append(self.buffer[:start])
            self.buffer = self.buffer[start:]
            payload = self.buffer[len(MARKER) :].lstrip()
            try:
                arguments, end = json.JSONDecoder().raw_decode(payload)
            except ValueError:
                if len(self.buffer) > 4096:
                    self.discarding = True
                else:
                    break
                continue
            tail = payload[end:].lstrip()
            if not tail:
                break
            if tail.startswith("]"):
                if isinstance(arguments, dict):
                    self.arguments.append(arguments)
                self.buffer = tail[1:]
            else:
                self.discarding = True
        return "".join(visible)

    def finish(self):
        return "" if self.buffer.startswith(MARKER) else self.buffer

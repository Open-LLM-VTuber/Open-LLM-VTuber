import unittest
from unittest.mock import patch
from src.open_llm_vtuber import broadcast

class BroadcastTests(unittest.TestCase):
    def test_live_allowlist_and_normalized_check(self):
        with patch.object(broadcast, 'LIVE', True), patch.object(broadcast.STOP.__class__, 'exists', return_value=False), patch.object(broadcast, 'policy', return_value={'approved': {'music': ['ok.wav']}, 'blocked_phrases': ['测试禁词']}):
            self.assertTrue(broadcast.allowed('music', 'ok.wav'))
            self.assertFalse(broadcast.allowed('music', 'other.wav'))
            self.assertTrue(broadcast.blocked('测试 禁词'))
            self.assertTrue(broadcast.blocked('电话13812345678'))
            self.assertFalse(broadcast.blocked('今天一起读书'))

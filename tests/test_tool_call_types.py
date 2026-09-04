import unittest

from open_llm_vtuber.mcpp.types import ToolCallObject


class ToolCallObjectTest(unittest.TestCase):
    def test_provider_metadata_survives_message_round_trip(self):
        raw_tool_call = {
            "index": 0,
            "id": "call-1",
            "type": "function",
            "function": {"name": "search", "arguments": '{"query":"test"}'},
            "extra_content": {"google": {"thought_signature": "encrypted-signature"}},
        }

        tool_call = ToolCallObject.from_dict(raw_tool_call)

        self.assertEqual(
            tool_call.to_dict()["extra_content"], raw_tool_call["extra_content"]
        )

    def test_absent_provider_metadata_is_not_serialized(self):
        tool_call = ToolCallObject.from_dict(
            {
                "index": 0,
                "id": "call-1",
                "type": "function",
                "function": {"name": "search", "arguments": "{}"},
            }
        )

        self.assertNotIn("extra_content", tool_call.to_dict())


if __name__ == "__main__":
    unittest.main()

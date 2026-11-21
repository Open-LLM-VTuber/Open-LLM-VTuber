import asyncio
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
import json
from src.open_llm_vtuber.agent.live2d_agent import Live2DActionAgent
from src.open_llm_vtuber.agent.transformers import actions_extractor
from src.open_llm_vtuber.utils.sentence_divider import SentenceWithTags


class ActionAgentTests(unittest.TestCase):
    def test_real_model_and_invalid_tags(self):
        info = json.loads(Path('model_dict.json').read_text())[0]
        agent = Live2DActionAgent(info)
        self.assertEqual(len(agent.actions), 6)
        clean, motions = agent.extract('[action:0]你好[action:999]')
        self.assertEqual(clean, '你好')
        self.assertEqual(motions, [{'group': '', 'index': 0}])
        self.assertEqual(agent.extract('[action:-1]你好')[1], [])
        self.assertIn('未标注', agent.prompt())

    def test_disabled_and_path_escape(self):
        self.assertEqual(Live2DActionAgent({'actionAgent': {'enabled': False}}).prompt(), '')
        with TemporaryDirectory() as root:
            self.assertEqual(Live2DActionAgent({'url': '/live2d-models/../outside.json'}, Path(root)).actions, [])

    def test_stream_limits_and_clean_display(self):
        class Model:
            action_agent = Live2DActionAgent(json.loads(Path('model_dict.json').read_text())[0])
            def extract_emotion(self, text):
                return [3]
        @actions_extractor(Model())
        async def stream():
            for _ in range(6):
                yield SentenceWithTags('[action:0]你好', [])
        async def collect():
            return [item async for item in stream()]
        items = asyncio.run(collect())
        self.assertEqual(sum(bool(action.motions) for _, action in items), 2)
        self.assertTrue(all(sentence.text == '你好' for sentence, _ in items))
        self.assertTrue(all(action.expressions == [3] for _, action in items))

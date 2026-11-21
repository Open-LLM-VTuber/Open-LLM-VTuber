import json
import tempfile
import unittest
from pathlib import Path
from src.open_llm_vtuber.conversation_rag import retrieve


class ConversationRagTests(unittest.TestCase):
    def test_recall_isolation_and_deletion(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for character in ['one', 'two']:
                (root / character).mkdir()
                (root / character / 'old.json').write_text(json.dumps([
                    {'role': 'human', 'content': '我喜欢听古典音乐，尤其是钢琴', 'timestamp': '2026-01-01'}
                ]))
            result = retrieve('喜欢什么音乐', 'one', 'current', root)
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0]['role'], 'human')
            self.assertEqual(retrieve('音乐', 'one', 'old', root), [])
            self.assertEqual(retrieve('音乐', '../two', root=root), [])
            (root / 'one' / 'old.json').unlink()
            self.assertEqual(retrieve('音乐', 'one', root=root), [])

    def test_unrelated_query_does_not_recall(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory) / 'one'
            folder.mkdir()
            (folder / 'old.json').write_text('[{"role":"human","content":"古典音乐"}]')
            self.assertEqual(retrieve('天气如何', 'one', root=Path(directory)), [])

    def test_modified_history_invalidates_index(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory) / 'one'
            folder.mkdir()
            path = folder / 'old.json'
            path.write_text('[{"role":"human","content":"古典音乐"}]')
            self.assertTrue(retrieve('音乐', 'one', root=Path(directory)))
            path.write_text('[{"role":"human","content":"今天喜欢看动物纪录片"}]')
            self.assertEqual(retrieve('音乐', 'one', root=Path(directory)), [])
            self.assertTrue(retrieve('动物', 'one', root=Path(directory)))

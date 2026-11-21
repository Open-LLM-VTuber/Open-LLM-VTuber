import tempfile
import unittest
from pathlib import Path
from src.open_llm_vtuber.memory_store import MemoryStore

class MemoryStoreTests(unittest.TestCase):
    def test_versions_isolation_and_forgetting(self):
        with tempfile.TemporaryDirectory() as directory:
            store = MemoryStore(Path(directory)/'memory.db')
            self.assertEqual(store.put('one','preference','音乐','钢琴','我喜欢钢琴')['version'],1)
            self.assertEqual(store.put('one','preference','音乐','爵士','现在喜欢爵士')['version'],2)
            self.assertEqual(store.list('one')[0]['value'],'爵士')
            self.assertEqual(store.list('two'),[])
            store.forget('one','preference','音乐')
            self.assertEqual(store.list('one'),[])

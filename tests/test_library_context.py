import json
import unittest
from unittest.mock import patch
from src.open_llm_vtuber.library_context import library_context


class LibraryContextTests(unittest.TestCase):
    def test_refreshes_between_turns(self):
        with patch('src.open_llm_vtuber.bookshelf.catalog', side_effect=[['甲.txt'], ['乙.txt']]), patch('src.open_llm_vtuber.media_library.list_media', return_value={'music': [], 'videos': []}):
            self.assertIn('甲.txt', library_context(True))
            self.assertIn('乙.txt', library_context(True))

    def test_failure_is_not_empty_and_large_catalog_is_marked(self):
        with patch('src.open_llm_vtuber.bookshelf.catalog', side_effect=OSError), patch('src.open_llm_vtuber.media_library.list_media', return_value={'music': list(range(100)), 'videos': []}):
            result = json.loads(library_context().split('\n')[-1])
            self.assertIn('读取失败', result['books']['status'])
            self.assertEqual(result['music']['count'], 100)
            self.assertEqual(len(result['music']['items']), 80)
            self.assertTrue(result['music']['truncated'])

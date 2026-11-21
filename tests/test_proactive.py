import unittest
from types import SimpleNamespace
from src.open_llm_vtuber.proactive import activity_hint


class ProactiveTests(unittest.TestCase):
    def test_avoids_recent_activities_and_resets_on_character_change(self):
        context = SimpleNamespace(character_config=SimpleNamespace(conf_uid='one'), history_uid='chat')
        picked = []
        def choose(options):
            self.assertTrue(all(key not in picked[-3:] for key in options))
            picked.append(options[0])
            return options[0]
        for _ in range(12):
            activity_hint(context, choose)
        context.character_config.conf_uid = 'two'
        activity_hint(context, lambda options: options[0])
        self.assertEqual(context._proactive_recent, ['continue'])

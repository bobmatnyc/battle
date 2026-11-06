import copy
import re
import tempfile
import unittest
from pathlib import Path
from battle import engine, grid, scenario
from battle.presentation import present_view
from battle.server import Application

POC = Path(__file__).resolve().parents[1]


def _plain(html):
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', html)).strip()


class MissionTextTests(unittest.TestCase):
    def test_mission_text_states_early_summit_loss_before_deadline(self):
        # The hold-objective rule (poc-8, and poc-9 as a victory kind) ends the
        # battle when Confederates hold the summit ring uncontested for three
        # intervals, before 17:00. The text must say so.
        with tempfile.TemporaryDirectory() as directory:
            app = Application(Path(directory) / 'battle.sqlite', offline=True)
            gid, state = app.gid, app.state()
            self.assertEqual(state['rules'], 'poc-9')
            app.mutate('/api/orders', dict(game_id=gid, revision=state['revision'], orders=[
                {'unit_id': 'U1', 'destination': [11, 9], 'stance': 'move'}]))
            while (saved := app.store.load(gid))['status'] == 'active':
                app.mutate('/api/advance', dict(game_id=gid, revision=saved['revision']))
        self.assertEqual((saved['winner'], saved['turn']), ('confederate', 16))
        self.assertLess(saved['turn'], saved['max_turns'])
        self.assertIn('uncontested for 90 seconds', saved['reason'])
        hold_seconds = saved['capture'] * saved['seconds_per_turn']
        holders = [u for u in saved['units'] if u['status'] == 'ready'
                   and grid.distance(u['pos'], saved['objective']) <= 1]
        self.assertEqual({u['side'] for u in holders}, {'confederate'})

        html = (POC / 'static' / 'index.html').read_text(encoding='utf-8')
        mission = _plain(re.search(r'<div id="mission-objective".*?</div>', html, re.S).group(0))
        readme = _plain((POC / 'README.md').read_text(encoding='utf-8'))
        for text in (mission, readme):
            self.assertIn('summit hex or the six hexes around it', text)
            self.assertIn(f'{hold_seconds} seconds', text)
            self.assertIn('17:00', text)
            self.assertIn('ends at once', text)
            self.assertIn('even before 17:00', text)


class PresentationTests(unittest.TestCase):
    def test_voice_preserves_facts_receipt_times_and_canonical_state(self):
        state = scenario.create()
        engine.issue(state, 'union', {'unit_id': 'U1', 'stance': 'hold', 'destination': None})
        original = copy.deepcopy(state)
        observed = engine.view(state)
        before = copy.deepcopy(observed)
        displayed = present_view(observed)
        dispatch = displayed['dispatches'][0]
        self.assertEqual(dispatch['message_key'], 'order.hold.sent')
        self.assertEqual(dispatch['text'], before['dispatches'][0]['text'])
        self.assertEqual(dispatch['turn'], before['dispatches'][0]['turn'])
        self.assertEqual(dispatch['observed_turn'], before['dispatches'][0]['observed_turn'])
        self.assertEqual(dispatch['message_args']['unit'], 'U1')
        self.assertIn(dispatch['message_args']['seconds'] + ' seconds', dispatch['display_text'])
        self.assertEqual(displayed['contacts'], [])
        self.assertEqual(state, original)
        self.assertEqual(observed, before)

    def test_unknown_saved_prose_falls_back_without_rewriting(self):
        observation = {'dispatches': [{'text': 'An older saved dispatch.', 'turn': 4, 'observed_turn': 2}]}
        result = present_view(observation)
        self.assertEqual(result['dispatches'][0]['display_text'], 'An older saved dispatch.')
        self.assertNotIn('message_key', result['dispatches'][0])
        self.assertEqual(result['display_locale'], 'en')


if __name__ == '__main__':
    unittest.main()

import json
import unittest
from unittest.mock import MagicMock, patch
from urllib.error import URLError

from tools.simulate_pico import main


class SimulatorTests(unittest.TestCase):
    @patch('tools.simulate_pico.urlopen')
    def test_sends_structured_event_and_closes_response(self, urlopen):
        response = MagicMock()
        response.status = 200
        response.read.return_value = b'{"status":"received"}'
        urlopen.return_value.__enter__.return_value = response
        self.assertEqual(main(['--location', 'armoury', '--device-id', 'test', '--sequence', '3']), 0)
        request = urlopen.call_args.args[0]
        self.assertEqual(json.loads(request.data), {
            'device_id': 'test', 'event': 'trap_triggered', 'location': 'armoury', 'sequence': 3,
        })
        self.assertEqual(urlopen.call_args.kwargs['timeout'], 5)
        urlopen.return_value.__exit__.assert_called_once()

    @patch('tools.simulate_pico.urlopen', side_effect=URLError('offline'))
    def test_failure_exits_nonzero(self, _urlopen):
        self.assertEqual(main(['--location', 'armoury']), 1)

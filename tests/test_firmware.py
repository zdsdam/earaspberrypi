"""Host-side logic checks; run with python -m unittest discover -s tests."""
import runpy
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch


class FirmwareTests(unittest.TestCase):
    def setUp(self):
        self.now = 0
        self.wlan = Mock()
        self.wlan.isconnected.return_value = True
        self.wlan.ifconfig.return_value = ('192.168.1.2', '', '', '')
        self.http = Mock()
        self.pins = {}

        def pin(gpio, *args):
            self.pins[gpio] = Mock()
            self.pins[gpio].value.return_value = 1
            return self.pins[gpio]

        pin.IN, pin.OUT, pin.PULL_UP = 0, 1, 2
        clock = SimpleNamespace(
            ticks_ms=lambda: self.now % 65536,
            ticks_diff=lambda a, b: (a - b + 32768) % 65536 - 32768,
            sleep_ms=self.advance,
        )
        modules = {
            'machine': SimpleNamespace(Pin=pin),
            'network': SimpleNamespace(STA_IF=0, WLAN=lambda _: self.wlan),
            'urequests': self.http,
            'time': clock,
        }
        with patch.dict('sys.modules', modules):
            self.code = runpy.run_path(str(Path(__file__).resolve().parents[1] / 'main.py'))

    def advance(self, ms):
        self.now += ms

    def response(self, status):
        return SimpleNamespace(status_code=status, close=Mock())

    def test_retry_keeps_sequence_and_closes_responses(self):
        failed, success = self.response(503), self.response(200)
        self.http.post.side_effect = [failed, OSError('timeout'), success, success]
        send = self.code['send_event']
        self.assertTrue(send('blinding', 'Armoury'))
        self.assertTrue(send('blinding', 'Storage'))
        payloads = [call.kwargs['json'] for call in self.http.post.call_args_list]
        self.assertEqual([p['sequence'] for p in payloads], [1, 1, 1, 2])
        self.assertEqual(payloads[0], {
            'device_id': 'pico-w-01', 'event': 'blinding',
            'location': 'Armoury', 'sequence': 1,
        })
        failed.close.assert_called_once()
        self.assertEqual(success.close.call_count, 2)
        self.assertEqual(self.http.post.call_args.kwargs['timeout'], 5)
        self.pins['LED'].off.assert_called()

    def test_retry_limit_and_rejected_payload(self):
        self.http.post.side_effect = OSError('offline')
        self.assertFalse(self.code['send_event']('blinding', 'Armoury'))
        self.assertEqual(self.http.post.call_count, 3)
        self.http.post.reset_mock(side_effect=True)
        response = self.response(400)
        self.http.post.return_value = response
        self.assertFalse(self.code['send_event']('blinding', 'Storage'))
        self.http.post.assert_called_once()
        self.assertEqual(self.http.post.call_args.kwargs['json']['sequence'], 2)
        response.close.assert_called_once()

    def test_wifi_timeout_and_reconnect_across_tick_wrap(self):
        self.now = 65000
        self.wlan.isconnected.return_value = False
        self.assertFalse(self.code['connect_wifi']())
        self.assertEqual(self.now, 75000)
        self.wlan.isconnected.side_effect = [False, False, True]
        self.assertTrue(self.code['connect_wifi']())
        self.assertEqual(self.wlan.connect.call_count, 2)

    def test_failed_send_recovers_and_led_patterns(self):
        self.http.post.side_effect = ValueError('bad HTTP response')
        self.assertFalse(self.code['send_event']('blinding', 'Armoury'))
        self.assertEqual(self.http.post.call_count, 3)
        # Solid while sending, then three failure flashes.
        self.assertEqual(self.pins['LED'].on.call_count, 4)
        self.pins['LED'].reset_mock()
        self.http.post.side_effect = None
        response = self.response(200)
        response.close.side_effect = OSError('close failed')
        self.http.post.return_value = response
        self.assertTrue(self.code['send_event']('blinding', 'Storage'))
        self.assertEqual(self.http.post.call_args.kwargs['json']['sequence'], 2)
        self.assertEqual(self.pins['LED'].on.call_count, 2)
        self.pins['LED'].off.assert_called()

    def test_unsupported_http_timeout_returns_to_loop(self):
        self.http.post.side_effect = TypeError('unexpected keyword timeout')
        self.assertFalse(self.code['send_event']('blinding', 'Armoury'))
        self.http.post.assert_called_once()
        self.assertEqual(self.pins['LED'].on.call_count, 4)

    def test_debounce_hold_release_and_tick_wrap(self):
        button = self.code['Button'](14, 'Armoury')
        pin = self.pins[14]
        self.now = 65520
        pin.value.return_value = 0
        self.assertFalse(button.pressed())
        self.advance(20)
        pin.value.return_value = 1
        self.assertFalse(button.pressed())
        self.advance(10)
        pin.value.return_value = 0
        self.assertFalse(button.pressed())
        self.advance(49)
        self.assertFalse(button.pressed())
        self.advance(1)
        self.assertTrue(button.pressed())
        self.advance(1000)
        self.assertFalse(button.pressed())
        pin.value.return_value = 1
        self.assertFalse(button.pressed())
        self.advance(50)
        self.assertFalse(button.pressed())
        pin.value.return_value = 0
        self.assertFalse(button.pressed())
        self.advance(50)
        self.assertTrue(button.pressed())


if __name__ == '__main__':
    unittest.main()

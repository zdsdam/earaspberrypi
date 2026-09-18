import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from client import create_app


class ServerTests(unittest.TestCase):
    def setUp(self):
        self.app, self.socketio = create_app()
        self.app.config['TESTING'] = True
        self.http = self.app.test_client()
        self.socket = self.socketio.test_client(self.app)
        self.addCleanup(self.socket.disconnect)
        self.payload = {
            'device_id': 'pico-w-01', 'event': 'trap_triggered',
            'location': 'Armoury', 'sequence': 1,
        }

    def test_valid_event(self):
        before = datetime.now(timezone.utc)
        response = self.http.post('/message', json=dict(self.payload, location=' Armoury '))
        self.assertEqual(response.status_code, 200)
        payload = response.json['event']
        self.assertEqual(set(payload), set(self.payload) | {'received_at'})
        for field, value in self.payload.items():
            self.assertEqual(payload[field], value)
        received = datetime.fromisoformat(payload['received_at'])
        self.assertEqual(received.utcoffset().total_seconds(), 0)
        self.assertLessEqual(before, received)
        self.assertLessEqual(received, datetime.now(timezone.utc))
        self.assertEqual(self.socket.get_received(), [
            {'name': 'trap_triggered', 'args': [payload], 'namespace': '/'},
        ])

    def test_invalid_events(self):
        invalid = [None, [], 'text', {}]
        for field in self.payload:
            invalid.append({k: v for k, v in self.payload.items() if k != field})
        for field in ('device_id', 'event', 'location'):
            for value in ('', '  ', None, 123, []):
                invalid.append(dict(self.payload, **{field: value}))
        for value in (True, False, 0, -1, 1.5, '1', None):
            invalid.append(dict(self.payload, sequence=value))
        invalid.append(dict(self.payload, event='unknown'))
        for payload in invalid:
            with self.subTest(payload=payload):
                self.assertEqual(self.http.post('/message', json=payload).status_code, 400)
        self.assertEqual(self.http.post('/message', data='{', content_type='application/json').status_code, 400)
        self.assertEqual(self.http.post('/message', data='text').status_code, 400)
        self.assertEqual(self.socket.get_received(), [])
        # Invalid requests must not reserve the sequence number.
        self.assertEqual(self.http.post('/message', json=self.payload).json['status'], 'received')

    def test_duplicate_event(self):
        self.http.post('/message', json=self.payload)
        self.socket.get_received()
        response = self.http.post('/message', json=self.payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, {'status': 'duplicate'})
        self.assertEqual(self.socket.get_received(), [])
        for payload in (dict(self.payload, sequence=2), dict(self.payload, device_id='pico-w-02')):
            self.assertEqual(self.http.post('/message', json=payload).json['status'], 'received')
        self.assertEqual(len(self.socket.get_received()), 2)

    def test_current_firmware_alias(self):
        response = self.http.post('/message', json=dict(self.payload, event='blinding'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.socket.get_received()[0]['args'][0]['event'], 'trap_triggered')

    def test_health(self):
        response = self.http.get('/health')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, {'status': 'ok'})
        self.assertEqual(self.socket.get_received(), [])

    def test_accepted_and_duplicate_logging(self):
        with self.assertLogs('client', level='INFO') as logs:
            self.http.post('/message', json=self.payload)
            self.http.post('/message', json=self.payload)
        accepted = next(line for line in logs.output if 'Accepted event' in line)
        for value in ('device_id=pico-w-01', 'location=Armoury', 'sequence=1', 'received_at='):
            self.assertIn(value, accepted)
        self.assertTrue(any('Duplicate event' in line for line in logs.output))

    def test_emit_failure_can_be_retried(self):
        with patch.object(self.socketio, 'emit', side_effect=RuntimeError('test failure')):
            with self.assertLogs('client', level='ERROR'):
                self.assertEqual(self.http.post('/message', json=self.payload).status_code, 500)
        self.assertEqual(self.http.post('/message', json=self.payload).json['status'], 'received')
        self.assertEqual(len(self.socket.get_received()), 1)

    def test_connection_logging(self):
        with self.assertLogs('client', level='INFO') as logs:
            socket = self.socketio.test_client(self.app)
            socket.disconnect()
        self.assertTrue(any('client connected' in message for message in logs.output))
        self.assertTrue(any('client disconnected' in message for message in logs.output))


if __name__ == '__main__':
    unittest.main()

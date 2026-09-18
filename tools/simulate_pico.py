"""Send one Pico-style event using only the Python standard library."""
import argparse
import json
import sys
import uuid
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def positive_int(value):
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError('Must be a positive integer')
    return number


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--location', required=True)
    parser.add_argument('--url', default='http://127.0.0.1:5050/message')
    parser.add_argument('--device-id', default=None,
                        help='Default: unique simulator ID for this invocation')
    parser.add_argument('--sequence', type=positive_int, default=1)
    args = parser.parse_args(argv)
    payload = {
        'device_id': args.device_id or 'simulator-' + uuid.uuid4().hex,
        'event': 'trap_triggered',
        'location': args.location,
        'sequence': args.sequence,
    }
    print('Sending:', json.dumps(payload))
    request = Request(args.url, data=json.dumps(payload).encode('utf-8'),
                      headers={'Content-Type': 'application/json'}, method='POST')
    try:
        with urlopen(request, timeout=5) as response:
            print('HTTP {}: {}'.format(response.status, response.read().decode('utf-8')))
        return 0
    except HTTPError as error:
        with error:
            print('HTTP {}: {}'.format(error.code, error.read().decode('utf-8')), file=sys.stderr)
    except (URLError, OSError, ValueError) as error:
        print('Send failed: {}'.format(error), file=sys.stderr)
    return 1


if __name__ == '__main__':
    sys.exit(main())

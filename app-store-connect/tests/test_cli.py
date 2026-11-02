"""CLI transport checks with mocked Apple responses; no live credentials or requests."""
import contextlib
from email.message import Message
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch, Mock
import urllib.error
import urllib.parse

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import client
import manage


def response(payload, content_type='application/json', status=200):
    result = io.BytesIO(json.dumps(payload).encode() if isinstance(payload, dict) else payload)
    result.status = status
    result.headers = Message()
    result.headers['Content-Type'] = content_type
    return result


class CliTests(unittest.TestCase):
    def setUp(self):
        client.UPLOAD_RESERVATIONS.clear()
        client.ANALYTICS_DOWNLOADS.clear()
        for target, value in [('client.load_connection', {}), ('client.make_jwt', 'local-jwt')]:
            mock = patch(target, return_value=value)
            mock.start()
            self.addCleanup(mock.stop)
        self.opener = Mock()
        mock = patch('client.urllib.request.build_opener', return_value=self.opener)
        mock.start()
        self.addCleanup(mock.stop)

    def run_cli(self, argv):
        out, err = io.StringIO(), io.StringIO()
        with patch('manage.runtime_python', return_value=Path(sys.executable)), contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = manage.main(argv)
        return code, out.getvalue(), err.getvalue()

    def test_get_serializes_query_and_attaches_auth(self):
        self.opener.open.return_value = response({'data': []})
        code, out, _ = self.run_cli(['request', 'GET', '/v1/apps', '--query', '{"fields[apps]":["name","bundleId"],"limit":5}'])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)['status'], 200)
        request = self.opener.open.call_args.args[0]
        self.assertEqual(urllib.parse.parse_qs(urllib.parse.urlsplit(request.full_url).query), {'fields[apps]': ['name,bundleId'], 'limit': ['5']})
        self.assertEqual(request.get_header('Authorization'), 'Bearer local-jwt')

    def test_patch_body_file(self):
        payload = {'data': {'type': 'appStoreVersionLocalizations', 'id': '123', 'attributes': {'description': 'Updated'}}}
        self.opener.open.return_value = response(payload)
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'body.json'
            source.write_text(json.dumps(payload))
            code, _, _ = self.run_cli(['request', 'PATCH', '/v1/appStoreVersionLocalizations/123', '--body', '@' + str(source)])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(self.opener.open.call_args.args[0].data), payload)

    def test_invalid_json_fails_without_request(self):
        for raw in ['[]', '{broken']:
            code, _, err = self.run_cli(['request', 'POST', '/v1/apps', '--body', raw])
            self.assertEqual(code, 1)
            self.assertIn('error', json.loads(err))
        self.opener.open.assert_not_called()

    def test_body_stdin(self):
        self.opener.open.return_value = response({'data': {}})
        with patch('sys.stdin', io.StringIO('{"data":{}}')):
            code, _, _ = self.run_cli(['request', 'POST', '/v1/customerReviewResponses', '--body', '-'])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(self.opener.open.call_args.args[0].data), {'data': {}})

    def test_external_or_traversal_paths_rejected(self):
        for path in ['https://example.org/v1/apps', '//example.org/v1/apps', '/v1/../apps', '/v1/%2e%2e/apps', '/v1/apps?limit=5']:
            with self.subTest(path=path), self.assertRaises(ValueError):
                client.request('GET', path)
        self.opener.open.assert_not_called()

    def test_cancelled_write_returns_failure_without_request(self):
        with patch('client.request_approval', return_value=False):
            code, out, _ = self.run_cli(['request', 'DELETE', '/v1/betaTesters/123'])
        self.assertEqual(code, 1)
        self.assertTrue(json.loads(out)['cancelled'])
        self.opener.open.assert_not_called()

    def test_api_error_exit_and_no_retry(self):
        self.opener.open.side_effect = urllib.error.HTTPError('https://api.appstoreconnect.apple.com/v1/apps', 403, 'Forbidden', {}, io.BytesIO(b'{"errors":[{"status":"403","title":"Forbidden"}]}'))
        code, out, _ = self.run_cli(['request', 'GET', '/v1/apps'])
        self.assertEqual(code, 1)
        self.assertEqual(json.loads(out)['error']['status'], 403)
        self.opener.open.assert_called_once()

    def test_binary_download_does_not_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'report.gz'
            self.opener.open.return_value = response(b'report', 'application/gzip')
            result = client.request('GET', '/v1/salesReports', output_file=str(target))
            self.assertEqual(Path(result['file']).read_bytes(), b'report')
            self.opener.open.return_value = response(b'replacement', 'application/gzip')
            with self.assertRaises(ValueError):
                client.request('GET', '/v1/salesReports', output_file=str(target))
            self.assertEqual(target.read_bytes(), b'report')

    def test_segment_fetch_and_download_same_command(self):
        data = b'compressed report'
        signed_url = 'https://asp-test.s3.amazonaws.com/report?secret=hidden'
        self.opener.open.side_effect = [response({'data': {'type': 'analyticsReportSegments', 'id': '123', 'attributes': {'url': signed_url, 'sizeInBytes': len(data), 'checksum': hashlib.md5(data).hexdigest()}}}), response(data, 'application/gzip')]
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'segment.gz'
            code, out, err = self.run_cli(['download-segment', '123', '--output-file', str(target)])
            self.assertEqual(code, 0, err)
            self.assertEqual(target.read_bytes(), data)
            self.assertTrue(json.loads(out)['checksumVerified'])
        storage_request = self.opener.open.call_args_list[1].args[0]
        self.assertIsNone(storage_request.get_header('Authorization'))
        self.assertNotIn(signed_url, out)

    def test_upload_fetches_reservation_and_transfers(self):
        signed_url = 'https://upload.apple.com/part?hidden'
        self.opener.open.return_value = response({'data': {'type': 'appScreenshots', 'id': '123', 'attributes': {'fileName': 'image.png', 'fileSize': 3, 'uploadOperations': [{'method': 'PUT', 'url': signed_url, 'offset': 0, 'length': 3, 'requestHeaders': []}]}}})
        with tempfile.TemporaryDirectory() as directory, patch('client._upload_part') as upload:
            source = Path(directory) / 'image.png'
            source.write_bytes(b'png')
            code, out, err = self.run_cli(['upload-asset', 'appScreenshots', '123', str(source)])
            self.assertEqual(code, 0, err)
            upload.assert_called_once()
        self.assertEqual(json.loads(out)['commitPath'], '/v1/appScreenshots/123')
        self.assertNotIn(signed_url, out)


if __name__ == '__main__':
    unittest.main()

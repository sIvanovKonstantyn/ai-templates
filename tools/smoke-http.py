#!/usr/bin/env python3
"""One HTTP smoke check against the started service. Python standard library only.

Usage:
  smoke-http.py --id <task> --name "<check>" --method POST --path /api/v1/... \
      [--json '{...}' | --multipart-json '{...}' [--part request]] [--auth] \
      --expect-status 400 [--expect-body TEXT ...] [--base http://localhost:8080]

--auth adds `Authorization: Bearer <token>` from SMOKE_TOKEN, or from smoke/service-token.sh next to this tool.
The token is never printed or recorded; smoke.md shows `Bearer <redacted>`.
Prints one PASS/FAIL line and appends a check block (request, response, verification, result)
to .spec/tasks/<id>/smoke.md (or .spec/reviews/<id>/smoke.md for a review fix). Exit codes: 0 pass, 1 check failed, 2 tool or connection error.
"""
from pathlib import Path
import argparse
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
import uuid

ROOT = Path(__file__).resolve().parents[2]
EXCERPT = 400


def token():
    value = os.environ.get('SMOKE_TOKEN')
    if value:
        return value
    result = subprocess.run([str(Path(__file__).resolve().parent / 'smoke/service-token.sh')], capture_output=True, text=True)
    if result.returncode or not result.stdout.strip():
        raise RuntimeError((result.stderr.strip().splitlines() or ['token generation failed'])[-1])
    return result.stdout.strip()


def build(args):
    headers = {'Accept': 'application/json'}
    body = None
    shown = None
    if args.json is not None:
        body = args.json.encode()
        headers['Content-Type'] = 'application/json'
        shown = args.json
    elif args.multipart_json is not None:
        boundary = 'smoke-' + uuid.uuid4().hex
        body = (f'--{boundary}\r\nContent-Disposition: form-data; name="{args.part}"\r\n'
                f'Content-Type: application/json\r\n\r\n{args.multipart_json}\r\n--{boundary}--\r\n').encode()
        headers['Content-Type'] = f'multipart/form-data; boundary={boundary}'
        shown = f'multipart part `{args.part}` (application/json): {args.multipart_json}'
    recorded = dict(headers)
    if args.multipart_json is not None:
        recorded['Content-Type'] = 'multipart/form-data'
    if args.auth:
        headers['Authorization'] = 'Bearer ' + token()
        recorded['Authorization'] = 'Bearer <redacted>'
    return headers, body, recorded, shown


def call(args, headers, body):
    request = urllib.request.Request(args.base.rstrip('/') + args.path, data=body, method=args.method, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=args.timeout) as response:
            return response.status, dict(response.headers), response.read().decode(errors='replace')
    except urllib.error.HTTPError as error:
        return error.code, dict(error.headers), error.read().decode(errors='replace')


def compact(text):
    try:
        text = json.dumps(json.loads(text), separators=(',', ':'))
    except ValueError:
        text = ' '.join(text.split())
    return text if len(text) <= EXCERPT else text[:EXCERPT] + '...'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--id', required=True)
    parser.add_argument('--name', required=True)
    parser.add_argument('--method', required=True)
    parser.add_argument('--path', required=True)
    parser.add_argument('--json')
    parser.add_argument('--multipart-json')
    parser.add_argument('--part', default='request')
    parser.add_argument('--auth', action='store_true')
    parser.add_argument('--expect-status', type=int, required=True)
    parser.add_argument('--expect-body', action='append', default=[])
    parser.add_argument('--base', default=os.environ.get('SMOKE_BASE_URL', 'http://localhost:8080'))
    parser.add_argument('--timeout', type=float, default=30)
    args = parser.parse_args()
    try:
        headers, body, recorded, shown = build(args)
        status, response_headers, response_body = call(args, headers, body)
    except (RuntimeError, OSError, ValueError) as error:
        print(f'smoke-http: {error}')
        return 2
    missing = [text for text in args.expect_body if text not in response_body]
    reasons = []
    if status != args.expect_status:
        reasons.append(f'status {status}, expected {args.expect_status}')
    if missing:
        reasons.append('body is missing ' + ', '.join(f'`{m}`' for m in missing))
    passed = not reasons
    print(f'{"PASS" if passed else "FAIL"} {args.name}: {args.method} {args.path} -> {status}'
          + ('' if passed else ' reason=' + '; '.join(reasons)))
    content_type = response_headers.get('Content-Type') or response_headers.get('content-type') or 'none'
    checked = [f'status `{args.expect_status}`'] + [f'body contains `{text}`' for text in args.expect_body]
    block = [
        '',
        f'### HTTP check: {args.name}',
        f'- Request: `{args.method} {args.path}`. Headers: '
        + ', '.join(f'`{k}: {v}`' for k, v in recorded.items()) + '.'
        + (f' Body: `{shown}`' if shown else ' No body.'),
        f'- Response: status `{status}`, `Content-Type: {content_type}`. Body: `{compact(response_body) or "empty"}`',
        f'- Verification: checked {", ".join(checked)}. ' + ('All matched.' if passed else '; '.join(reasons) + '.'),
        f'- Result: {"pass" if passed else "fail"}',
    ]
    review = ROOT / '.spec/reviews' / args.id
    smoke = (review if review.is_dir() else ROOT / '.spec/tasks' / args.id) / 'smoke.md'
    smoke.parent.mkdir(parents=True, exist_ok=True)
    with smoke.open('a') as handle:
        handle.write('\n'.join(block) + '\n')
    return 0 if passed else 1


if __name__ == '__main__':
    sys.exit(main())

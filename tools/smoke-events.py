#!/usr/bin/env python3
"""Smoke checks for events published to Redis streams. Python standard library only.

Connection comes from SMOKE_REDIS_* variables, loaded from
${SPEC_SMOKE_REDIS_ENV_FILE:-$HOME/.config/spec-kit/smoke-redis.env} (mode 600).
The stream comes from --stream or SMOKE_EVENT_STREAM; there is no built-in default.
Variables already set in the environment win over the file.

Usage:
  smoke-events.py ping
  smoke-events.py mark   --id <task> [--stream S]
  smoke-events.py expect --id <task> [--stream S] --name "<check>" --where path=value ... [--absent path ...]
                         [--count N] [--timeout SECONDS]

`mark` stores the newest stream id before the HTTP call. `expect` reads records after it, prints one line
(PASS/FAIL), and appends an "Event check" block to .spec/tasks/<id>/smoke.md.
Paths: first segment is the stream field (for example `body`). JSON string fields are decoded, so
`body.changeType` and `body.changedKeys[*].key` work. `[n]` picks one element, `[*]` matches any element.
Only asserted values are printed or recorded. Other record fields and the password are never printed.
Exit codes: 0 pass, 1 check failed, 2 tool or connection error.
"""
from pathlib import Path
import argparse
import ipaddress
import json
import os
import re
import socket
import ssl
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / 'target/spec-smoke'
ENV_FILE = Path(os.environ.get('SPEC_SMOKE_REDIS_ENV_FILE', str(Path.home() / '.config/spec-kit/smoke-redis.env')))
DEFAULT_STREAM = ''
SETTLE_SECONDS = 2


class ToolError(Exception):
    pass


class RedisError(Exception):
    pass


def load_env():
    values = {}
    if ENV_FILE.is_file():
        if ENV_FILE.stat().st_mode & 0o077:
            raise ToolError(f'{ENV_FILE} must have permissions 600')
        for raw in ENV_FILE.read_text().splitlines():
            line = raw.strip()
            if not line or line.startswith('#'):
                continue
            line = line[7:] if line.startswith('export ') else line
            key, sep, value = line.partition('=')
            if sep:
                values[key.strip()] = value.strip().strip('"').strip("'")
    values.update({k: v for k, v in os.environ.items() if k.startswith('SMOKE_')})
    return values


def flag(value, default):
    return default if value in (None, '') else value.strip().lower() in ('1', 'true', 'yes', 'on')


class Redis:
    def __init__(self, env):
        self.host = env.get('SMOKE_REDIS_HOST', '')
        if not self.host:
            raise ToolError(f'SMOKE_REDIS_HOST is not set. Fill {ENV_FILE} (template: smoke/smoke-redis.env.example next to this tool)')
        self.port = int(env.get('SMOKE_REDIS_PORT') or 6379)
        self.tls = flag(env.get('SMOKE_REDIS_TLS'), True)
        self.cluster = flag(env.get('SMOKE_REDIS_CLUSTER'), True)
        self.username = env.get('SMOKE_REDIS_USERNAME') or None
        self.password = env.get('SMOKE_REDIS_PASSWORD') or None
        self.timeout = float(env.get('SMOKE_REDIS_TIMEOUT_SECONDS') or 5)
        self.connections = {}

    def connection(self, host, port):
        key = (host, port)
        if key not in self.connections:
            try:
                sock = socket.create_connection((host, port), timeout=self.timeout)
                if self.tls:
                    sock = ssl.create_default_context().wrap_socket(sock, server_hostname=self.server_name(host))
            except (OSError, ssl.SSLError) as error:
                raise ToolError(f'cannot connect to {host}:{port}: {error.__class__.__name__}: {error}') from error
            stream = sock.makefile('rwb')
            self.connections[key] = stream
            if self.password:
                self.send(stream, ['AUTH', self.username, self.password] if self.username else ['AUTH', self.password])
        return self.connections[key]

    def server_name(self, host):
        try:
            ipaddress.ip_address(host)
            return self.host
        except ValueError:
            return host

    def command(self, *args):
        host, port, asking = self.host, self.port, False
        for _ in range(6):
            stream = self.connection(host, port)
            try:
                if asking:
                    self.send(stream, ['ASKING'])
                return self.send(stream, list(args))
            except RedisError as error:
                parts = str(error).split()
                if self.cluster and parts and parts[0] in ('MOVED', 'ASK') and len(parts) == 3:
                    host, _, port_text = parts[2].rpartition(':')
                    port, asking = int(port_text), parts[0] == 'ASK'
                    continue
                raise
        raise ToolError('too many cluster redirects')

    def send(self, stream, args):
        payload = b'*%d\r\n' % len(args)
        for arg in args:
            data = str(arg).encode()
            payload += b'$%d\r\n%s\r\n' % (len(data), data)
        try:
            stream.write(payload)
            stream.flush()
            return self.read(stream)
        except (OSError, ssl.SSLError) as error:
            raise ToolError(f'connection error: {error.__class__.__name__}: {error}') from error

    def read(self, stream):
        line = stream.readline()
        if not line:
            raise ToolError('connection closed by Redis')
        kind, body = line[:1], line[1:-2].decode()
        if kind == b'+':
            return body
        if kind == b'-':
            raise RedisError(body)
        if kind == b':':
            return int(body)
        if kind == b'$':
            size = int(body)
            if size < 0:
                return None
            data = stream.read(size + 2)
            return data[:-2].decode(errors='replace')
        if kind == b'*':
            size = int(body)
            return None if size < 0 else [self.read(stream) for _ in range(size)]
        raise ToolError(f'unexpected Redis reply: {line[:40]!r}')


def records(redis, stream_name, start, count=500):
    reply = redis.command('XRANGE', stream_name, start, '+', 'COUNT', count) or []
    return [(entry[0], dict(zip(entry[1][::2], entry[1][1::2]))) for entry in reply]


def newest_id(redis, stream_name):
    reply = redis.command('XREVRANGE', stream_name, '+', '-', 'COUNT', 1) or []
    return reply[0][0] if reply else '0-0'


def id_after(record_id, cursor):
    left = tuple(int(x) for x in record_id.split('-'))
    right = tuple(int(x) for x in cursor.split('-'))
    return left > right


TOKEN = re.compile(r'([^.\[\]]+)|\[(\d+|\*)\]')


def resolve(value, path):
    """Return every value reachable through `path`. JSON strings are decoded on the way."""
    current = [value]
    for name, index in TOKEN.findall(path):
        following = []
        for item in current:
            if isinstance(item, str):
                try:
                    item = json.loads(item)
                except ValueError:
                    continue
            if name and isinstance(item, dict) and name in item:
                following.append(item[name])
            elif index == '*' and isinstance(item, list):
                following.extend(item)
            elif index and index != '*' and isinstance(item, list) and int(index) < len(item):
                following.append(item[int(index)])
        current = following
    return current


def text(value):
    if isinstance(value, bool):
        return 'true' if value else 'false'
    if value is None:
        return 'null'
    if isinstance(value, (dict, list)):
        return json.dumps(value, separators=(',', ':'), sort_keys=True)
    return str(value)


def matches(fields, where):
    return all(any(text(found) == expected for found in resolve(fields, path)) for path, expected in where)


def cursor_file(task_id, stream_name):
    return STATE / task_id / f'{re.sub(r"[^A-Za-z0-9_.-]", "_", stream_name)}.cursor'


def mark(redis, args):
    cursor = newest_id(redis, args.stream)
    target = cursor_file(args.id, args.stream)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(cursor)
    print(f'MARK stream={args.stream} cursor={cursor}')
    return 0


def expect(redis, args):
    target = cursor_file(args.id, args.stream)
    if not target.is_file():
        raise ToolError(f'no cursor for {args.stream}. Run `smoke-events.py mark --id {args.id} --stream {args.stream}` before the HTTP call')
    cursor = target.read_text().strip()
    where = [parse_pair(item) for item in args.where]
    deadline = time.monotonic() + args.timeout
    wanted = args.count or 1
    while True:
        fresh = [(rid, fields) for rid, fields in records(redis, args.stream, cursor) if id_after(rid, cursor)]
        matched = [(rid, fields) for rid, fields in fresh if matches(fields, where)]
        if len(matched) >= wanted or time.monotonic() >= deadline:
            break
        time.sleep(0.5)
    if args.count and len(matched) >= wanted:
        time.sleep(SETTLE_SECONDS)
        fresh = [(rid, fields) for rid, fields in records(redis, args.stream, cursor) if id_after(rid, cursor)]
        matched = [(rid, fields) for rid, fields in fresh if matches(fields, where)]
    present = sorted({path for _, fields in matched for path in args.absent if resolve(fields, path)})
    reasons = []
    if args.count and len(matched) != args.count:
        reasons.append(f'expected exactly {args.count} matching record(s), found {len(matched)}')
    elif not matched:
        reasons.append(f'no matching record within {args.timeout:g}s ({len(fresh)} new record(s) in stream)')
    if present:
        reasons.append('present but expected absent: ' + ', '.join(present))
    passed = not reasons
    ids = [rid for rid, _ in matched]
    asserted = [f'{path}={expected}' for path, expected in where]
    summary = f'stream={args.stream} matched={len(matched)} new={len(fresh)} ids={",".join(ids[:5]) or "-"}'
    print(f'{"PASS" if passed else "FAIL"} {args.name}: {summary}' + ('' if passed else ' reason=' + '; '.join(reasons)))
    record(args, redis, cursor, asserted, ids, len(fresh), passed, reasons)
    return 0 if passed else 1


def record(args, redis, cursor, asserted, ids, fresh, passed, reasons):
    review = ROOT / '.spec/reviews' / args.id
    smoke = (review if review.is_dir() else ROOT / '.spec/tasks' / args.id) / 'smoke.md'
    smoke.parent.mkdir(parents=True, exist_ok=True)
    filters = ', '.join(f'`{item}`' for item in asserted) or 'none'
    absent = ', '.join(f'`{path}`' for path in args.absent) or 'none'
    count = f'exactly `{args.count}`' if args.count else 'at least `1`'
    verification = 'All filters matched' + (', absent fields were absent' if args.absent else '') + f', count {count.replace("`", "")}.'
    block = [
        '',
        f'### Event check: {args.name}',
        f'- Request: `XRANGE {args.stream}` after cursor `{cursor}` on Redis `{redis.host}:{redis.port}` '
        f'(TLS {"on" if redis.tls else "off"}), waited up to {args.timeout:g}s. Filters {filters}. Absent {absent}. Count {count}.',
        f'- Response: {len(ids)} matching record(s) out of {fresh} new. Record ids: {", ".join(f"`{i}`" for i in ids[:5]) or "none"}. '
        f'Asserted values: {filters}.',
        f'- Verification: {verification if passed else "; ".join(reasons) + "."}',
        f'- Result: {"pass" if passed else "fail"}',
    ]
    with smoke.open('a') as handle:
        handle.write('\n'.join(block) + '\n')


def parse_pair(item):
    path, sep, value = item.partition('=')
    if not sep or not path:
        raise ToolError(f'--where needs path=value, got {item!r}')
    return path.strip(), value


def main():
    parser = argparse.ArgumentParser(description='Event smoke checks against Redis streams.')
    sub = parser.add_subparsers(dest='action', required=True)
    sub.add_parser('ping')
    for name in ('mark', 'expect'):
        command = sub.add_parser(name)
        command.add_argument('--id', required=True)
        command.add_argument('--stream', default=None)
    expect_parser = sub.choices['expect']
    expect_parser.add_argument('--name', required=True)
    expect_parser.add_argument('--where', action='append', default=[])
    expect_parser.add_argument('--absent', action='append', default=[])
    expect_parser.add_argument('--count', type=int, default=0)
    expect_parser.add_argument('--timeout', type=float, default=15)
    args = parser.parse_args()
    try:
        env = load_env()
        if getattr(args, 'stream', None) is None and args.action != 'ping':
            args.stream = env.get('SMOKE_EVENT_STREAM') or DEFAULT_STREAM
            if not args.stream:
                raise ToolError('no stream. Pass --stream or set SMOKE_EVENT_STREAM in the env file')
        redis = Redis(env)
        if args.action == 'ping':
            print(f'PING {redis.host}:{redis.port} {redis.command("PING")}')
            return 0
        return mark(redis, args) if args.action == 'mark' else expect(redis, args)
    except (ToolError, RedisError) as error:
        print(f'smoke-events: {error}')
        return 2


if __name__ == '__main__':
    sys.exit(main())

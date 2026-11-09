#!/usr/bin/env python3
"""Helpers for the prepare-mr skill. Python standard library only.

Usage:
  prepare-mr.py ticket
      Print the ticket from the current branch `review/<TICKET-123>`.
  prepare-mr.py target
      Print the default merge request target branch (the branch `origin/HEAD` points to).
  prepare-mr.py bump --entry "<TICKET> | <description>" [--level patch|minor|major] [--target <branch>] [--dry-run]
      Bump the project version unless it is still unreleased, and add the entry to the changelog
      under that version. Prints `version=<v> bumped=<yes|no> previous=<v> files=<changed files>`.
  prepare-mr.py link --title "<title>" --description-file <file> [--target <branch>]
      Print the GitLab "new merge request" URL for the current branch.

Project version, detected in this order:
  pom.xml       the project's own <version> (the <parent> block is ignored)
  package.json  "version" (package-lock.json is updated to match when it exists)
Changelog, the first file that exists:
  documentation/CHANGELOG.yml  `versions:` map of `  <version>:` keys with `    - <entry>` items
  documentation/CHANGELOG.md, CHANGELOG.md
                               `#`/`##` version headers with `- <entry>` items; the header level is
                               taken from the first version header in the file
  When several exist, the one that already lists the current version wins.
A version counts as released when a git tag `<version>` or `v<version>` exists, or when the target
branch already has the same version. A suffix such as `-SNAPSHOT` is kept when bumping.
Exit codes: 0 success, 2 usage or repository problem.
"""
from pathlib import Path
import argparse
import json
import re
import subprocess
import sys
import urllib.parse

ROOT = Path(__file__).resolve().parents[2]
BRANCH = re.compile(r'^review/([A-Z][A-Z0-9]+-\d+)$')
SEMVER = re.compile(r'^(\d+)\.(\d+)\.(\d+)(-[0-9A-Za-z.-]+)?$')
MD_HEADER = re.compile(r'^(#{1,6})\s+v?(\d+\.\d+\.\d+\S*)\s*$')
CHANGELOGS = ('documentation/CHANGELOG.yml', 'documentation/CHANGELOG.md', 'CHANGELOG.md')
MAX_URL = 8000


class ToolError(Exception):
    pass


def git(*args, check=True):
    result = subprocess.run(['git', *args], cwd=ROOT, capture_output=True, text=True)
    if result.returncode and check:
        raise ToolError(f'git {" ".join(args)} failed: {result.stderr.strip()}')
    return result.stdout.strip() if result.returncode == 0 else ''


def branch():
    return git('rev-parse', '--abbrev-ref', 'HEAD')


def ticket():
    name = branch()
    match = BRANCH.match(name)
    if not match:
        raise ToolError(f'branch `{name}` does not match review/<TICKET-123>')
    return match.group(1)


def default_target():
    ref = git('symbolic-ref', '--short', 'refs/remotes/origin/HEAD', check=False)
    return ref.split('/', 1)[1] if ref.startswith('origin/') else 'feature/next'


def bumped(version, level):
    match = SEMVER.match(version)
    if not match:
        raise ToolError(f'version `{version}` is not MAJOR.MINOR.PATCH[-SUFFIX]')
    major, minor, patch = (int(part) for part in match.groups()[:3])
    suffix = match.group(4) or ''
    if level == 'major':
        return f'{major + 1}.0.0{suffix}'
    if level == 'minor':
        return f'{major}.{minor + 1}.0{suffix}'
    return f'{major}.{minor}.{patch + 1}{suffix}'


class Pom:
    file = 'pom.xml'

    TAG = re.compile(r'<!--.*?-->|<\?.*?\?>|<(/?)([A-Za-z_][\w.:-]*)[^>]*?(/?)>', re.S)

    @classmethod
    def span(cls, text):
        """Return the start and end of the <version> value that is a direct child of <project>."""
        depth = 0
        for match in cls.TAG.finditer(text):
            closing, name, empty = match.group(1), match.group(2), match.group(3)
            if not name:
                continue
            if closing:
                depth -= 1
            elif empty:
                continue
            else:
                if depth == 1 and name == 'version':
                    end = text.find('</version>', match.end())
                    if end < 0:
                        break
                    return match.end(), end
                depth += 1
        raise ToolError('project version not found in pom.xml')

    def read(self, text):
        start, end = self.span(text)
        return text[start:end].strip()

    def write(self, version, dry_run):
        path = ROOT / self.file
        text = path.read_text()
        start, end = self.span(text)
        if not dry_run:
            path.write_text(text[:start] + version + text[end:])
        return [self.file]


class PackageJson:
    file = 'package.json'

    def read(self, text):
        version = json.loads(text).get('version')
        if not version:
            raise ToolError('"version" not found in package.json')
        return version

    def write(self, version, dry_run):
        changed = []
        for name in (self.file, 'package-lock.json'):
            path = ROOT / name
            if not path.is_file():
                continue
            text = path.read_text()
            data = json.loads(text)
            data['version'] = version
            if name == 'package-lock.json' and '' in data.get('packages', {}):
                data['packages']['']['version'] = version
            if not dry_run:
                path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n')
            changed.append(name)
        return changed


def project():
    for kind in (Pom(), PackageJson()):
        if (ROOT / kind.file).is_file():
            return kind
    raise ToolError('no pom.xml or package.json at the repository root')


def changelog_file(version):
    """Prefer the changelog that already lists the current version, else the first one that exists."""
    existing = [name for name in CHANGELOGS if (ROOT / name).is_file()]
    if not existing:
        raise ToolError('no changelog found: ' + ', '.join(CHANGELOGS))
    for name in existing:
        text = (ROOT / name).read_text()
        if f'  {version}:' in text.splitlines() or any(
                (m := MD_HEADER.match(line)) and m.group(2) == version for line in text.splitlines()):
            return name
    return existing[0]


def add_yaml_entry(text, version, entry):
    lines = text.splitlines()
    if not lines or lines[0].strip() != 'versions:':
        raise ToolError('CHANGELOG.yml does not start with `versions:`')
    item = f'    - {entry}'
    header = f'  {version}:'
    if header in lines:
        start = lines.index(header) + 1
        end = start
        while end < len(lines) and lines[end].startswith('    - '):
            end += 1
        if item not in lines[start:end]:
            lines.insert(end, item)
    else:
        lines[1:1] = [header, item]
    return '\n'.join(lines) + '\n'


def add_markdown_entry(text, version, entry):
    lines = text.splitlines()
    headers = [(index, MD_HEADER.match(line)) for index, line in enumerate(lines) if MD_HEADER.match(line)]
    item = f'- {entry}'
    for index, match in headers:
        if match.group(2) == version:
            end = index + 1
            while end < len(lines) and not lines[end].startswith('#') and lines[end].strip():
                end += 1
            if item not in lines[index + 1:end]:
                lines.insert(end, item)
            return '\n'.join(lines) + '\n'
    level = headers[0][1].group(1) if headers else '##'
    at = headers[0][0] if headers else len(lines)
    lines[at:at] = [f'{level} {version}', item]
    return '\n'.join(lines) + '\n'


def released(kind, version, target):
    tags = set(git('tag', '--list').splitlines())
    if version in tags or f'v{version}' in tags:
        return True
    remote = git('show', f'origin/{target}:{kind.file}', check=False)
    try:
        return bool(remote) and kind.read(remote) == version
    except (ToolError, ValueError):
        return False


def bump(args):
    if ' | ' not in args.entry:
        raise ToolError('entry must look like `<TICKET> | <description>`')
    kind = project()
    current = kind.read((ROOT / kind.file).read_text())
    bumped(current, 'patch')
    target = args.target or default_target()
    is_released = released(kind, current, target)
    version = bumped(current, args.level) if is_released else current
    log = changelog_file(current)
    log_text = (ROOT / log).read_text()
    new_log = add_yaml_entry(log_text, version, args.entry) if log.endswith('.yml') else add_markdown_entry(log_text, version, args.entry)
    changed = kind.write(version, args.dry_run) if is_released else []
    if new_log != log_text:
        if not args.dry_run:
            (ROOT / log).write_text(new_log)
        changed.append(log)
    print(f'version={version} bumped={"yes" if is_released else "no"} previous={current} '
          f'target={target} files={",".join(changed) or "-"}')


def project_url():
    remote = git('remote', 'get-url', 'origin')
    match = re.match(r'^(?:https://|git@)([^/:]+)[/:](.+?)(?:\.git)?$', remote)
    if not match:
        raise ToolError(f'cannot parse origin remote `{remote}`')
    return f'https://{match.group(1)}/{match.group(2)}'


def link(args):
    description = Path(args.description_file).read_text().strip()
    query = urllib.parse.urlencode({
        'merge_request[source_branch]': branch(),
        'merge_request[target_branch]': args.target or default_target(),
        'merge_request[title]': args.title,
        'merge_request[description]': description,
    })
    url = f'{project_url()}/-/merge_requests/new?{query}'
    if len(url) > MAX_URL:
        raise ToolError(f'URL is {len(url)} characters, over {MAX_URL}. Shorten the description.')
    print(url)


def main():
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('ticket')
    commands.add_parser('target')
    bump_parser = commands.add_parser('bump')
    bump_parser.add_argument('--entry', required=True)
    bump_parser.add_argument('--level', choices=('patch', 'minor', 'major'), default='patch')
    bump_parser.add_argument('--target', default=None)
    bump_parser.add_argument('--dry-run', action='store_true')
    link_parser = commands.add_parser('link')
    link_parser.add_argument('--title', required=True)
    link_parser.add_argument('--description-file', required=True)
    link_parser.add_argument('--target', default=None)
    args = parser.parse_args()
    try:
        if args.command == 'ticket':
            print(ticket())
        elif args.command == 'target':
            print(default_target())
        elif args.command == 'bump':
            bump(args)
        else:
            link(args)
    except (ToolError, OSError, ValueError) as error:
        print(f'prepare-mr: {error}', file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())

#!/usr/bin/env python3
"""Compact style gate for the spec kit. The project pom is not changed.

Checks:
- PMD with `pmd/ruleset.xml` next to this tool (PMD jars resolved from `style/pmd-pom.xml`).
- RedundantAnnotationDefault: an annotation attribute set to its declared default (javac API from the JDK).

Output: one line per finding, `path:line Rule message`. No output and exit 0 when clean.
Exit 1 means findings. Exit 2 means the tool itself failed.
Scope: findings on lines added or changed against the upstream merge-base, plus every line of untracked
Java files. Legacy findings on untouched lines are not reported. `--all` reports every finding.
Requires compiled classes (`target/classes`, `target/test-classes`), so run it after the Tests command.
"""
from pathlib import Path
import argparse
import os
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'target/spec-style'
TOOLS = Path(__file__).resolve().parent / 'style'
RULESET = Path(__file__).resolve().parent / 'pmd/ruleset.xml'
# Optional Maven settings file for the classpath resolution (for a private repository).
SETTINGS = os.environ.get('SPEC_MAVEN_SETTINGS', str(Path.home() / '.m2/settings.xml'))
BUILD_CLASSPATH = 'org.apache.maven.plugins:maven-dependency-plugin:3.8.1:build-classpath'


def run(command):
    return subprocess.run(command, cwd=ROOT, capture_output=True, text=True)


def fail(message):
    print(f'style-check: {message}')
    sys.exit(2)


def mvn_classpath(pom, target, scope):
    if target.is_file() and target.stat().st_mtime >= pom.stat().st_mtime:
        return target
    OUT.mkdir(parents=True, exist_ok=True)
    command = ['mvn', '-q', '-B', '-f', str(pom), BUILD_CLASSPATH,
               f'-Dmdep.includeScope={scope}', f'-Dmdep.outputFile={target}']
    if Path(SETTINGS).is_file():
        command[1:1] = ['-s', SETTINGS]
    result = run(command)
    if result.returncode or not target.is_file():
        errors = [line for line in (result.stdout + result.stderr).splitlines() if '[ERROR]' in line][:2]
        fail('cannot resolve classpath from ' + pom.relative_to(ROOT).as_posix() + ': ' + ' | '.join(errors))
    return target


def project_classpath():
    dependencies = mvn_classpath(ROOT / 'pom.xml', OUT / 'project-classpath.txt', 'test').read_text().strip()
    combined = OUT / 'aux-classpath.txt'
    combined.write_text(os.pathsep.join([str(ROOT / 'target/classes'), str(ROOT / 'target/test-classes'), dependencies]))
    return combined


def java(*args):
    home = os.environ.get('JAVA_HOME')
    result = run([str(Path(home) / 'bin/java') if home else 'java', *args])
    if result.returncode:
        tool = Path(args[2] if args[0] == '-cp' else args[0]).name
        errors = [line for line in result.stderr.splitlines() if 'error' in line.lower()][:2]
        fail(f'{tool} failed (exit {result.returncode}): ' + ' | '.join(errors or ['no stderr'])[:240])
    return [line for line in result.stdout.splitlines() if line.strip()]


def git(*args):
    result = run(['git', *args])
    return result.stdout if result.returncode == 0 else ''


def is_source(name):
    return name.endswith('.java') and name.startswith('src/') and (ROOT / name).is_file()


def changed_lines():
    """Map each changed Java file to its added lines, or None when the whole file is new."""
    base = git('merge-base', 'HEAD', '@{upstream}').strip() or 'HEAD'
    changes = {}
    current = None
    for line in git('diff', '-U0', '--no-color', '--diff-filter=ACMR', base, '--', 'src').splitlines():
        if line.startswith('+++ '):
            name = line[6:] if line.startswith('+++ b/') else None
            current = name if name and is_source(name) else None
            if current:
                changes.setdefault(current, set())
        elif current and line.startswith('@@'):
            added = line.split('+', 1)[1].split(' ', 1)[0]
            start, _, count = added.partition(',')
            changes[current].update(range(int(start), int(start) + int(count or 1)))
    for name in git('ls-files', '--others', '--exclude-standard', '--', 'src').split():
        if is_source(name):
            changes[name] = None
    return {name: lines for name, lines in changes.items() if lines is None or lines}


def in_scope(finding, scope):
    location = finding.split(' ', 1)[0]
    name, _, line = location.rpartition(':')
    if name not in scope:
        return False
    lines = scope[name]
    return lines is None or not line.isdigit() or int(line) in lines or int(line) == 0


def all_files():
    return sorted(p.relative_to(ROOT).as_posix() for d in ('src/main/java', 'src/test/java')
                  if (ROOT / d).is_dir() for p in (ROOT / d).rglob('*.java'))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--all', action='store_true', help='report every finding, not only findings on changed lines')
    args = parser.parse_args()
    scope = {name: None for name in all_files()} if args.all else changed_lines()
    files = sorted(scope)
    if not files:
        return 0
    if not (ROOT / 'target/classes').is_dir():
        fail('target/classes is missing. Run the Tests command first.')
    aux = project_classpath()
    pmd = mvn_classpath(TOOLS / 'pmd-pom.xml', OUT / 'pmd-classpath.txt', 'runtime').read_text().strip()
    paths = [str(ROOT / name) for name in files]
    findings = java('-cp', pmd, str(TOOLS / 'PmdRunner.java'), str(RULESET), str(aux), str(OUT / 'pmd.cache'), *paths)
    findings += java(str(TOOLS / 'RedundantAnnotationDefaults.java'), str(aux), *paths)
    findings = sorted({line for line in findings if in_scope(line, scope)}, key=lambda line: (line.split(' ', 1)[0].rsplit(':', 1)[0], int(line.split(' ', 1)[0].rsplit(':', 1)[1] or 0)))
    if findings:
        print('\n'.join(findings))
    return 1 if findings else 0


if __name__ == '__main__':
    sys.exit(main())

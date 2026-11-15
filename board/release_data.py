"""Read-only release guard: a code update must not silently remove tutor data.

No student database is opened. Only training identifiers, optional artifact file
names and the current systemd service are inspected. An explicit override allows
an intentional smaller/different dataset; it does not copy or alter the old one.
"""

import json
from pathlib import Path
import re
import shlex


EXCLUDED_ML = frozenset(('embeddings.json', 'features.json', 'features.jsonl'))
MAX_SERVICE_BYTES = 64 * 1024
MAX_TRAIN_BYTES = 64 * 1024 * 1024


def installed_root(service_path):
    """Return the current release Path for the known Python server unit, or None.

    Quoted deployment paths and ExecStart resets are supported. Unknown commands
    return None, allowing ``validate`` to require an explicit override rather than
    guessing that an unrelated argument is the application being launched.
    """
    service_path = Path(service_path)
    if not service_path.is_file():
        return None
    if service_path.stat().st_size > MAX_SERVICE_BYTES:
        raise ValueError('The existing tutor service unit is too large to inspect safely')
    try:
        content = service_path.read_text(encoding='utf-8')
    except (OSError, UnicodeError) as error:
        raise ValueError('Cannot read the existing tutor service unit') from error
    section = None
    commands = []
    continued = ''
    for raw in content.splitlines():
        line = continued + raw.strip()
        if line.endswith('\\'):
            continued = line[:-1] + ' '
            continue
        continued = ''
        if not line or line.startswith(('#', ';')):
            continue
        if line.startswith('[') and line.endswith(']'):
            section = line[1:-1]
            continue
        if section != 'Service' or '=' not in line:
            continue
        key, value = (part.strip() for part in line.split('=', 1))
        if key != 'ExecStart':
            continue
        if value:
            commands.append(value)
        else:
            commands.clear()
    if continued or len(commands) != 1:
        return None
    try:
        words = shlex.split(commands[0], posix=True)
    except ValueError:
        return None
    if not words or not re.fullmatch(r'python(?:3(?:\.[0-9]+)?)?', Path(words[0]).name):
        return None
    # Only accept normal interpreter flags, not -c/-m which change what is run.
    position = 1
    while position < len(words) and words[position] in ('-u', '-B', '-E', '-s', '-S', '-I'):
        position += 1
    if position >= len(words):
        return None
    script = Path(words[position])
    if not script.is_absolute() or script.name != 'server.py' or script.parent.name != 'student_app':
        return None
    if any(character in str(script) for character in ('$', '%', '\n', '\r')):
        return None
    return script.parent.parent.resolve()


def _training_keys(path):
    """Read only enough row data to compare membership, never expose row text."""
    path = Path(path)
    if not path.is_file():
        return set()
    if path.stat().st_size > MAX_TRAIN_BYTES:
        raise ValueError('Training data exceeds the release-check size limit')
    keys = set()
    try:
        with path.open(encoding='utf-8-sig') as stream:
            for number, line in enumerate(stream, 1):
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                    if not isinstance(row, dict) or not isinstance(row.get('id'), str) or not row['id']:
                        raise ValueError('invalid id')
                    language = row.get('language') or 'und'
                    if not isinstance(language, str):
                        raise ValueError('invalid language')
                    key = row['id'], language
                    if key in keys:
                        raise ValueError('duplicate key')
                    keys.add(key)
                except (ValueError, TypeError):
                    raise ValueError(f'Invalid or duplicate training identifier at row {number}; release not activated') from None
    except (OSError, UnicodeError) as error:
        raise ValueError('Cannot read training data for the release check') from error
    return keys


def _optional_artifacts(root):
    annotation = root / 'data/teaching_annotations.generated.json'
    files = [annotation] if annotation.is_file() else []
    files.extend(path for path in (root / 'data/ml').glob('*.json')
                 if path.is_file() and path.name not in EXCLUDED_ML)
    return {path.relative_to(root).as_posix() for path in files}


def validate(root, service_path, allow_data_change=False):
    """Reject missing old training rows/artifacts; return the previous root.

    ``allow_data_change=True`` permits explicit data removals and an unrecognised
    old service command. Invalid training JSON still fails validation. Call this
    before replacing the unit or restarting the application. Presence guards do
    not replace the app's validation of map/content formats and fingerprints.
    """
    root, service_path = Path(root).resolve(), Path(service_path)
    old = installed_root(service_path)
    if old is None:
        if service_path.is_file() and not allow_data_change:
            raise ValueError('Cannot identify the existing tutor release from ExecStart; inspect its data or explicitly use --allow-data-change')
        return None
    if not old.is_dir():
        if allow_data_change:
            return old
        raise ValueError('The existing tutor release directory is unavailable; cannot confirm data preservation')
    removed = _training_keys(old / 'data/train.jsonl') - _training_keys(root / 'data/train.jsonl')
    missing = sorted(name for name in _optional_artifacts(old) if not (root / name).is_file())
    if (removed or missing) and not allow_data_change:
        details = []
        if removed:
            details.append(f'{len(removed)} installed training rows would be removed')
        if missing:
            details.append('missing installed artifacts: ' + ', '.join(missing))
        raise ValueError('Release not activated: ' + '; '.join(details) +
                         '. Preserve these files/rows in the new release, or explicitly use --allow-data-change for an intentional dataset change.')
    return old

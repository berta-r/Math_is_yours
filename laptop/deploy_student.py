"""Build a bounded tutor bundle, or stage/install it on a specified UNO Q via USB.

Board model installation is deliberately separate (README steps 0-7). Builds
never contain model weights, validation data, virtualenvs, credentials or progress.
Each upload creates a new release directory; persistent student records stay put.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import shlex
import subprocess
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from laptop.usb_launcher import Adb, find_adb


EXCLUDED_ML = {'embeddings.json', 'features.jsonl'}


def forbidden(relative):
    """Paths that must never ship: credentials and model weights."""
    parts = Path(relative).parts
    return (Path(relative).name.startswith('.env') or parts[:2] == ('data', 'models'))


def bundle_files(root, with_data=False):
    root = Path(root).resolve()
    files = [root/'config.env', root/'data/sample_problems.jsonl']
    files.extend(root / name for name in ('predict.py', 'eval.py', 'build_index.py', 'docs/COMPUTE_SOLVER.md'))
    for folder in ('copilot', 'student_app'):
        files.extend(p for p in (root/folder).glob('*.py') if not p.name.startswith(('test_', 'check_')))
    files.extend((root/'student_app/assets').rglob('*'))
    files.extend((root/'knowledge').rglob('*'))
    files.extend((root/'board').glob('*.py'))
    files.extend(root / name for name in ('docs/SLM-COACH.md', 'docs/COACH-DESIGN.md', 'board/STUDENT_DEPLOYMENT.md'))
    # Similarity metadata has no raw problem text and is safe to prepare offline.
    files.append(root/'data/skill_graph.json')
    if with_data:
        files.extend(root/'data'/name for name in ('train.jsonl', 'teaching_annotations.json', 'teaching_annotations.generated.json'))
        # Laptop ML artifacts and verified large-model content (D-013), keyed to the training rows.
        # Embeddings are large and only used on the laptop; features.jsonl is not *.json.
        files.extend(p for p in (root/'data/ml').glob('*.json') if p.name not in EXCLUDED_ML)
        # The shared image folder also contains validation images. Include only
        # originals and explicitly referenced previews from loaded training rows.
        images = (root/'data/images').resolve()
        train = root/'data/train.jsonl'
        if train.is_file():
            for line in train.read_text(encoding='utf-8-sig').splitlines():
                if not line.strip():
                    continue
                problem = json.loads(line)
                stem = f"{problem['id']}_{problem.get('language') or 'und'}"
                names = [f'{stem}.png'] + [f'{stem}_option_{letter}.png' for letter in 'ABCDE'
                                         if letter in problem.get('option_images', [])]
                for name in names:
                    candidate = images/name
                    if candidate.resolve().is_relative_to(images):
                        files.append(candidate)
    result = []
    for path in sorted(set(files)):
        if not path.is_file() or path.is_symlink():
            continue
        if not path.resolve().is_relative_to(root) or path.suffix in ('.db', '.gguf', '.pyc'):
            continue
        if forbidden(path.relative_to(root)):
            continue
        if path.is_relative_to(root/'knowledge') and path.suffix not in ('.md', '.json'):
            continue
        if path.is_relative_to(root/'student_app/assets') and path.suffix not in ('.html', '.css', '.js', '.svg', '.woff2', '.txt'):
            continue
        result.append(path)
    return result


def build_bundle(root, output, with_data=False):
    root, output = Path(root).resolve(), Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    files = bundle_files(root, with_data)
    if with_data and not (root/'data/train.jsonl').is_file():
        raise ValueError('--with-data requires prepared data/train.jsonl; prepare data first or omit that flag')
    required = {'student_app/server.py', 'copilot/knowledge.py', 'knowledge/model.json', 'board/install_student_service.py'}
    names = {p.relative_to(root).as_posix() for p in files}
    if any(forbidden(name) for name in names):
        raise ValueError('Refusing to package credentials or model weights')
    if not required <= names:
        raise ValueError('Incomplete application source: ' + ', '.join(sorted(required - names)))
    manifest = {
        'format': 1,
        'runtime': 'Python standard library; existing local math-llm service for conceptual dialogue',
        'includes_progress': False,
        'ml_artifacts': sorted(name for name in names if name.startswith('data/ml/')),
        'missing_optional_artifacts': [name for name in (
            'data/ml/problem_map.json', 'data/ml/difficulty.json',
            'data/ml/thinking_steps_generated.json', 'data/ml/solutions_generated.json',
            'data/ml/slm_explanations.json') if name not in names],
        'files': {p.relative_to(root).as_posix(): {'bytes': p.stat().st_size,
                  'sha256': hashlib.sha256(p.read_bytes()).hexdigest()} for p in files},
    }
    with tarfile.open(output, 'w:gz') as archive:
        for path in files:
            archive.add(path, arcname=path.relative_to(root).as_posix(), recursive=False)
        content = json.dumps(manifest, indent=2).encode('utf-8')
        entry = tarfile.TarInfo('release-manifest.json')
        entry.size, entry.mode = len(content), 0o644
        archive.addfile(entry, io.BytesIO(content))
    metadata = {'file':str(output.resolve()), 'files':len(files), 'sha256':hashlib.sha256(output.read_bytes()).hexdigest(),
                'includes_training_data':with_data, 'includes_progress':False,
                'archive_bytes': output.stat().st_size,
                'payload_bytes': sum(item['bytes'] for item in manifest['files'].values()),
                'ml_artifacts': manifest['ml_artifacts'],
                'missing_optional_artifacts': manifest['missing_optional_artifacts']}
    if with_data:
        rows = [json.loads(line) for line in (root/'data/train.jsonl').read_text(encoding='utf-8-sig').splitlines() if line.strip()]
        missing = [p for p in rows if f"data/images/{p['id']}_{p.get('language') or 'und'}.png" not in names]
        metadata['training_rows'] = len(rows)
        metadata['missing_original_images'] = len(missing)
        metadata['missing_required_images'] = sum(p.get('text_only') is False for p in missing)
        if missing:
            metadata['warning'] = 'Some training images are absent locally. Restore them before claiming full image coverage; only available files were packaged.'
    return metadata


def deploy(args, metadata):
    if not args.serial or any(c.isspace() for c in args.serial):
        raise ValueError('Deployment requires --serial from the USB launcher devices command')
    adb = Adb(find_adb(args.adb))
    if adb.devices().get(args.serial) != 'device':
        raise ValueError('The specified USB board is not connected and ready')
    model = adb.run('-s', args.serial, 'shell', 'cat /sys/firmware/devicetree/base/model').replace('\x00', '')
    if 'unoq' not in ''.join(model.lower().split()):
        raise ValueError(f'Refusing deployment: device model is not identified as UNO Q ({model.strip()})')
    home = adb.run('-s', args.serial, 'shell', 'printenv HOME').strip()
    if not home.startswith('/home/') or any(c in home for c in ('\n', '\r')):
        raise ValueError('Unexpected board home directory')
    stamp = datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')
    release = f'{home}/math-tutor-releases/{stamp}-{metadata["sha256"][:10]}'
    adb.run('-s', args.serial, 'shell', shlex.join(['mkdir', '-p', release]))
    remote = release+'/bundle.tar.gz'
    # Data can be large: allow transfer more time than normal discovery calls.
    subprocess.run([adb.executable, '-s', args.serial, 'push', str(args.output.resolve()), remote], check=True, timeout=600)
    actual = adb.run('-s', args.serial, 'shell', shlex.join(['sha256sum', remote])).split()[0]
    if actual != metadata['sha256']:
        raise ValueError('USB bundle checksum does not match; deployment was not installed')
    subprocess.run([adb.executable, '-s', args.serial, 'shell', shlex.join(['tar', '-xzf', remote, '-C', release])],
                   check=True, timeout=600)
    command = ['python3', release+'/board/install_student_service.py']
    if args.local_tutor:
        command.append('--local-tutor')
    if getattr(args, 'safe_shutdown', False):
        command.append('--safe-shutdown')
    if getattr(args, 'allow_data_change', False):
        command.append('--allow-data-change')
    print(f'Application staged at {release}. Existing board progress was not modified.')
    print('Board installation command: ' + shlex.join(command))
    if args.install:
        # Inherit the terminal so the owner can enter sudo credentials themselves.
        subprocess.run([adb.executable, '-s', args.serial, 'shell', '-t', shlex.join(command)], check=True)
    return release


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT/'results/math-tutor-bundle.tar.gz')
    parser.add_argument('--with-data', action='store_true')
    parser.add_argument('--serial', help='Exact board serial; omit to build a local reviewable bundle only')
    parser.add_argument('--adb')
    parser.add_argument('--install', action='store_true', help='After upload, install the boot service with an interactive sudo prompt')
    parser.add_argument('--local-tutor', action='store_true', help='Use the existing math-llm service; requires board model setup first')
    parser.add_argument('--safe-shutdown', action='store_true', help='Enable the saved-session shutdown control and fixed board shutdown helper')
    parser.add_argument('--allow-data-change', action='store_true', help='Explicitly allow removing currently installed training IDs or ML artifacts during activation')
    args = parser.parse_args()
    try:
        if args.install and not args.serial:
            raise ValueError('--install requires --serial')
        metadata = build_bundle(ROOT, args.output, args.with_data)
        print(json.dumps(metadata, indent=2))
        if args.serial:
            deploy(args, metadata)
        else:
            print('Bundle prepared locally. No board or Windows startup settings were changed.')
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        parser.error(str(error))


if __name__ == '__main__':
    main()

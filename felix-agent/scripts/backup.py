#!/usr/bin/env python3
"""Back up a Felix starter's .env file."""
import argparse
import hashlib
import os
from pathlib import Path
import tempfile
import zipfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('installation', type=Path)
    parser.add_argument('--backup-root', type=Path, default=Path.home() / '.felix-agent-backups')
    args = parser.parse_args()
    root = args.installation.resolve(strict=True)
    env = root / '.env'
    if not env.is_file() or env.is_symlink():
        parser.error('A regular .env file is required')
    dest = args.backup_root.expanduser().resolve()
    if dest == root or root in dest.parents:
        parser.error('Backup directory must be outside the installation')
    dest.mkdir(parents=True, exist_ok=True, mode=0o700)
    if os.name != 'nt':
        os.chmod(dest, 0o700)
    key = hashlib.sha256(os.fsencode(str(root))).hexdigest()[:16]
    target = dest / ('felix-' + key + '.zip')
    entries = [env]
    fd, temporary = tempfile.mkstemp(prefix='.felix-', suffix='.tmp', dir=dest)
    os.close(fd)
    try:
        hashes = {}
        with zipfile.ZipFile(temporary, 'w', zipfile.ZIP_DEFLATED, allowZip64=True) as archive:
            for path in entries:
                name = path.relative_to(root).as_posix()
                archive.write(path, name)
                if path.is_file():
                    digest = hashlib.sha256()
                    with path.open('rb') as stream:
                        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                            digest.update(chunk)
                    hashes[name] = digest.digest()
        with zipfile.ZipFile(temporary) as archive:
            if archive.testzip() is not None:
                raise ValueError('Archive integrity check failed')
            for name, expected in hashes.items():
                digest = hashlib.sha256()
                with archive.open(name) as stream:
                    for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                        digest.update(chunk)
                if digest.digest() != expected:
                    raise ValueError('Archive contents do not match source: ' + name)
        os.replace(temporary, target)
        print('Verified backup:', target)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


if __name__ == '__main__':
    main()

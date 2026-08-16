from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from dataclasses import dataclass, asdict
from pathlib import Path
from urllib.parse import urlparse

from .core import index_repo, load_index, save_index


@dataclass
class RepositoryRecord:
    id: str
    name: str
    source: str
    path: str
    index_path: str
    files_indexed: int
    symbols: int


class Workspace:
    def __init__(self, root: str | Path = '.repo_assistant'):
        self.root = Path(root).expanduser().resolve()
        self.repos_dir = self.root / 'repos'
        self.indices_dir = self.root / 'indices'
        self.meta_file = self.root / 'repositories.json'
        self.repos_dir.mkdir(parents=True, exist_ok=True)
        self.indices_dir.mkdir(parents=True, exist_ok=True)

    def _load_records(self) -> dict[str, dict]:
        if not self.meta_file.exists():
            return {}
        return json.loads(self.meta_file.read_text(encoding='utf-8'))

    def _save_records(self, records: dict[str, dict]) -> None:
        self.meta_file.write_text(json.dumps(records, indent=2), encoding='utf-8')

    def list(self) -> list[dict]:
        return sorted(self._load_records().values(), key=lambda x: x['name'].lower())

    def get(self, repo_id: str) -> dict:
        records = self._load_records()
        if repo_id not in records:
            raise KeyError(f'Unknown repository id: {repo_id}')
        return records[repo_id]

    def index_local(self, path: str | Path, name: str | None = None) -> dict:
        repo_path = Path(path).expanduser().resolve()
        if not repo_path.is_dir():
            raise ValueError(f'Not a directory: {repo_path}')
        repo_id = hashlib.sha1(str(repo_path).encode()).hexdigest()[:12]
        return self._index(repo_id, name or repo_path.name, str(repo_path), repo_path)

    def clone_and_index(self, url: str, name: str | None = None) -> dict:
        parsed = urlparse(url)
        if parsed.scheme not in {'https', 'http'} or not parsed.netloc:
            raise ValueError('Only http(s) git URLs are supported')
        slug = Path(parsed.path).stem or 'repository'
        repo_id = hashlib.sha1(url.encode()).hexdigest()[:12]
        target = self.repos_dir / repo_id
        if target.exists():
            shutil.rmtree(target)
        subprocess.run(['git', 'clone', '--depth', '1', url, str(target)], check=True, capture_output=True, text=True, timeout=120)
        return self._index(repo_id, name or slug, url, target)

    def refresh(self, repo_id: str) -> dict:
        record = self.get(repo_id)
        path = Path(record['path'])
        if record['source'].startswith(('http://', 'https://')) and (path / '.git').exists():
            subprocess.run(['git', '-C', str(path), 'pull', '--ff-only'], check=True, capture_output=True, text=True, timeout=60)
        return self._index(repo_id, record['name'], record['source'], path)

    def load_repo_index(self, repo_id: str) -> dict:
        return load_index(self.get(repo_id)['index_path'])

    def _index(self, repo_id: str, name: str, source: str, path: Path) -> dict:
        index = index_repo(path)
        index_path = self.indices_dir / f'{repo_id}.json'
        save_index(index, index_path)
        record = RepositoryRecord(repo_id, name, source, str(path), str(index_path), index['files_indexed'], len(index['chunks']))
        records = self._load_records()
        records[repo_id] = asdict(record)
        self._save_records(records)
        return records[repo_id]

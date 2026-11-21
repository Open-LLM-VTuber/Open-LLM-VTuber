from pathlib import Path
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.open_llm_vtuber.media_library import init_media_routes


def test_import_catalog_duplicate_and_file(tmp_path, monkeypatch):
    monkeypatch.delenv('VTUBER_BOOKS_DIR', raising=False)
    monkeypatch.setattr('src.open_llm_vtuber.broadcast.LIVE', False)
    app = FastAPI()
    app.include_router(init_media_routes(SimpleNamespace(), tmp_path))
    with TestClient(app) as client:
        for kind, name in [('books', '书.txt'), ('images', 'photo.png'),
                           ('music', 'song.mp3'), ('videos', 'movie.mp4')]:
            response = client.post(f'/api/media/resources/{kind}', params={'filename': name}, content=b'test data')
            assert response.status_code == 200
            assert client.get(f'/api/media/resources/file/{kind}/{name}').content == b'test data'
        response = client.post('/api/media/resources/books', params={'filename': '书.txt'}, content=b'new')
        assert response.json()['path'] == '书 (1).txt'
        assert len(client.get('/api/media/resources').json()) == 5
        for name in ['../escape.txt', 'bad.exe', '']:
            assert client.post('/api/media/resources/books', params={'filename': name}, content=b'x').status_code == 400
        assert client.post('/api/media/resources/books', params={'filename': 'empty.txt'}, content=b'').status_code == 400
        outside = tmp_path.parent / 'outside.txt'
        outside.write_text('private')
        (tmp_path / 'books' / 'link.txt').symlink_to(outside)
        assert client.get('/api/media/resources/file/books/link.txt').status_code == 404
        assert not list(tmp_path.rglob('*.upload'))
        monkeypatch.setattr('src.open_llm_vtuber.broadcast.LIVE', True)
        assert client.post('/api/media/resources/books', params={'filename': 'live.txt'}, content=b'x').status_code == 403

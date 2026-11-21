"""Start the app with local Compose PostgreSQL and Redis configuration."""
import os
import runpy
import sys
from pathlib import Path
from urllib.parse import quote

root = Path(__file__).resolve().parents[1]
os.chdir(root)
# run_path does not add the target script directory to sys.path.
sys.path.insert(0, str(root))
password = next(line.split('=', 1)[1] for line in (root/'infra/.env').read_text().splitlines()
                if line.startswith('POSTGRES_PASSWORD='))
os.environ.setdefault('VTUBER_DATABASE_URL', f'postgresql://vtuber:{quote(password, safe="")}@127.0.0.1:15432/vtuber')
os.environ.setdefault('VTUBER_REDIS_URL', 'redis://127.0.0.1:16379/0')
runpy.run_path(str(root/'run_server.py'), run_name='__main__')

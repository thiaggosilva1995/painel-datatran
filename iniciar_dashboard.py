#!/usr/bin/env python3
"""Inicia o servidor local em segundo plano e verifica sua resposta HTTP."""
from pathlib import Path
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parent
URL = 'http://127.0.0.1:8000/'


def ready():
    try:
        with urllib.request.urlopen(URL, timeout=2) as response:
            return response.status == 200
    except (OSError, urllib.error.URLError):
        return False


def main():
    if ready():
        print('O dashboard já está funcionando: ' + URL)
        return 0
    python = ROOT / 'venv/bin/python'
    if not python.exists():
        print('Ambiente virtual não encontrado. Crie o venv conforme o README.')
        return 1
    with socket.socket() as sock:
        if sock.connect_ex(('127.0.0.1', 8000)) == 0:
            print('A porta 8000 está ocupada, mas o dashboard não respondeu corretamente.')
            return 1
    runtime = ROOT / '.runtime'
    runtime.mkdir(exist_ok=True)
    logfile = runtime / 'dashboard.log'
    with logfile.open('ab') as output:
        process = subprocess.Popen(
            [str(python), '-u', 'manage.py', 'runserver', '127.0.0.1:8000'],
            cwd=ROOT, stdin=subprocess.DEVNULL, stdout=output,
            stderr=subprocess.STDOUT, start_new_session=True,
        )
    (runtime / 'dashboard.pid').write_text(str(process.pid))
    for _ in range(30):
        if ready():
            print('Dashboard iniciado: ' + URL)
            print('Servidor em segundo plano. Log: ' + str(logfile))
            return 0
        if process.poll() is not None:
            print('O servidor não iniciou. Veja o log: ' + str(logfile))
            print(logfile.read_text(errors='replace')[-3000:])
            return 1
        time.sleep(1)
    print('Servidor em inicialização. Veja o log: ' + str(logfile))
    return 1


if __name__ == '__main__':
    sys.exit(main())

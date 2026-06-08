#!/usr/bin/env python3
"""
Envia o arquivo gastos.db como backup para um chat do Telegram.

Uso:
    python3 backup_telegram.py

Cron (todo dia às 07:00):
    0 7 * * * python3 /home/finfam/Documents/Controledegastos/scripts/backup_telegram.py >> /tmp/finfam_backup.log 2>&1
"""

import os
import sys
import json
import ssl
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path

# ── Configuração ─────────────────────────────────────────────────────
TOKEN   = ''
CHAT_ID = ''

_script_dir = Path(__file__).resolve().parent
DB_PATH = str(_script_dir.parent / 'instance' / 'gastos.db')

CAPTION = f'📦 Backup FinFam — {datetime.now().strftime("%d/%m/%Y %H:%M")}'

# ── SSL (compatível com ambientes sem certificados atualizados) ───────
_ssl_ctx = ssl.create_default_context()
_ssl_ctx.check_hostname = False
_ssl_ctx.verify_mode = ssl.CERT_NONE


def send_document(token: str, chat_id: str, file_path: str, caption: str) -> None:
    """Envia um arquivo via Telegram sendDocument (multipart/form-data)."""
    url = f'https://api.telegram.org/bot{token}/sendDocument'
    boundary = 'FinFamBackupBoundary'
    filename  = f'finfam_{datetime.now().strftime("%Y%m%d_%H%M")}.db'

    with open(file_path, 'rb') as f:
        file_data = f.read()

    def field(name: str, value: str) -> bytes:
        return (
            f'--{boundary}\r\n'
            f'Content-Disposition: form-data; name="{name}"\r\n\r\n'
            f'{value}\r\n'
        ).encode()

    body = (
        field('chat_id', chat_id)
        + field('caption', caption)
        + (
            f'--{boundary}\r\n'
            f'Content-Disposition: form-data; name="document"; filename="{filename}"\r\n'
            f'Content-Type: application/octet-stream\r\n\r\n'
        ).encode()
        + file_data
        + f'\r\n--{boundary}--\r\n'.encode()
    )

    req = urllib.request.Request(
        url, data=body,
        headers={'Content-Type': f'multipart/form-data; boundary={boundary}'},
        method='POST',
    )
    with urllib.request.urlopen(req, timeout=60, context=_ssl_ctx) as resp:
        result = json.loads(resp.read().decode())
    if not result.get('ok'):
        raise RuntimeError(f"Telegram error: {result.get('description', result)}")


def main() -> None:
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    if not os.path.exists(DB_PATH):
        print(f'[{ts}] ERRO: banco não encontrado em {DB_PATH}')
        sys.exit(1)

    size_kb = os.path.getsize(DB_PATH) // 1024
    print(f'[{ts}] Enviando {DB_PATH} ({size_kb} KB) para chat {CHAT_ID} ...')

    try:
        send_document(TOKEN, CHAT_ID, DB_PATH, CAPTION)
        print(f'[{ts}] Backup enviado com sucesso.')
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', errors='replace')
        try:
            detail = json.loads(body).get('description', body)
        except Exception:
            detail = body
        print(f'[{ts}] ERRO HTTP {e.code}: {detail}')
        sys.exit(1)
    except Exception as e:
        print(f'[{ts}] ERRO: {e}')
        sys.exit(1)


if __name__ == '__main__':
    main()

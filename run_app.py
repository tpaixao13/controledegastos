import socket
import threading
import time
import webbrowser


def _find_free_port(start=5000):
    for port in range(start, start + 20):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(('127.0.0.1', port)) != 0:
                return port
    return start


def _open_browser(url, delay=1.5):
    time.sleep(delay)
    webbrowser.open(url)


if __name__ == '__main__':
    from waitress import serve
    from app import create_app

    port = _find_free_port()
    url = f'http://127.0.0.1:{port}'

    app = create_app('windows')

    print(f'\n{"=" * 42}')
    print(f'  FinFam iniciado com sucesso!')
    print(f'  Acesse: {url}')
    print(f'  Feche esta janela para encerrar.')
    print(f'{"=" * 42}\n')

    threading.Thread(target=_open_browser, args=(url,), daemon=True).start()
    serve(app, host='127.0.0.1', port=port)

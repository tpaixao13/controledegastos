import os
import secrets
from dotenv import load_dotenv

load_dotenv()


class Config:
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAX_CONTENT_LENGTH = 2 * 1024 * 1024  # 2 MB
    UPLOAD_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}


class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///gastos.db'
    SECRET_KEY = os.environ.get('SECRET_KEY') or secrets.token_hex(32)


class ProductionConfig(Config):
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///gastos.db'
    SECRET_KEY = os.environ.get('SECRET_KEY', '')


# ── Windows .exe (PyInstaller) ────────────────────────────────────
_WINDOWS_DATA_DIR = os.path.join(
    os.environ.get('APPDATA', os.path.expanduser('~')), 'FinFam'
)


def _get_or_create_secret_key(data_dir: str) -> str:
    os.makedirs(data_dir, exist_ok=True)
    key_file = os.path.join(data_dir, '.secret_key')
    if os.path.exists(key_file):
        with open(key_file) as f:
            return f.read().strip()
    key = secrets.token_hex(32)
    with open(key_file, 'w') as f:
        f.write(key)
    return key


class WindowsConfig(Config):
    DEBUG = False
    SECRET_KEY = _get_or_create_secret_key(_WINDOWS_DATA_DIR)
    SQLALCHEMY_DATABASE_URI = (
        'sqlite:///'
        + os.path.join(_WINDOWS_DATA_DIR, 'gastos.db').replace('\\', '/')
    )


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'windows': WindowsConfig,
    'default': DevelopmentConfig,
}

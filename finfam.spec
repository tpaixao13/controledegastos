# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['run_app.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('app/templates', 'app/templates'),
        ('app/static',    'app/static'),
    ],
    hiddenimports=[
        # Waitress
        'waitress',
        'waitress.task',
        'waitress.server',
        'waitress.channel',
        'waitress.utilities',
        # Flask
        'flask',
        'flask.templating',
        'flask.json.provider',
        'flask_sqlalchemy',
        'flask_wtf',
        'flask_wtf.csrf',
        'flask_wtf.file',
        # WTForms
        'wtforms',
        'wtforms.validators',
        'wtforms.fields',
        'wtforms.widgets',
        # SQLAlchemy
        'sqlalchemy',
        'sqlalchemy.dialects.sqlite',
        'sqlalchemy.orm',
        'sqlalchemy.ext.declarative',
        'sqlalchemy.pool',
        # Werkzeug
        'werkzeug',
        'werkzeug.security',
        'werkzeug.routing',
        'werkzeug.serving',
        # Jinja2
        'jinja2',
        'jinja2.ext',
        # Outros
        'email_validator',
        'dotenv',
        'itsdangerous',
        'click',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'test', 'unittest'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='FinFam',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,   # janela de terminal mostra logs de startup e erros
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

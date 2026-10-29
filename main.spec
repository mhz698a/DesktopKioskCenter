# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

# 1. Definimos los recursos adicionales que PyInstaller no arrastra de forma automática
added_files = [
    ('css', 'css'),                      # Copia toda la carpeta css/ (con los QSS y SVGs)
    ('kiosks.json', '.'),                 # Archivo de configuración inicial
    ('kiosko_cert.cer', '.'),             # Certificado
    ('kiosko_cert.pfx', '.'),             # Llave privada/certificado PFX
    ('icon.png', '.')                     # Icono de la aplicación
]

a = Analysis(
    ['main.py'],                          # Archivo de entrada principal
    pathex=['.'],                         # Incluye la raíz para resolver los imports locales
    binaries=[],
    datas=added_files,                    # Inyectamos los recursos estáticos aquí
    hiddenimports=[
        'wmain',
        'database',
        'utils',
        'const',
        'api_server',
        'pollstatus',
        'action_req',
        'user_record_dialog',
        'tabs.registered_user_editor',
        'tabs.access_logs.build',
        'tabs.access_logs.backend',
        'tabs.equipment.build',
        'tabs.equipment.backend',
        'tabs.equipment.bulk_dialog',
        'tabs.equipment.bulk_dlg_add',
        'tabs.external_users.build',
        'tabs.external_users.backend',
        'tabs.internal_students.build',
        'tabs.internal_students.backend',
        'tabs.received_logins.build',
        'tabs.received_logins.backend',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tests', 'docs', '.git', '.gitignore', 'copilation.txt'], # Excluimos carpetas innecesarias para producción
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='DesktopKioskCenter',             # Nombre del .exe resultante
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,                         # IMPORTANTE: False para ocultar la ventana negra de CMD (esencial para PyQt6)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.png'                        # Icono incrustado en el propio binario executable
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='DesktopKioskCenter',             # Nombre del directorio de salida dentro de /dist
)

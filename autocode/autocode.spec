# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec file for AutoCode single-file executable.

Build: pyinstaller autocode.spec
Output: dist/autocode (Linux) or dist/autocode.exe (Windows)
"""

import sys
from pathlib import Path

block_cipher = None

# Collect all autocode source files
a = Analysis(
    ['src/autocode/__main__.py'],
    pathex=['src'],
    binaries=[],
    datas=[
        # Include tree-sitter grammars if available
    ],
    hiddenimports=[
        'autocode.cli',
        'autocode.config',
        'autocode.agent.loop',
        'autocode.agent.tools',
        'autocode.agent.identity',
        'autocode.agent.bus',
        'autocode.agent.llmloop',
        'autocode.agent.sop_runner',
        'autocode.agent.policy_router',
        'autocode.agent.cost_dashboard',
        'autocode.agent.token_tracker',
        'autocode.agent.completion',
        'autocode.agent.multi_edit',
        'autocode.agent.team',
        'autocode.agent.provider_registry',
        'autocode.eval.harness',
        'autocode.eval.context_packer',
        'autocode.external.tracker',
        'autocode.external.mcp_server',
        'autocode.external.config_merge',
        'autocode.packaging.platform_detect',
        'autocode.packaging.bootstrap',
        'autocode.packaging.installer',
        'autocode.doctor',
        'autocode.layer1',
        'autocode.layer2',
        'autocode.layer4',
        'tree_sitter',
        'tree_sitter_python',
        'typer',
        'rich',
        'pydantic',
        'yaml',
        'dotenv',
        'openai',
        'ollama',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'numpy',
        'pandas',
        'scipy',
        'sklearn',
        'torch',
        'tensorflow',
    ],
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
    name='autocode',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

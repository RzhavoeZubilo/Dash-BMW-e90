"""Общий conftest: инструменты в tools/ — плоские скрипты без __init__.py
(это намеренно: ими пользуются и как CLI, и как библиотекой через
`python3 script.py` / `from script import func`). Чтобы их можно было
импортировать в тестах без переустановки пакета, добавляем нужные каталоги
в sys.path здесь, один раз для всей сессии pytest.
"""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

for sub in ("tools/re", "tools/check_firmware"):
    p = str(REPO_ROOT / sub)
    if p not in sys.path:
        sys.path.insert(0, p)

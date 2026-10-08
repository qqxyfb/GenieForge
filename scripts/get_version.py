"""读取应用版本号（单一来源：backend/app/__init__.py 的 __version__）。

所有打包脚本都从这里读取版本，避免多处硬编码不一致。
用法: python scripts/get_version.py
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INIT = ROOT / "backend" / "app" / "__init__.py"


def get_version() -> str:
    text = INIT.read_text(encoding="utf-8")
    m = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', text)
    return m.group(1) if m else "0.0.0"


if __name__ == "__main__":
    print(get_version())

"""仓库级环境检查脚本。

本脚本只校验不涉及本地敏感信息的基础项目结构和命令依赖，
用于帮助协作者确认当前 monorepo 是否具备继续开发所需的最小前置条件。
"""

from __future__ import annotations

from pathlib import Path
import shutil


def check_path(path: Path, label: str) -> tuple[bool, str]:
    """检查仓库内必需路径是否存在。

    参数：
        path: 需要校验的绝对路径。
        label: 输出结果时展示的人类可读标签。

    返回：
        包含检查结果和格式化输出文案的元组。
    """

    exists = path.exists()
    status = "OK" if exists else "MISSING"
    return exists, f"[{status}] {label}: {path}"


def check_command(command: str) -> tuple[bool, str]:
    """检查本地 PATH 中是否存在必需命令。

    参数：
        command: 要查找的可执行命令名。

    返回：
        包含检查结果和格式化输出文案的元组。
    """

    available = shutil.which(command) is not None
    status = "OK" if available else "MISSING"
    return available, f"[{status}] command: {command}"


def main() -> int:
    """执行轻量级仓库和本地工具检查。

    返回：
        所有检查通过时返回 ``0``，否则返回 ``1``。
    """

    root = Path(__file__).resolve().parents[1]

    checks = [
        check_path(root / "backend" / "run.py", "backend entrypoint"),
        check_path(root / "backend" / ".env.example", "backend env example"),
        check_path(root / "web" / "package.json", "web package manifest"),
        check_path(root / "web" / ".env.example", "web env example"),
        check_path(root / "package.json", "workspace package manifest"),
        check_command("python"),
        check_command("pnpm"),
    ]

    failed = False

    for success, message in checks:
        print(message)
        failed = failed or not success

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

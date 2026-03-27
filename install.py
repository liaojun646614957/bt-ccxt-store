#!/usr/bin/env python3
"""
bt-ccxt-store 安装脚本（基于 pyproject.toml）
用法: python install.py
"""

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore

def run_command(cmd, check=True, quiet=False):
    """运行命令，返回 CompletedProcess"""
    if not quiet:
        print(f"执行: {' '.join(cmd)}")
    result = subprocess.run(
        cmd,
        capture_output=quiet,
        text=True,
    )
    if check and result.returncode != 0:
        if quiet and result.stderr:
            print(result.stderr.strip())
        raise subprocess.CalledProcessError(result.returncode, cmd, result.stdout, result.stderr)
    return result

def load_project_metadata(project_dir: Path):
    pyproject_path = project_dir / "pyproject.toml"
    if not pyproject_path.exists():
        print("错误: 未找到 pyproject.toml，请确认项目结构。")
        sys.exit(1)
    with pyproject_path.open("rb") as f:
        return tomllib.load(f)


def ensure_python_version(spec: str):
    """
    仅支持常见的 >=X.Y 形式，对于当前项目足够
    """
    match = re.fullmatch(r"\s*>=\s*(\d+)\.(\d+)\s*", spec)
    if not match:
        print(f"警告: 无法解析 requires-python='{spec}'，跳过版本校验。")
        return
    required_major, required_minor = map(int, match.groups())
    current = sys.version_info
    if (current.major, current.minor) < (required_major, required_minor):
        print(
            f"错误: 需要 Python >={required_major}.{required_minor}，"
            f"当前为 {current.major}.{current.minor}"
        )
        sys.exit(1)


FALLBACK_CCXT_DEPENDENCIES = [
    "certifi",
    "requests",
    "cryptography",
    "typing_extensions",
    "aiohttp",
    "aiodns",
    "yarl",
]


def install_ccxt_with_fallback(venv_pip: Path):
    """优先尝试正常安装 ccxt，必要时启用降级方案"""
    print("安装 ccxt...")
    result = run_command([str(venv_pip), "install", "ccxt"], check=False, quiet=True)
    if result.returncode == 0:
        print("ccxt 安装成功")
        return

    print("ccxt 安装失败，可能缺少 pkg-config / ninja 等系统依赖，启用降级方案。")
    if result.stderr:
        print(result.stderr.strip())
    run_command([str(venv_pip), "install", "ccxt", "--no-deps"], check=True, quiet=True)
    print("安装 ccxt 运行所需的 Python 依赖...")
    run_command([str(venv_pip), "install", *FALLBACK_CCXT_DEPENDENCIES], check=False, quiet=True)


def install_declared_dependencies(venv_pip: Path, dependencies):
    if not dependencies:
        return
    print("\n安装 pyproject.toml 中声明的依赖...")
    for dep in dependencies:
        if dep.startswith("ccxt"):
            install_ccxt_with_fallback(venv_pip)
        else:
            run_command([str(venv_pip), "install", dep], check=True, quiet=True)


def install_project_package(venv_pip: Path):
    """尝试安装项目本体，失败则退化为 --no-deps"""
    print("\n安装项目 (pip install -e .，基于 pyproject.toml)...")
    result = run_command([str(venv_pip), "install", "-e", "."], check=False, quiet=True)
    if result.returncode == 0:
        print("项目安装成功")
        return True

    print("pip install -e . 失败，尝试使用 --no-deps 重新安装。")
    if result.stderr:
        print(result.stderr.strip())
    run_command([str(venv_pip), "install", "-e", ".", "--no-deps"], check=True, quiet=True)
    return False


def install_requirements_file(venv_pip: Path, project_dir: Path):
    requirements_file = project_dir / "requirements.txt"
    if not requirements_file.exists():
        return
    print("\n安装 requirements.txt 额外依赖...")
    run_command([str(venv_pip), "install", "-r", str(requirements_file)], check=False, quiet=True)


def main():
    project_dir = Path(__file__).parent.absolute()
    os.chdir(project_dir)

    metadata = load_project_metadata(project_dir)
    project_info = metadata.get("project", {})
    requires_python = project_info.get("requires-python", ">=3.6")

    print("=" * 60)
    print(f"{project_info.get('name', 'bt-ccxt-store')} 安装脚本")
    print("=" * 60)
    print(f"项目目录: {project_dir}")
    print(f"Python版本: {sys.version}")
    print(f"要求版本: {requires_python}\n")

    ensure_python_version(requires_python)
    
    # 检查虚拟环境
    venv_dir = project_dir / "venv"
    if venv_dir.exists():
        try:
            response = input("虚拟环境已存在，是否删除并重新创建? (y/n): ").strip().lower()
            if response in ['y', 'yes']:
                print("删除旧虚拟环境...")
                shutil.rmtree(venv_dir)
            else:
                print("使用现有虚拟环境...")
        except (EOFError, KeyboardInterrupt):
            # 非交互式模式，使用现有虚拟环境
            print("使用现有虚拟环境...")
    
    # 创建虚拟环境
    if not venv_dir.exists():
        print("创建虚拟环境...")
        run_command([sys.executable, "-m", "venv", "venv"])
    
    # 确定虚拟环境中的Python和pip路径
    if sys.platform == "win32":
        venv_python = venv_dir / "Scripts" / "python.exe"
        venv_pip = venv_dir / "Scripts" / "pip.exe"
    else:
        venv_python = venv_dir / "bin" / "python"
        venv_pip = venv_dir / "bin" / "pip"
    
    # 升级pip和setuptools
    print("\n升级pip和setuptools...")
    run_command([str(venv_pip), "install", "--upgrade", "pip", "setuptools", "wheel"], check=False, quiet=True)

    installed_with_deps = install_project_package(venv_pip)

    if not installed_with_deps:
        install_declared_dependencies(venv_pip, project_info.get("dependencies", []))

    install_requirements_file(venv_pip, project_dir)
    
    # 验证安装
    print("\n验证安装...")
    test_cmd = (
        "import ccxt; import backtrader; "
        "from ccxtbt import CCXTStore; print('✓ 所有核心模块导入成功')"
    )
    result = run_command([str(venv_python), "-c", test_cmd], check=False, quiet=True)
    if result.returncode == 0:
        print("✓ 安装验证成功！")
    else:
        print("⚠ 安装验证失败，请检查错误信息")
        if result.stderr:
            print(result.stderr)
    
    print("\n" + "=" * 50)
    print("安装完成！")
    print("=" * 50)
    print("\n使用方法:")
    if sys.platform == "win32":
        print("  venv\\Scripts\\activate")
    else:
        print("  source venv/bin/activate")
    print("  cd exchanges/okx && python buy-order.py")
    print()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n安装已取消")
        sys.exit(1)
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

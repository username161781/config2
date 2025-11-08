#!/usr/bin/env python3
"""
Минимальный CLI-приложение: парсит опции командной строки, валидирует их,
и выводит все параметры в формате ключ=значение при запуске.
Обработка ошибок для всех параметров предусмотрена.
"""

import argparse
import os
import sys
from urllib.parse import urlparse

def positive_int(value):
    try:
        iv = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"Ожидалось целое число, получено: {value}")
    if iv < 0:
        raise argparse.ArgumentTypeError("Значение должно быть >= 0")
    return iv

def validate_url_or_path(value):
    # простая валидация: либо корректный URL с схемой http/https, либо существующий путь
    parsed = urlparse(value)
    if parsed.scheme in ('http', 'https'):
        return value
    if os.path.exists(value):
        return os.path.abspath(value)
    raise argparse.ArgumentTypeError("Значение должно быть корректным URL (http/https) или существующим путём к файлу/папке")

def parse_args():
    p = argparse.ArgumentParser(description="Stage 1: Minimal configurable CLI for dependency visualizer")
    p.add_argument("--package", "-p", required=True, help="Имя анализируемого пакета (например: Newtonsoft.Json или MyPackage)")
    p.add_argument("--repo", "-r", required=True, type=validate_url_or_path,
                   help="URL репозитория NuGet или путь к файлу тестового репозитория")
    p.add_argument("--mode", "-m", choices=("real", "test"), default="test",
                   help="Режим работы с тестовым репозиторием: 'real' для URL NuGet, 'test' для локального файла")
    p.add_argument("--ascii", action="store_true", help="Режим вывода зависимостей в формате ASCII-дерева")
    p.add_argument("--max-depth", type=positive_int, default=5, help="Максимальная глубина анализа зависимостей (целое >= 0)")
    p.add_argument("--filter", type=str, default="", help="Подстрока для фильтрации пакетов (не учитывать пакеты, содержащие её)")
    return p.parse_args()

def main():
    try:
        args = parse_args()
    except Exception as e:
        print(f"Ошибка аргументов: {e}", file=sys.stderr)
        sys.exit(2)

    # Покажем все параметры в формате ключ=значение
    params = {
        "package": args.package,
        "repo": args.repo,
        "mode": args.mode,
        "ascii_output": args.ascii,
        "max_depth": args.max_depth,
        "filter_substring": args.filter
    }

    print("=== Параметры запуска (ключ=значение) ===")
    for k, v in params.items():
        print(f"{k} = {v!r}")
    print("=== Конец списка параметров ===")

if __name__ == "__main__":
    main()
# python3 config2/stage1.py --package A --repo config2/repo.txt --mode test --ascii --max-depth 4 --filter SKIP
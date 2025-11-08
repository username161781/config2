#!/usr/bin/env python3
"""
stage2.py
Извлекает прямые зависимости указанного пакета.
Если mode == 'test' - читает локальный файл в формате тестового репозитория.
Если mode == 'real' - пытается использовать публичный NuGet V3 API (через urllib).
(Запуск: см. инструкции ниже)
"""

import argparse
import json
import sys
import os
import ssl
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from urllib.parse import urljoin, urlparse

def positive_int(value):
    try:
        return int(value)
    except ValueError:
        raise argparse.ArgumentTypeError("Ожидалось целое число")

def validate_url_or_path(value):
    parsed = urlparse(value)
    if parsed.scheme in ('http', 'https'):
        return value
    if os.path.exists(value):
        return os.path.abspath(value)
    raise argparse.ArgumentTypeError("Должен быть URL (http/https) или существующий путь к файлу")

def parse_args():
    p = argparse.ArgumentParser(description="Stage 2: Extract direct dependencies (NuGet or test file).")
    p.add_argument("--package", "-p", required=True)
    p.add_argument("--repo", "-r", required=True, type=validate_url_or_path)
    p.add_argument("--mode", "-m", choices=("real","test"), default="test")
    p.add_argument("--insecure", action="store_true", help="Отключить проверку SSL сертификатов (для тестирования)")
    return p.parse_args()

def read_test_repo(path):
    """
    Формат тестового файла: каждая строка:
    PACKAGENAME: DEP1 DEP2 DEP3
    Пример:
    A: B C
    B: D
    C:
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"Тестовый файл не найден: {path}")
    deps = {}
    with open(path, "r", encoding="utf-8") as f:
        ln = 0
        for raw in f:
            ln += 1
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if ":" not in line:
                raise ValueError(f"Неверный формат в строке {ln}: '{line}' (ожидается ':')")
            left, right = line.split(":", 1)
            pkg = left.strip()
            # допустим имена пакетов — большие латинские буквы/строки
            dep_list = [x for x in (right.strip().split()) if x]
            deps[pkg] = dep_list
    return deps

def get_nuget_direct_dependencies(package_name, repo_url, insecure=False):
    """
    Попытка получить информацию о зависимостях через NuGet V3 API.
    """
    # Создаем контекст SSL (для игнорирования ошибок сертификатов в тестовом режиме)
    ssl_context = None
    if insecure:
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

    try:
        index_url = repo_url
        if not repo_url.endswith("index.json"):
            if repo_url.endswith("/"):
                index_url = urljoin(repo_url, "index.json")
            else:
                index_url = urljoin(repo_url + "/", "index.json")
        print(f"Попытка получить service index: {index_url}")
        req = Request(index_url, headers={"User-Agent":"dep-vis/1.0"})

        if insecure:
            with urlopen(req, timeout=10, context=ssl_context) as res:
                index = json.load(res)
        else:
            with urlopen(req, timeout=10) as res:
                index = json.load(res)

    except Exception as e:
        raise RuntimeError(f"Не удалось получить service index: {e}")

    # ищем registrations endpoint
    reg_url = None
    for r in index.get("resources", []):
        if r.get("@type","").startswith("RegistrationsBaseUrl"):
            reg_url = r.get("@id")
            break
    if not reg_url:
        raise RuntimeError("Не найден endpoint RegistrationsBaseUrl в service index")

    # регистрация пакета: регистрация обычно по нижнему регистру имени
    pkg_lower = package_name.lower()
    registration_index = urljoin(reg_url if reg_url.endswith("/") else reg_url + "/", pkg_lower + "/index.json")

    try:
        req = Request(registration_index, headers={"User-Agent":"dep-vis/1.0"})

        if insecure:
            with urlopen(req, timeout=10, context=ssl_context) as res:
                reg = json.load(res)
        else:
            with urlopen(req, timeout=10) as res:
                reg = json.load(res)

    except HTTPError as e:
        if e.code == 404:
            raise RuntimeError(f"Пакет {package_name} не найден в репозитории ({registration_index}).")
        else:
            raise RuntimeError(f"HTTP ошибка при получении {registration_index}: {e}")
    except URLError as e:
        raise RuntimeError(f"Ошибка сети при получении {registration_index}: {e}")

    # возьмём самый последний item -> последняя версия
    items = reg.get("items", [])
    if not items:
        return []

    # items могут содержать страницы; берем последнюю запись последней страницы
    last_item = items[-1]

    # если в last_item есть вложенные items, берём последний элемент
    if "items" in last_item and last_item["items"]:
        last_entry = last_item["items"][-1]
    else:
        last_entry = last_item

    # metadata может быть разной вложенности
    metadata = last_entry.get("catalogEntry") or last_entry.get("data") or last_entry

    # dependencies находятся в metadata.get("dependencyGroups")
    deps = []
    for group in metadata.get("dependencyGroups", []) or []:
        for d in group.get("dependencies", []) or []:
            # d может иметь id и range
            dep_id = d.get("id") or d.get("name")
            if dep_id:
                deps.append(dep_id)

    return deps

def main():
    args = parse_args()
    try:
        if args.mode == "test":
            deps_map = read_test_repo(args.repo)
            direct = deps_map.get(args.package, [])
            print(f"Прямые зависимости пакета {args.package!r} (из тестового файла {args.repo}):")
            if direct:
                for d in direct:
                    print(" -", d)
            else:
                print(" (нет прямых зависимостей или пакет не найден)")
        else:
            # режим real: repo — должен быть URL до NuGet service index (index.json)
            deps = get_nuget_direct_dependencies(args.package, args.repo, args.insecure)
            print(f"Прямые зависимости пакета {args.package!r} (из NuGet репозитория {args.repo}):")
            if deps:
                for d in deps:
                    print(" -", d)
            else:
                print(" (нет прямых зависимостей или не удалось извлечь)")
    except Exception as e:
        print("Ошибка при извлечении зависимостей:", e, file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
# python3 config2/stage2.py --package Newtonsoft.Json --repo https://api.nuget.org/v3/index.json --mode real --insecure

#python3 config2/stage2.py --package A --repo config2/repo.txt --mode test
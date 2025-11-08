"""
Построение полного графа зависимостей (транзитивного) с использованием BFS,
реализованного рекурсивно. Обрабатывает максимальную глубину, фильтрацию по подстроке,
циклические зависимости и режим тестового репозитория.
"""

import argparse
import sys
import os
from collections import deque, defaultdict

# переиспользуем парсер для путей/входных данных
def validate_path(value):
    if os.path.exists(value):
        return os.path.abspath(value)
    raise argparse.ArgumentTypeError("Укажите существующий путь к тестовому файлу")

def parse_args():
    p = argparse.ArgumentParser(description="Stage 3: Build dependency graph (BFS with recursion)")
    p.add_argument("--package", "-p", required=True)
    p.add_argument("--repo", "-r", required=True, type=validate_path, help="Путь к тестовому файлу репозитория")
    p.add_argument("--mode", "-m", choices=("test",), default="test")
    p.add_argument("--max-depth", "-d", type=int, default=5)
    p.add_argument("--filter", "-f", default="", help="Не учитывать пакеты, содержащие эту подстроку")
    return p.parse_args()

def read_test_repo(path):
    deps = {}
    with open(path, "r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            left, right = line.split(":", 1)
            pkg = left.strip()
            dep_list = [x for x in (right.strip().split()) if x]
            deps[pkg] = dep_list
    return deps

# Реализуем BFS с рекурсией: рекурсивно обрабатываем очереди уровней.
def recursive_bfs_levels(start, get_neighbors, max_depth, exclude_substr):
    """
    Возвращает dict: node -> set(neighbors)
    Реализация: проход по уровням; рекурсивная функция обрабатывает текущий уровень.
    Защита от циклов: visited set.
    """
    graph = defaultdict(set)
    visited = set([start])

    def process_level(current_level_nodes, depth):
        if not current_level_nodes:
            return
        if depth >= max_depth:
            return
        next_level = set()
        for node in current_level_nodes:
            try:
                neighbors = get_neighbors(node)
            except Exception as e:
                print(f"Ошибка при получении соседей для {node}: {e}", file=sys.stderr)
                neighbors = []
            for nb in neighbors:
                if exclude_substr and exclude_substr in nb:
                    continue
                graph[node].add(nb)
                if nb not in visited:
                    visited.add(nb)
                    next_level.add(nb)
        # рекурсивный вызов для следующего уровня
        process_level(next_level, depth+1)

    process_level({start}, 0)
    return graph

def main():
    args = parse_args()
    if args.mode != "test":
        print("Этот этап поддерживает только 'test' режим (локальный файл).", file=sys.stderr)
        sys.exit(2)
    repo = read_test_repo(args.repo)
    if args.package not in repo:
        print(f"В тестовом репозитории пакет {args.package!r} не найден. Попытка продолжить (буд построен граф от узла даже если нет записей).")
    def neigh(x):
        return repo.get(x, [])

    graph = recursive_bfs_levels(args.package, neigh, args.max_depth, args.filter)
    # Выведем граф в читаемом виде
    print("Построенный граф зависимостей (node -> [neighbors]):")
    if not graph:
        print(" (пусто)")
    else:
        for k in sorted(graph.keys()):
            print(f"{k} -> {sorted(graph[k])}")

if __name__ == "__main__":
    main()

# python3 config2/stage3.py --package A --repo config2/repo.txt --max-depth 5 --filter SKIP
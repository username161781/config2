#!/usr/bin/env python3
"""
stage4.py
Поддерживает вывод обратных зависимостей для заданного пакета.
Использует тот же файл тестового репозитория (формат см. test_repo.txt).
Алгоритм: строим полный граф (как в stage3), затем инвертируем и делаем поиск,
кто достигает целевого узла (т.е. все пакеты, которые транзитивно зависят от target).
"""

import argparse
import sys
import os
from collections import defaultdict, deque

def validate_path(value):
    if os.path.exists(value):
        return os.path.abspath(value)
    raise argparse.ArgumentTypeError("Укажите существующий путь к тестовому файлу")

def parse_args():
    p = argparse.ArgumentParser(description="Stage 4: Reverse dependencies (who depends on given package)")
    p.add_argument("--package", "-p", required=True, help="Целевой пакет (например: B)")
    p.add_argument("--repo", "-r", required=True, type=validate_path, help="Путь к тестовому файлу репозитория")
    p.add_argument("--max-depth", "-d", type=int, default=10, help="Максимальная глубина поиска")
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

def build_full_graph(repo_map, start_nodes=None, max_depth=10, exclude_substr=""):
    """
    Построим транзитивный граф для всех узлов встречающихся в repo_map (упрощённо).
    Для небольших тестовых репозиториев этого достаточно.
    """
    graph = defaultdict(set)
    # простой BFS без рекурсии здесь — достаточно
    for start in repo_map.keys():
        visited = set([start])
        q = deque([(start, 0)])
        while q:
            node, depth = q.popleft()
            if depth >= max_depth:
                continue
            for nb in repo_map.get(node, []):
                if exclude_substr and exclude_substr in nb:
                    continue
                graph[start].add(nb)
                if nb not in visited:
                    visited.add(nb)
                    q.append((nb, depth+1))
    return graph

def invert_graph(graph):
    inv = defaultdict(set)
    for a, neighs in graph.items():
        for b in neighs:
            inv[b].add(a)
    return inv

def transitive_predecessors(inv_graph, target, max_depth=10):
    # найдем все узлы, которые могут достичь target (транзитивно), с ограничением глубины.
    result = set()
    q = deque([(target, 0)])
    visited = set([target])
    while q:
        node, depth = q.popleft()
        if depth >= max_depth:
            continue
        for pred in inv_graph.get(node, []):
            if pred not in visited:
                visited.add(pred)
                result.add(pred)
                q.append((pred, depth+1))
    return result

def main():
    args = parse_args()
    repo_map = read_test_repo(args.repo)
    graph = build_full_graph(repo_map, max_depth=args.max_depth, exclude_substr=args.filter)
    inv = invert_graph(graph)
    preds = transitive_predecessors(inv, args.package, max_depth=args.max_depth)
    print(f"Обратные зависимости (пакеты, которые зависят от {args.package!r}):")
    if not preds:
        print(" (не найдено)")
    else:
        for p in sorted(preds):
            print(" -", p)

if __name__ == "__main__":
    main()
#  python3 config2/stage4.py --package A --repo config2/repo.txt --max-depth 10
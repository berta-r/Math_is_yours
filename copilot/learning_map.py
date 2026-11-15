"""Problem map: precomputed 2-D layout, kNN graph and stepping-stone paths.

Loads data/ml/problem_map.json exported by laptop/ml/build_map.py. Missing file
means the map is disabled. Standard library only. Paths are Dijkstra searches
whose edge cost is GAP_WEIGHT * (b_target - b_source)^2 + STEP_COST. The squared
gap makes one big jump dearer than several small ones (a 0.6 jump costs 3.7, six
0.1 steps cost 1.2), so a path prefers steady steps between similar problems.
"""
import heapq
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PATH = ROOT / 'data/ml/problem_map.json'
MAX_BYTES = 400 * 1024
STEP_COST = 0.1
GAP_WEIGHT = 10.0
START_POOL = 10


def _finite(x):
    return type(x) in (int, float) and math.isfinite(x)


def validate_map(data):
    if not isinstance(data, dict) or data.get('version') != 1:
        raise ValueError('Problem map needs version 1 metadata')
    nodes, edges = data.get('nodes'), data.get('edges')
    if not isinstance(nodes, list) or not nodes:
        raise ValueError('Problem map needs a non-empty node list')
    if not isinstance(edges, list):
        raise ValueError('Problem map needs an edge list')
    clean_nodes, seen = [], set()
    for node in nodes:
        if not isinstance(node, dict) or not isinstance(node.get('id'), str) or not node['id']:
            raise ValueError('Every map node needs a string id')
        if node['id'] in seen:
            raise ValueError(f'Duplicate map node id: {node["id"]}')
        seen.add(node['id'])
        for key in ('x', 'y', 'b'):
            if not _finite(node.get(key)):
                raise ValueError(f'Map node {node["id"]} needs a finite {key}')
        if type(node.get('cluster')) is not int:
            raise ValueError(f'Map node {node["id"]} needs an integer cluster')
        clean_nodes.append({'id': node['id'], 'level': node.get('level'), 'x': float(node['x']), 'y': float(node['y']),
                            'cluster': node['cluster'], 'b': float(node['b']),
                            'languages': list(node.get('languages') or [])})
    n = len(clean_nodes)
    clean_edges = []
    for edge in edges:
        if not isinstance(edge, list) or len(edge) != 3:
            raise ValueError('Map edges must be [source, target, weight]')
        a, b, w = edge
        if type(a) is not int or type(b) is not int or not (0 <= a < n and 0 <= b < n) or a == b:
            raise ValueError('Map edge indices must be two different nodes in range')
        if not _finite(w):
            raise ValueError('Map edge weights must be finite')
        clean_edges.append((a, b, float(w)))
    clusters = data.get('clusters') or []
    if not isinstance(clusters, list):
        raise ValueError('Map clusters must be a list')
    return clean_nodes, clean_edges, clusters


class LearningMap:
    def __init__(self, path=None):
        self.file = Path(path) if path is not None else DEFAULT_PATH
        self.nodes, self.edges, self._clusters = [], [], []
        self.index = {}
        self.adjacency = []
        self.metadata = {}
        self._enabled = False
        if not self.file.is_file():
            return
        if self.file.stat().st_size > MAX_BYTES:
            raise ValueError('Problem map exceeds the 400 KB runtime budget')
        try:
            data = json.loads(self.file.read_text(encoding='utf-8'))
        except (UnicodeError, json.JSONDecodeError) as error:
            raise ValueError(f'Invalid problem map: {self.file}') from error
        self.nodes, self.edges, self._clusters = validate_map(data)
        self.index = {node['id']: i for i, node in enumerate(self.nodes)}
        best = {}
        for a, b, w in self.edges:  # duplicates keep the strongest weight
            key = (a, b) if a < b else (b, a)
            best[key] = max(w, best.get(key, w))
        self.adjacency = [[] for _ in self.nodes]
        for (a, b), w in best.items():
            self.adjacency[a].append((b, w))
            self.adjacency[b].append((a, w))
        ids = [node['id'] for node in self.nodes]
        for row in self.adjacency:
            row.sort(key=lambda pair: (-pair[1], ids[pair[0]]))
        self.metadata = {k: data[k] for k in ('version', 'source', 'k') if k in data}
        self._enabled = True

    @property
    def enabled(self):
        return self._enabled

    def node(self, problem_id):
        i = self.index.get(problem_id)
        return None if i is None else dict(self.nodes[i])

    def neighbors(self, problem_id, k=5):
        i = self.index.get(problem_id)
        if i is None:
            return []
        return [{'id': self.nodes[j]['id'], 'weight': w} for j, w in self.adjacency[i][:k]]

    def clusters(self):
        return [dict(c) for c in self._clusters]

    def _solved_indices(self, solved_ids):
        return sorted({self.index[s] for s in solved_ids or () if s in self.index})

    def path(self, solved_ids, goal_id, max_steps=6):
        """Cheapest stepping-stone route from what the student solved to goal_id.

        Returns {'goal', 'steps', 'cost', 'remaining', 'reachable'}; steps are
        unsolved ids ending with the goal. With more than max_steps, the last
        max_steps before (and including) the goal are kept and the number of
        earlier steps is reported as 'remaining'.
        """
        if goal_id not in self.index:
            raise ValueError(f'Unknown goal problem: {goal_id}')
        goal = self.index[goal_id]
        solved = self._solved_indices(solved_ids)
        solved_set = set(solved)
        if goal in solved_set:
            return {'goal': goal_id, 'steps': [], 'cost': 0.0, 'remaining': 0, 'reachable': True}
        ids = [node['id'] for node in self.nodes]
        bvals = [node['b'] for node in self.nodes]
        sources = solved or sorted(range(len(self.nodes)), key=lambda i: (bvals[i], ids[i]))[:START_POOL]
        dist = {}
        prev = {}
        heap = []
        for s in sources:
            dist[s] = 0.0
            prev[s] = None
            heap.append((0.0, ids[s], s))
        heapq.heapify(heap)
        done = set()
        while heap:
            d, _sid, u = heapq.heappop(heap)
            if u in done:
                continue
            done.add(u)
            if u == goal:
                break
            bu = bvals[u]
            for v, _w in self.adjacency[u]:
                if v in done:
                    continue
                nd = d + GAP_WEIGHT * (bvals[v] - bu) ** 2 + STEP_COST
                old = dist.get(v)
                # tie on cost: prefer the predecessor with the smaller id
                if old is None or nd < old - 1e-12 or (abs(nd - old) <= 1e-12 and ids[u] < ids[prev[v]]):
                    dist[v] = nd
                    prev[v] = u
                    heapq.heappush(heap, (nd, ids[v], v))
        if goal not in done:
            return {'goal': goal_id, 'steps': [], 'cost': None, 'remaining': 0, 'reachable': False}
        route, cur = [], goal
        while cur is not None:
            route.append(cur)
            cur = prev[cur]
        route.reverse()
        steps = [ids[i] for i in route if i not in solved_set]
        remaining = max(0, len(steps) - max_steps)
        if remaining:
            steps = steps[-max_steps:] if max_steps > 0 else []
        return {'goal': goal_id, 'steps': steps, 'cost': round(dist[goal], 6), 'remaining': remaining, 'reachable': True}

    def frontier(self, solved_ids, limit=5):
        """Unsolved neighbours of solved problems, closest in b just above the student's mean."""
        ids = [node['id'] for node in self.nodes]
        solved = self._solved_indices(solved_ids)
        if not solved:
            order = sorted(range(len(self.nodes)), key=lambda i: (self.nodes[i]['b'], ids[i]))[:limit]
            return [{'id': ids[i], 'b': self.nodes[i]['b'], 'gap': None, 'via': None} for i in order]
        solved_set = set(solved)
        mean_b = sum(self.nodes[i]['b'] for i in solved) / len(solved)
        via = {}
        for s in solved:
            for v, w in self.adjacency[s]:
                if v in solved_set:
                    continue
                # strongest solved neighbour; on equal weight the smaller id
                if v not in via or w > via[v][1] or (w == via[v][1] and ids[s] < ids[via[v][0]]):
                    via[v] = (s, w)
        candidates = []
        for v, (s, _w) in via.items():
            gap = self.nodes[v]['b'] - mean_b
            candidates.append(((0 if gap >= 0 else 1, abs(gap), ids[v]), v, s, gap))
        candidates.sort()
        return [{'id': ids[v], 'b': self.nodes[v]['b'], 'gap': round(gap, 6), 'via': ids[s]}
                for _key, v, s, gap in candidates[:limit]]

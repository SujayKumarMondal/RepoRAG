"""
Dependency graph construction and traversal.
"""

from collections import defaultdict, deque
from dataclasses import dataclass


@dataclass(frozen=True)
class GraphEdge:
    """
    Directed dependency edge.
    """

    source: str
    target: str
    dependency_type: str = "import"


class DependencyGraph:
    """
    In-memory directed dependency graph.

    Later this graph can be persisted to PostgreSQL.
    """

    def __init__(self) -> None:

        self.edges: list[GraphEdge] = []

        self.adjacency: dict[
            str,
            set[str],
        ] = defaultdict(set)

    def add_edge(
        self,
        source: str,
        target: str,
        dependency_type: str = "import",
    ) -> None:

        edge = GraphEdge(
            source=source,
            target=target,
            dependency_type=dependency_type,
        )

        self.edges.append(edge)

        self.adjacency[source].add(target)

    def add_edges(
        self,
        edges: list[GraphEdge],
    ) -> None:

        for edge in edges:

            self.add_edge(
                edge.source,
                edge.target,
                edge.dependency_type,
            )

    def neighbors(
        self,
        node: str,
    ) -> list[str]:

        return sorted(
            self.adjacency.get(
                node,
                set(),
            )
        )

    def dependencies(
        self,
        node: str,
        depth: int = 2,
    ) -> set[str]:

        visited: set[str] = set()

        queue = deque(
            [(node, 0)]
        )

        while queue:

            current, current_depth = (
                queue.popleft()
            )

            if current_depth >= depth:
                continue

            for neighbor in self.neighbors(
                current
            ):

                if neighbor in visited:
                    continue

                visited.add(neighbor)

                queue.append(
                    (
                        neighbor,
                        current_depth + 1,
                    )
                )

        return visited

    def dependents(
        self,
        node: str,
    ) -> set[str]:

        result = set()

        for source, targets in (
            self.adjacency.items()
        ):

            if node in targets:
                result.add(source)

        return result

    def to_dict(self) -> dict:

        return {
            "nodes": sorted(
                self.adjacency.keys()
            ),
            "edges": [
                {
                    "source": edge.source,
                    "target": edge.target,
                    "dependency_type": (
                        edge.dependency_type
                    ),
                }
                for edge in self.edges
            ],
        }
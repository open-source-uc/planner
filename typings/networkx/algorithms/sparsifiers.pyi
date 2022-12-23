"""
This type stub file was generated by pyright.
"""

from networkx.utils import not_implemented_for, py_random_state

"""Functions for computing sparsifiers of graphs."""
__all__ = ["spanner"]
@py_random_state(3)
@not_implemented_for("directed")
@not_implemented_for("multigraph")
def spanner(G, stretch, weight=..., seed=...):
    """Returns a spanner of the given graph with the given stretch.

    A spanner of a graph G = (V, E) with stretch t is a subgraph
    H = (V, E_S) such that E_S is a subset of E and the distance between
    any pair of nodes in H is at most t times the distance between the
    nodes in G.

    Parameters
    ----------
    G : NetworkX graph
        An undirected simple graph.

    stretch : float
        The stretch of the spanner.

    weight : object
        The edge attribute to use as distance.

    seed : integer, random_state, or None (default)
        Indicator of random number generation state.
        See :ref:`Randomness<randomness>`.

    Returns
    -------
    NetworkX graph
        A spanner of the given graph with the given stretch.

    Raises
    ------
    ValueError
        If a stretch less than 1 is given.

    Notes
    -----
    This function implements the spanner algorithm by Baswana and Sen,
    see [1].

    This algorithm is a randomized las vegas algorithm: The expected
    running time is O(km) where k = (stretch + 1) // 2 and m is the
    number of edges in G. The returned graph is always a spanner of the
    given graph with the specified stretch. For weighted graphs the
    number of edges in the spanner is O(k * n^(1 + 1 / k)) where k is
    defined as above and n is the number of nodes in G. For unweighted
    graphs the number of edges is O(n^(1 + 1 / k) + kn).

    References
    ----------
    [1] S. Baswana, S. Sen. A Simple and Linear Time Randomized
    Algorithm for Computing Sparse Spanners in Weighted Graphs.
    Random Struct. Algorithms 30(4): 532-563 (2007).
    """
    ...


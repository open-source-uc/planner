"""
This type stub file was generated by pyright.
"""

"""Priority queue class with updatable priorities.
"""
__all__ = ["MappedQueue"]
class _HeapElement:
    """This proxy class separates the heap element from its priority.

    The idea is that using a 2-tuple (priority, element) works
    for sorting, but not for dict lookup because priorities are
    often floating point values so round-off can mess up equality.

    So, we need inequalities to look at the priority (for sorting)
    and equality (and hash) to look at the element to enable
    updates to the priority.

    Unfortunately, this class can be tricky to work with if you forget that
    `__lt__` compares the priority while `__eq__` compares the element.
    In `greedy_modularity_communities()` the following code is
    used to check that two _HeapElements differ in either element or priority:

        if d_oldmax != row_max or d_oldmax.priority != row_max.priority:

    If the priorities are the same, this implementation uses the element
    as a tiebreaker. This provides compatibility with older systems that
    use tuples to combine priority and elements.
    """
    __slots__ = ...
    def __init__(self, priority, element) -> None:
        ...
    
    def __lt__(self, other) -> bool:
        ...
    
    def __gt__(self, other) -> bool:
        ...
    
    def __eq__(self, other) -> bool:
        ...
    
    def __hash__(self) -> int:
        ...
    
    def __getitem__(self, indx): # -> Unknown:
        ...
    
    def __iter__(self): # -> Generator[Unknown, None, None]:
        ...
    
    def __repr__(self): # -> str:
        ...
    


class MappedQueue:
    """The MappedQueue class implements a min-heap with removal and update-priority.

    The min heap uses heapq as well as custom written _siftup and _siftdown
    methods to allow the heap positions to be tracked by an additional dict
    keyed by element to position. The smallest element can be popped in O(1) time,
    new elements can be pushed in O(log n) time, and any element can be removed
    or updated in O(log n) time. The queue cannot contain duplicate elements
    and an attempt to push an element already in the queue will have no effect.

    MappedQueue complements the heapq package from the python standard
    library. While MappedQueue is designed for maximum compatibility with
    heapq, it adds element removal, lookup, and priority update.

    Examples
    --------

    A `MappedQueue` can be created empty or optionally given an array of
    initial elements. Calling `push()` will add an element and calling `pop()`
    will remove and return the smallest element.

    >>> q = MappedQueue([916, 50, 4609, 493, 237])
    >>> q.push(1310)
    True
    >>> [q.pop() for i in range(len(q.heap))]
    [50, 237, 493, 916, 1310, 4609]

    Elements can also be updated or removed from anywhere in the queue.

    >>> q = MappedQueue([916, 50, 4609, 493, 237])
    >>> q.remove(493)
    >>> q.update(237, 1117)
    >>> [q.pop() for i in range(len(q.heap))]
    [50, 916, 1117, 4609]

    References
    ----------
    .. [1] Cormen, T. H., Leiserson, C. E., Rivest, R. L., & Stein, C. (2001).
       Introduction to algorithms second edition.
    .. [2] Knuth, D. E. (1997). The art of computer programming (Vol. 3).
       Pearson Education.
    """
    def __init__(self, data=...) -> None:
        """Priority queue class with updatable priorities."""
        ...
    
    def __len__(self): # -> int:
        ...
    
    def push(self, elt, priority=...): # -> bool:
        """Add an element to the queue."""
        ...
    
    def pop(self): # -> _HeapElement:
        """Remove and return the smallest element in the queue."""
        ...
    
    def update(self, elt, new, priority=...): # -> None:
        """Replace an element in the queue with a new one."""
        ...
    
    def remove(self, elt): # -> None:
        """Remove an element from the queue."""
        ...
    


"""Edge cases where the proof's '=' (mathematical equality) and the code's == could diverge."""
import sys; sys.path.insert(0, "/home/user/dsdk/src")
from dsdk.logic.structures import Leaf, Node, mirror
nan = float("nan")
t = Node(Leaf(nan), Leaf(1))
print("NaN leaf (same object): mirror(mirror(t)) == t ->", mirror(mirror(t)) == t)
class Bad:
    def __eq__(s, o): return False
    __hash__ = None
b = Leaf(Bad()); print("Leaf with __eq__=False: mirror(mirror(Leaf(b))) == Leaf(b) ->", mirror(mirror(b)) == b, "| same object:", mirror(mirror(b)) is b)
t2 = Node(Leaf(Bad()), Leaf(1)); print("Node containing it: mirror(mirror(t2)) == t2 ->", mirror(mirror(t2)) == t2)

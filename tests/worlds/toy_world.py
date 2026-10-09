"""A six-track toy festival small enough to check by hand. Every expected value in the worlds tests that uses it is
derived in a comment next to the assertion.

Artists  0 Ada, 1 Bo, 2 Cy.          Dates  0 "2018-01-01", 1 "2018-01-02".
Tracks   T0 Ada - One                T1 Bo - Two          T2 Cy - Three (REMIX by Bo, feat. Ada)
         T3 Ada & Bo - Four          T4 Bo - Five         T5 Cy - Six  (never played)
Groups   G0 "Ada" [Ada]   G1 "Bo & Cy" [Bo, Cy]   G2 "Cy + More" [Cy] (truncated credit)
Sets     A = (G0, d0): T0 T1 T2        B = (G1, d0): T2 T3
         C = (G0, d1): T0 T1           D = (G2, d1): T3 T4 T3   (T3 is played twice)
Transitions 0>1(A) 1>2(A) 2>3(B) 0>1(C) 3>4(D) 4>3(D)
"""
import copy

TOY_DOC = {
    "schema": "jukebox-primitives/v1",
    "meta": {"corpus": "toy", "sourceFiles": 4, "rejectedRows": 0, "tracks": 6, "selectionEvents": 10, "transitionEvents": 6},
    "artists": ["Ada", "Bo", "Cy"],
    "tracks": [
        ["One#001", "One", [0], [], None, []],
        ["Two#001", "Two", [1], [], None, []],
        ["Three#001", "Three", [2], [0], "REMIX", [1]],
        ["Four#001", "Four", [0, 1], [], None, []],
        ["Five#001", "Five", [1], [], None, []],
        ["Six#001", "Six", [2], [], None, []],
    ],
    "selectorGroups": [[[0], "Ada", 0], [[1, 2], "Bo & Cy", 0], [[2], "Cy + More", 1]],
    "dates": ["2018-01-01", "2018-01-02"],
    "selections": [[0, 0, 0], [1, 0, 0], [2, 0, 0], [2, 1, 0], [3, 1, 0], [0, 0, 1], [1, 0, 1], [3, 2, 1], [4, 2, 1], [3, 2, 1]],
    "transitions": [[0, 1, 0, 0], [1, 2, 0, 0], [2, 3, 1, 0], [0, 1, 0, 1], [3, 4, 2, 1], [4, 3, 2, 1]],
}


def toy_doc():
    """A fresh deep copy (tests mutate it to build adversarial documents)."""
    return copy.deepcopy(TOY_DOC)


def toy_world(**kwargs):
    from dsdk.worlds import parse_lostlands

    return parse_lostlands(toy_doc(), **kwargs)

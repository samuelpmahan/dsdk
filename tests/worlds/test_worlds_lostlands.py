"""Lost Lands loader: integrity, decoding, validation, provenance. Hand-derived toy values plus the real corpus.

The real-corpus numbers (1,352 tracks, 817 artists, 50 selector groups, 8 dates, 1,973 selections, 1,919 transitions,
54 sets) were counted by fixtures/worlds/gen_slices.py, an independent script that does not import dsdk.
"""
import gzip
import hashlib
import json
import shutil

import pytest
from toy_world import TOY_DOC, toy_doc, toy_world

from dsdk.core import AddressOccupiedError, PxC, Status
from dsdk.graph import CALCULATION_LABEL, lineage_graph
from dsdk.worlds import (
    FIXTURE_PATH, PINNED_SHA256, SCHEMA, SOURCE_COMMIT, IntegrityError, WorldError, check_transitions,
    describe_provenance, load_lostlands, parse_lostlands, record_provenance, sha256_bytes,
)

# ==== Pinned constants and the vendored file ====
def test_the_pinned_digest_is_the_one_in_jukeboxs_pages_workflow():
    """jukebox .github/workflows/pages.yml: expected="7e0b652a...eb8a5"; the commit is the lab/composable-mining tip."""
    assert PINNED_SHA256 == "7e0b652aac543fbe89e80e8b47b5e7f0e67ac622ee20ae2426bd6d07492eb8a5"
    assert SOURCE_COMMIT == "8b4d32b44217f8b4eb08977c9920a03194b2b1b2"
    assert SCHEMA == "jukebox-primitives/v1" and len(SCHEMA) == 21


def test_the_vendored_file_really_has_the_pinned_digest():
    """Hash the bytes ourselves: the fixture is what the contract says it is (hermetic and tamper-evident)."""
    assert FIXTURE_PATH.name == "lostlands-2018.jukebox.json.gz" and FIXTURE_PATH.parent.name == "worlds"
    assert hashlib.sha256(FIXTURE_PATH.read_bytes()).hexdigest() == PINNED_SHA256
    assert sha256_bytes(b"") == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    assert sha256_bytes(b"abc") == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"


# ==== Integrity: a tampered or undecodable file is refused ====
def test_load_default_path_verifies_and_records_the_digest(real_world):
    """Loading the vendored corpus verifies it against the pinned digest and records that digest on the world."""
    assert real_world.sha256 == PINNED_SHA256


def test_a_flipped_byte_is_an_integrity_error_before_any_decoding(tmp_path):
    """Integrity comes first: a corrupt non-gzip file with the wrong digest says 'sha256', not 'gzip'."""
    bad = tmp_path / "bad.gz"
    data = bytearray(FIXTURE_PATH.read_bytes())
    data[len(data) // 2] ^= 0x01
    bad.write_bytes(bytes(data))
    with pytest.raises(IntegrityError) as err:
        load_lostlands(bad)
    assert PINNED_SHA256 in str(err.value) and hashlib.sha256(bytes(data)).hexdigest() in str(err.value)
    assert isinstance(err.value, WorldError) and isinstance(err.value, ValueError)


def test_a_different_pin_is_honoured_and_case_does_not_matter(tmp_path):
    """A caller-supplied pin is honoured (upper case accepted) and the real-corpus pin does not accept a different file."""
    other = tmp_path / "toy.json.gz"
    other.write_bytes(gzip.compress(json.dumps(TOY_DOC).encode()))
    digest = sha256_bytes(other.read_bytes())
    assert load_lostlands(other, expected_sha256=digest.upper()).sha256 == digest
    with pytest.raises(IntegrityError):
        load_lostlands(other)  # default pin is the real corpus
    with pytest.raises(IntegrityError):
        load_lostlands(other, expected_sha256="0" * 64)


def test_expected_sha256_none_skips_the_check_but_still_reports_the_digest(tmp_path):
    """Passing expected_sha256=None skips the integrity check but the world still carries the file's actual digest."""
    other = tmp_path / "toy.json.gz"
    other.write_bytes(gzip.compress(json.dumps(TOY_DOC).encode()))
    world = load_lostlands(other, expected_sha256=None)
    assert world.sha256 == sha256_bytes(other.read_bytes()) and len(world.tracks) == 6


def test_path_may_be_a_str(tmp_path):
    """load_lostlands accepts a plain string path as well as a Path."""
    copy = tmp_path / "copy.gz"
    shutil.copy(FIXTURE_PATH, copy)
    assert len(load_lostlands(str(copy)).tracks) == 1352


def test_missing_file_is_file_not_found_not_a_world_error(tmp_path):
    """A missing file raises FileNotFoundError, not a data-format error."""
    with pytest.raises(FileNotFoundError):
        load_lostlands(tmp_path / "nope.gz")


@pytest.mark.parametrize(
    "payload, prefix",
    [
        (b"this is not gzip", "gzip:"),
        (gzip.compress(b'{"schema": ')[:-6], "gzip:"),  # truncated stream
        (gzip.compress(b"{not json"), "json:"),
        (gzip.compress(b"\xff\xfe\x00bad utf8"), "json:"),
        (gzip.compress(b"[]"), "schema"),  # valid JSON, wrong shape
    ],
)
def test_undecodable_payloads_are_world_errors_with_a_stage_prefix(tmp_path, payload, prefix):
    """Files that are not gzip, are truncated, are not JSON, are not UTF-8 or are JSON of the wrong shape each raise WorldError with a message starting with the stage that failed."""
    f = tmp_path / "x.gz"
    f.write_bytes(payload)
    with pytest.raises(WorldError) as err:
        load_lostlands(f, expected_sha256=None)
    assert str(err.value).startswith(prefix)


# ==== Decoding the toy festival by hand ====
def test_toy_world_decodes_exactly():
    """Every field of the toy document, derived from the doc in tests/worlds/toy_world.py."""
    w = toy_world()
    assert w.sha256 == "" and w.meta["corpus"] == "toy"
    assert [a.name for a in w.artists] == ["Ada", "Bo", "Cy"] and [a.id for a in w.artists] == [0, 1, 2]
    t2 = w.tracks[2]
    assert (t2.id, t2.key, t2.title, t2.artist, t2.artists, t2.featured, t2.variation, t2.variation_artists) == (
        2, "Three#001", "Three", "Cy", (2,), (0,), "REMIX", (1,))
    assert w.tracks[3].artist == "Ada & Bo"
    assert w.tracks[0].variation is None and w.tracks[3].artists == (0, 1)
    assert [(g.id, g.label, g.members, g.truncated) for g in w.groups] == [
        (0, "Ada", (0,), False), (1, "Bo & Cy", (1, 2), False), (2, "Cy + More", (2,), True)]
    assert w.dates == ("2018-01-01", "2018-01-02")
    assert len(w.selections) == 10 and len(w.transitions) == 6
    assert (w.selections[3].track, w.selections[3].group, w.selections[3].date) == (2, 1, 0)
    assert (w.transitions[5].source, w.transitions[5].target, w.transitions[5].group, w.transitions[5].date) == (4, 3, 2, 1)
    assert isinstance(w.tracks, tuple) and isinstance(w.selections, tuple) and isinstance(w.artists, tuple)


def test_toy_labels():
    """Track names render as 'Artists - Title', add the variation in parentheses, leave out featured artists, and dates render as their ISO string or None."""
    w = toy_world()
    assert w.track_artists(3) == "Ada & Bo" and w.track_artists(0) == "Ada"
    assert w.track_label(0) == "Ada - One"
    assert w.track_label(2) == "Cy - Three (REMIX)"  # featured Ada is NOT in the label
    assert w.track_label(3) == "Ada & Bo - Four"
    assert w.date_label(0) == "2018-01-01" and w.date_label(1) == "2018-01-02" and w.date_label(None) is None


def test_tracks_have_unique_string_keys_and_an_artist_string():
    """Every track carries a unique string key (what graphs use as the node name) and a readable artist string, and the key can be turned back into the track ID."""
    w = toy_world()
    assert [w.track_key(i) for i in range(6)] == ["One#001", "Two#001", "Three#001", "Four#001", "Five#001", "Six#001"]
    assert [w.track_index(w.track_key(i)) for i in range(6)] == list(range(6))
    assert [t.artist for t in w.tracks] == ["Ada", "Bo", "Cy", "Ada & Bo", "Bo", "Cy"]
    with pytest.raises(KeyError):
        w.track_index("Nine#001")
    with pytest.raises(IndexError):
        w.track_key(-1)
    with pytest.raises(IndexError):
        w.track_key(6)


def test_a_transition_row_is_source_target_group_date_in_that_order():
    """In the raw file a transition row is [source track, target track, DJ credit, date index], counting columns from 0: column 2 is the DJ credit and column 3 is the date, and the typed record names them the same way."""
    w = toy_world()
    row = TOY_DOC["transitions"][2]  # [2, 3, 1, 0]: Three#001 then Four#001, played by "Bo & Cy" on the first date
    t = w.transitions[2]
    assert row == [2, 3, 1, 0] and (t.source, t.target, t.group, t.date) == (2, 3, 1, 0)
    assert (w.track_key(t.source), w.track_key(t.target), w.groups[t.group].label, w.dates[t.date]) == (
        "Three#001", "Four#001", "Bo & Cy", "2018-01-01")


@pytest.mark.parametrize("bad", [-1, 6, 99])
def test_track_lookups_do_not_wrap_around(bad):
    """Looking up a negative or too-large track ID raises IndexError instead of wrapping around like a Python list."""
    w = toy_world()
    for call in (w.track_artists, w.track_label):
        with pytest.raises(IndexError):
            call(bad)


@pytest.mark.parametrize("bad", [-2, -1, 2, 7])
def test_date_label_rejects_out_of_range_indices(bad):
    """date_label raises IndexError for any out-of-range date index."""
    with pytest.raises(IndexError):
        toy_world().date_label(bad)


def test_sets_are_grouped_in_first_appearance_order_and_keep_repeats():
    """A=(0,0): T0 T1 T2; B=(1,0): T2 T3; C=(0,1): T0 T1; D=(2,1): T3 T4 T3 (T3 repeated)."""
    sets = toy_world().sets()
    assert list(sets) == [(0, 0), (1, 0), (0, 1), (2, 1)]
    assert sets == {(0, 0): (0, 1, 2), (1, 0): (2, 3), (0, 1): (0, 1), (2, 1): (3, 4, 3)}


def test_check_transitions_toy_is_consistent():
    """The toy world's transitions are exactly the consecutive pairs of its four sets, and check_transitions says KNOWN True with that count."""
    j = check_transitions(toy_world())
    assert (j.status, j.value, j.reason) == (Status.KNOWN, True, "transitions match the consecutive pairs of 4 sets")


def test_check_transitions_notices_a_missing_extra_reordered_or_orphan_transition():
    """check_transitions returns KNOWN False, naming the bad set, when a transition is missing, extra, in the wrong order, or belongs to a set that has no selections."""
    def verdict(mutate):
        doc = toy_doc()
        mutate(doc)
        doc["meta"]["transitionEvents"] = len(doc["transitions"])
        return check_transitions(parse_lostlands(doc))

    j = verdict(lambda d: d["transitions"].pop(1))  # drop 1>2 of set A
    assert (j.status, j.value) == (Status.KNOWN, False) and j.reason == "set (0, 0) has transitions that are not its consecutive pairs"
    j = verdict(lambda d: d["transitions"].append([1, 0, 0, 1]))  # extra pair in set C
    assert j.value is False and j.reason == "set (0, 1) has transitions that are not its consecutive pairs"
    j = verdict(lambda d: d["transitions"].__setitem__(slice(4, 6), [[4, 3, 2, 1], [3, 4, 2, 1]]))  # set D pairs swapped: order matters
    assert j.value is False and j.reason == "set (2, 1) has transitions that are not its consecutive pairs"
    j = verdict(lambda d: d["transitions"].append([0, 1, 1, 1]))  # (G1, d1) has no selections
    assert j.value is False and j.reason == "transition set (1, 1) has no selections"


def test_check_transitions_reports_the_first_bad_set_in_set_order():
    """When several sets are inconsistent, check_transitions names the first one in set order."""
    doc = toy_doc()
    doc["transitions"] = [t for t in doc["transitions"] if t[:2] not in ([2, 3], [4, 3])]  # breaks B and D
    doc["meta"]["transitionEvents"] = len(doc["transitions"])
    assert check_transitions(parse_lostlands(doc)).reason.startswith("set (1, 0)")


def test_a_set_with_one_track_has_no_transitions_and_is_consistent():
    """A set containing a single track needs no transitions and counts as consistent."""
    doc = toy_doc()
    doc["selections"].append([5, 1, 1])  # (G1, d1): only T5
    doc["meta"]["selectionEvents"] = 11
    j = check_transitions(parse_lostlands(doc))
    assert j.value is True and j.reason.endswith("5 sets")


def test_undated_sets_are_kept_with_date_none():
    """date -1 means 'the source file had no date': decoded as None, never confused with date index 0 or -1."""
    doc = toy_doc()
    doc["selections"] += [[1, 0, -1], [2, 0, -1]]
    doc["transitions"].append([1, 2, 0, -1])
    doc["meta"].update(selectionEvents=12, transitionEvents=7)
    w = parse_lostlands(doc)
    assert w.selections[-1].date is None and w.transitions[-1].date is None
    assert w.sets()[(0, None)] == (1, 2)
    assert check_transitions(w).value is True


def test_parse_extra_keys_are_tolerated_and_the_input_is_not_aliased():
    """Extra top-level keys are ignored, and editing the input document afterwards does not change an already-decoded world."""
    doc = toy_doc()
    doc["note"] = "extra"
    w = parse_lostlands(doc, sha256="abc")
    assert w.sha256 == "abc"
    doc["artists"].append("Zed")
    doc["meta"]["corpus"] = "changed"
    assert len(w.artists) == 3 and w.meta["corpus"] == "toy"


# ==== Malformed documents are rejected with a named field ====
def _mut(fn):
    doc = toy_doc()
    fn(doc)
    return doc


BAD_DOCS = {
    "not a mapping": ([], "schema"),
    "none": (None, "schema"),
    "wrong schema": (_mut(lambda d: d.__setitem__("schema", "jukebox-primitives/v2")), "schema"),
    "schema missing": (_mut(lambda d: d.pop("schema")), "schema"),
    "missing meta": (_mut(lambda d: d.pop("meta")), "meta"),
    "missing artists": (_mut(lambda d: d.pop("artists")), "artists"),
    "missing tracks": (_mut(lambda d: d.pop("tracks")), "tracks"),
    "missing selectorGroups": (_mut(lambda d: d.pop("selectorGroups")), "selectorGroups"),
    "missing dates": (_mut(lambda d: d.pop("dates")), "dates"),
    "missing selections": (_mut(lambda d: d.pop("selections")), "selections"),
    "missing transitions": (_mut(lambda d: d.pop("transitions")), "transitions"),
    "artist not a string": (_mut(lambda d: d["artists"].__setitem__(1, 7)), "artists"),
    "dates not strings": (_mut(lambda d: d["dates"].__setitem__(0, 20180101)), "dates"),
    "track row too short": (_mut(lambda d: d["tracks"][2].pop()), "tracks[2]"),
    "track title not str": (_mut(lambda d: d["tracks"][1].__setitem__(1, None)), "tracks[1]"),
    "track artist out of range": (_mut(lambda d: d["tracks"][4].__setitem__(2, [3])), "tracks[4]"),
    "track artist negative": (_mut(lambda d: d["tracks"][4].__setitem__(2, [-1])), "tracks[4]"),
    "track artist is a bool": (_mut(lambda d: d["tracks"][0].__setitem__(2, [True])), "tracks[0]"),
    "track featured out of range": (_mut(lambda d: d["tracks"][2].__setitem__(3, [9])), "tracks[2]"),
    "track variation is a number": (_mut(lambda d: d["tracks"][2].__setitem__(4, 3)), "tracks[2]"),
    "track variation artists out of range": (_mut(lambda d: d["tracks"][2].__setitem__(5, [3])), "tracks[2]"),
    "group row wrong length": (_mut(lambda d: d["selectorGroups"][0].append(0)), "selectorGroups[0]"),
    "group member out of range": (_mut(lambda d: d["selectorGroups"][1].__setitem__(0, [1, 3])), "selectorGroups[1]"),
    "group truncated is 2": (_mut(lambda d: d["selectorGroups"][2].__setitem__(2, 2)), "selectorGroups[2]"),
    "selection row wrong length": (_mut(lambda d: d["selections"][3].append(0)), "selections[3]"),
    "selection track out of range": (_mut(lambda d: d["selections"][2].__setitem__(0, 6)), "selections[2]"),
    "selection track is a bool": (_mut(lambda d: d["selections"][2].__setitem__(0, True)), "selections[2]"),
    "selection track is a float": (_mut(lambda d: d["selections"][2].__setitem__(0, 1.0)), "selections[2]"),
    "selection group out of range": (_mut(lambda d: d["selections"][9].__setitem__(1, 3)), "selections[9]"),
    "selection date below -1": (_mut(lambda d: d["selections"][0].__setitem__(2, -2)), "selections[0]"),
    "selection date past the end": (_mut(lambda d: d["selections"][0].__setitem__(2, 2)), "selections[0]"),
    "transition row wrong length": (_mut(lambda d: d["transitions"][0].pop()), "transitions[0]"),
    "transition source out of range": (_mut(lambda d: d["transitions"][4].__setitem__(0, 6)), "transitions[4]"),
    "transition target negative": (_mut(lambda d: d["transitions"][4].__setitem__(1, -1)), "transitions[4]"),
    "transition group out of range": (_mut(lambda d: d["transitions"][1].__setitem__(2, 3)), "transitions[1]"),
    "transition date out of range": (_mut(lambda d: d["transitions"][5].__setitem__(3, 5)), "transitions[5]"),
    "duplicate track key": (_mut(lambda d: d["tracks"][3].__setitem__(0, "One#001")), "tracks[3]"),
    "duplicate group label": (_mut(lambda d: d["selectorGroups"][2].__setitem__(1, "Ada")), "selectorGroups[2]"),
    "meta not an object": (_mut(lambda d: d.__setitem__("meta", [])), "meta"),
    "meta.tracks wrong": (_mut(lambda d: d["meta"].__setitem__("tracks", 7)), "meta.tracks"),
    "meta.tracks missing": (_mut(lambda d: d["meta"].pop("tracks")), "meta.tracks"),
    "meta.tracks is a string": (_mut(lambda d: d["meta"].__setitem__("tracks", "6")), "meta.tracks"),
    "meta.selectionEvents wrong": (_mut(lambda d: d["meta"].__setitem__("selectionEvents", 9)), "meta.selectionEvents"),
    "meta.transitionEvents wrong": (_mut(lambda d: d["meta"].__setitem__("transitionEvents", 0)), "meta.transitionEvents"),
}


@pytest.mark.parametrize("name", BAD_DOCS)
def test_malformed_documents_raise_world_error_naming_the_field(name):
    """Each of 45 kinds of malformed document (wrong schema, missing key, bad row, out-of-range ID, bool or float where an integer is required, wrong meta count) raises WorldError whose message names the field, never a KeyError or TypeError."""
    doc, field = BAD_DOCS[name]
    with pytest.raises(WorldError) as err:
        parse_lostlands(doc)
    assert field in str(err.value), f"{name}: message {err.value!s} should mention {field!r}"
    assert not isinstance(err.value, (KeyError, TypeError, IndexError))


def test_group_truncated_accepts_booleans_and_zero_one():
    """A selector group's truncated flag accepts 0, 1, False and True."""
    doc = toy_doc()
    doc["selectorGroups"][0][2] = False
    doc["selectorGroups"][2][2] = True
    assert [g.truncated for g in parse_lostlands(doc).groups] == [False, False, True]


def test_an_empty_world_is_valid():
    """A world with no tracks, groups or selections is valid and consistent."""
    doc = {"schema": SCHEMA, "meta": {"tracks": 0, "selectionEvents": 0, "transitionEvents": 0}, "artists": [], "tracks": [],
           "selectorGroups": [], "dates": [], "selections": [], "transitions": []}
    w = parse_lostlands(doc)
    assert (w.tracks, w.groups, w.sets()) == ((), (), {}) and check_transitions(w).value is True


# ==== The real Lost Lands corpus decodes to the counted numbers ====
def test_real_counts_match_the_independent_script(real_world, slices):
    """The real corpus decodes to 817 artists, 1,352 tracks, 50 selector groups, 8 dates, 1,973 selections, 1,919 transitions and 54 sets, matching both the file's own meta and an independent counting script."""
    c = slices["counts"]
    w = real_world
    assert (len(w.artists), len(w.tracks), len(w.groups), len(w.dates), len(w.selections), len(w.transitions)) == (
        c["artists"], c["tracks"], c["selectorGroups"], c["dates"], c["selections"], c["transitions"])
    assert (c["artists"], c["tracks"], c["selectorGroups"], c["dates"], c["selections"], c["transitions"], c["sets"]) == (
        817, 1352, 50, 8, 1973, 1919, 54)
    assert len(w.sets()) == c["sets"]
    assert w.meta == slices["source"]["meta"]
    assert w.meta["corpus"] == "lost-lands-2018" and w.meta["sourceFiles"] == 54 and w.meta["rejectedRows"] == 234


def test_real_dates_and_truncated_credits(real_world):
    """The real corpus has 8 dates from 2018-01-18 to 2018-11-18, exactly two truncated '+ More' credits, and no undated selection."""
    assert real_world.dates[0] == "2018-01-18" and real_world.dates[-1] == "2018-11-18" and len(real_world.dates) == 8
    assert [g.label for g in real_world.groups if g.truncated] == [
        "Excision & Sullivan King & Dion Timmer + More", "Virtual Riot & PhaseOne & Terravita + More"]
    assert all(s.date is not None for s in real_world.selections)


def test_real_labels_of_known_tracks(real_world):
    """Four real tracks decode to the expected readable names, such as 'Space Laces - Torque' for track 483."""
    assert real_world.track_label(483) == "Space Laces - Torque"
    assert real_world.track_label(237) == "PEEKABOO (USA) & G-REX - Babatunde"
    assert real_world.track_label(0) == "Excision - Codename X (REMIX)"
    assert real_world.track_label(1351) == "Zomboy - Resurrected"


def test_real_transitions_are_consistent_with_selections(real_world):
    """In the real corpus, every set's transitions are exactly the consecutive pairs of its selections, across all 54 sets."""
    j = check_transitions(real_world)
    assert (j.status, j.value) == (Status.KNOWN, True) and j.reason == "transitions match the consecutive pairs of 54 sets"


def test_real_mega_set_is_the_truncated_credit(real_world, slices):
    """One truncated credit holds 169 of 1,973 selections (the biggest set)."""
    (group, date), size = slices["counts"]["mega_set"]
    sets = real_world.sets()
    assert len(sets[(group, date)]) == size == 169
    assert max(len(v) for v in sets.values()) == 169
    assert real_world.groups[group].truncated and real_world.dates[date] == "2018-09-13"


def test_real_hand_checked_sets(real_world, slices):
    """The sets named in the slice file (two shortest, the two 2018-09-14 Kill The Noise credits, the mega set)."""
    for key, s in slices["sets"].items():
        g, d = (int(x) for x in key.split(","))
        assert real_world.groups[g].label == s["group_label"] and real_world.dates[d] == s["date_label"]
        assert list(real_world.sets()[(g, d)]) == s["tracks"], key
        pairs = [(t.source, t.target) for t in real_world.transitions if (t.group, t.date) == (g, d)]
        assert pairs == [tuple(p) for p in s["transitions"]], key


def test_real_hand_checked_tracks_selections(real_world, slices):
    """Per-track facts from the independent script: how often it was selected and in which sets."""
    for i, s in slices["tracks"].items():
        i = int(i)
        assert real_world.track_label(i) == s["label"]
        assert real_world.tracks[i].key == s["key"]
        assert sum(1 for x in real_world.selections if x.track == i) == s["selections"]
        sets = sorted({(x.group, x.date) for x in real_world.selections if x.track == i})
        assert [list(p) for p in sets] == s["sets"]
    assert slices["tracks"]["483"]["selections"] == 12 and len(slices["tracks"]["483"]["sets"]) == 11


# ==== Provenance is recorded as core Parts with lineage ====
def test_provenance_parts_toy():
    """Recording provenance writes five addresses in order (source digest, branch commit, counts, the describing function, and the provenance sentence) with the expected values."""
    store = record_provenance(toy_world(sha256="f" * 64))
    assert isinstance(store, PxC)
    assert [a for a, _ in store.entries()] == [
        "px.lostlands.source_sha256", "px.lostlands.source_commit", "px.lostlands.counts", "fn.lostlands.describe",
        "px.lostlands.provenance"]
    assert store.get("px.lostlands.source_sha256").value == "f" * 64
    assert store.get("px.lostlands.source_commit").value == SOURCE_COMMIT
    counts = store.get("px.lostlands.counts").value
    assert counts == {"corpus": "toy", "artists": 3, "tracks": 6, "selectorGroups": 3, "dates": 2, "selections": 10,
                      "transitions": 6, "sets": 4}
    assert list(counts) == ["corpus", "artists", "tracks", "selectorGroups", "dates", "selections", "transitions", "sets"]
    assert store.get("px.lostlands.provenance").value == (
        "toy: 6 tracks, 3 artists, 3 selector groups, 4 sets on 2 dates, 10 selections, 6 transitions; "
        f"sha256 {'f' * 12} @ 8b4d32b")
    assert store.get("fn.lostlands.describe").value is describe_provenance


def test_provenance_sentence_is_a_composed_part_with_real_lineage():
    """The sentence is not just stored: it was COMPOSED, so dsdk.graph can walk its lineage (5 nodes, 4 edges)."""
    store = record_provenance(toy_world(sha256="a" * 64))
    out = store.get("px.lostlands.provenance")
    assert out.composition is not None
    assert list(out.composition.inputs) == ["sha256", "commit", "counts"]
    assert out.composition.inputs["sha256"] is store.get("px.lostlands.source_sha256")
    assert out.composition.calculation is store.get("fn.lostlands.describe")
    g = lineage_graph(out)
    assert len(g.nodes) == 5 and len(g.edges) == 4
    assert {e.label for e in g.edges} == {CALCULATION_LABEL, "sha256", "commit", "counts"}
    receipts = store.receipts()
    assert len(receipts) == 1 and receipts[0].into == "px.lostlands.provenance" and receipts[0].status.value == "produced"


def test_provenance_into_an_existing_store_returns_that_store_and_is_write_once():
    """record_provenance writes into a store you pass and returns it; a second call raises AddressOccupiedError and writes nothing more."""
    store = PxC()
    assert record_provenance(toy_world(), store) is store
    with pytest.raises(AddressOccupiedError):
        record_provenance(toy_world(), store)
    assert len(store.entries()) == 5 and len(store.receipts()) == 1  # the failed second call wrote nothing


def test_provenance_does_not_clobber_unrelated_addresses():
    """Recording provenance leaves unrelated addresses in the store untouched."""
    store = PxC()
    from dsdk.core import Part
    store.set("px.other", Part(1))
    record_provenance(toy_world(), store)
    assert store.get("px.other").value == 1 and len(store.entries()) == 6


def test_provenance_missing_corpus_name_is_an_empty_string():
    """If the corpus has no name in its meta, the recorded counts use an empty string for it."""
    doc = toy_doc()
    del doc["meta"]["corpus"]
    assert record_provenance(parse_lostlands(doc)).get("px.lostlands.counts").value["corpus"] == ""


def test_provenance_of_the_real_world_matches_the_pins(real_world):
    """For the real corpus the recorded digest is the pinned one and the provenance sentence is exactly the expected one-line summary."""
    store = record_provenance(real_world)
    assert store.get("px.lostlands.source_sha256").value == PINNED_SHA256
    assert store.get("px.lostlands.provenance").value == (
        "lost-lands-2018: 1352 tracks, 817 artists, 50 selector groups, 54 sets on 8 dates, 1973 selections, "
        "1919 transitions; sha256 7e0b652aac54 @ 8b4d32b")


def test_describe_provenance_is_a_pure_function_of_its_inputs():
    """describe_provenance builds its sentence only from the digest, commit and counts it is given."""
    values = {"sha256": "0123456789abcdef", "commit": "1234567890", "counts": {
        "corpus": "c", "tracks": 1, "artists": 2, "selectorGroups": 3, "sets": 4, "dates": 5, "selections": 6, "transitions": 7}}
    assert describe_provenance(values) == "c: 1 tracks, 2 artists, 3 selector groups, 4 sets on 5 dates, 6 selections, 7 transitions; sha256 0123456789ab @ 1234567"

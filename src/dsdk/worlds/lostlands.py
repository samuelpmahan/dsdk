"""Lost Lands 2018: Sam's DJ-set corpus, decoded from jukebox's derived primitive store.

The source is ``data/lostlands-2018.jukebox.json.gz`` (reassembled from ``.part00 .. .part07``) on the
``lab/composable-mining`` branch of jukebox. It is PUBLIC, DERIVED data: no raw tracklist lines, URLs, set titles or
ordered full tracklists. A copy is vendored at ``fixtures/worlds/lostlands-2018.jukebox.json.gz`` so every test is
hermetic. Its SHA-256 is pinned in jukebox's Pages workflow (:data:`PINNED_SHA256`).

File format (``schema == "jukebox-primitives/v1"``; the string is 21 characters long)
------------------------------------------------------------------------------------
A gzip of ONE JSON object with exactly these keys (extra keys are tolerated and ignored):

* ``schema``        the string :data:`SCHEMA`.
* ``meta``          ``{"corpus": str, "sourceFiles": int, "rejectedRows": int, "tracks": int,
                    "selectionEvents": int, "transitionEvents": int}``.
* ``artists``       list of canonical artist names (``str``). An artist's ID is its list position.
* ``tracks``        list of rows ``[key, title, artists, featured, variation, variationArtists]``: ``key`` and
                    ``title`` are ``str``; ``artists`` (primary), ``featured`` and ``variationArtists`` are lists of
                    artist IDs; ``variation`` is a ``str`` such as ``"REMIX"`` or ``null``. A track's ID is its list
                    position.
* ``selectorGroups`` list of rows ``[members, label, truncated]``: ``members`` is a list of artist IDs (the DJs of a
                    b2b credit decomposed into individuals), ``label`` is the credit as printed
                    (``"Dirt Monkey & Jantsen"``), ``truncated`` is ``0``/``1`` (``1`` when the credit ended in
                    ``+ More``, so ``members`` is an INCOMPLETE list). A group's ID is its list position.
* ``dates``         list of ``"YYYY-MM-DD"`` strings. A date's ID is its list position.
* ``selections``    list of rows ``[track, group, date]``: that group played that track in a set on that date. The
                    rows of one set are consecutive and in PLAY ORDER; a track may repeat inside a set.
* ``transitions``   list of rows ``[source, target, group, date]``: within a set the group played ``source`` and
                    then ``target`` back-to-back. They are exactly the consecutive pairs of that set's selections.

``date`` is an index into ``dates`` or ``-1`` meaning "the source file had no date"; the decoded records use ``None``
for ``-1``. A SET is the pair ``(group, date)``: one group's performance on one date. The real file has 54 sets.

Epistemic stance: this corpus is a SAMPLE (234 rows were rejected by the parser; some credits are truncated). A
pair of tracks that never appear together is therefore not known to be unrelated. Nothing in this module is
"closed world".
"""
from __future__ import annotations

import gzip
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from dsdk.core import Judgment, Part, PxC, Status

PINNED_SHA256 = "7e0b652aac543fbe89e80e8b47b5e7f0e67ac622ee20ae2426bd6d07492eb8a5"
"""SHA-256 of the reassembled gzip, as pinned in jukebox's ``.github/workflows/pages.yml``."""

SOURCE_REPO = "samuelpmahan/jukebox"
SOURCE_BRANCH = "lab/composable-mining"
SOURCE_COMMIT = "8b4d32b44217f8b4eb08977c9920a03194b2b1b2"
"""The branch tip the data was read from (``git show origin/lab/composable-mining:data/...part00..07``)."""

SCHEMA = "jukebox-primitives/v1"

FIXTURE_PATH = Path(__file__).resolve().parents[3] / "fixtures" / "worlds" / "lostlands-2018.jukebox.json.gz"
"""The vendored copy of the store (the default for :func:`load_lostlands`)."""

TOP_KEYS = ("meta", "artists", "tracks", "selectorGroups", "dates", "selections", "transitions")


class WorldError(ValueError):
    """The data is not a well-formed world (bad gzip/JSON, wrong schema, out-of-range index, wrong type...).

    The message names the offending field (and the row number for row errors) so a failure explains itself.
    """


class IntegrityError(WorldError):
    """The file's SHA-256 is not the expected one. The message contains BOTH the expected and the actual digest."""


@dataclass(frozen=True)
class Artist:
    id: int
    name: str


@dataclass(frozen=True)
class Track:
    """``artists`` / ``featured`` / ``variation_artists`` are tuples of artist IDs, in file order."""

    id: int
    key: str
    title: str
    artists: tuple[int, ...]
    featured: tuple[int, ...]
    variation: str | None
    variation_artists: tuple[int, ...]


@dataclass(frozen=True)
class SelectorGroup:
    """``members`` are artist IDs; ``truncated`` is True when the printed credit ended in ``+ More``."""

    id: int
    label: str
    members: tuple[int, ...]
    truncated: bool


@dataclass(frozen=True)
class Selection:
    """``group`` played ``track`` in its set on ``date`` (an index into ``LostLands.dates``, or ``None``)."""

    track: int
    group: int
    date: int | None


@dataclass(frozen=True)
class Transition:
    """``group`` played ``source`` then ``target`` back-to-back on ``date``."""

    source: int
    target: int
    group: int
    date: int | None


@dataclass(frozen=True)
class LostLands:
    """The decoded world. Every field is an immutable tuple/str so a world can be shared freely.

    ``sha256`` is the digest of the FILE the world was decoded from (``""`` when built by :func:`parse_lostlands`
    without one). ``meta`` is a plain dict copy of the file's ``meta`` object.
    """

    sha256: str
    meta: dict
    artists: tuple[Artist, ...]
    tracks: tuple[Track, ...]
    groups: tuple[SelectorGroup, ...]
    dates: tuple[str, ...]
    selections: tuple[Selection, ...]
    transitions: tuple[Transition, ...]

    def track_artists(self, track: int) -> str:
        """The primary artists' names of ``track`` joined with ``" & "`` in file order (``""`` if it has none).

        ``IndexError`` for a track ID outside ``range(len(tracks))`` (negative IDs included: no wrap-around).
        """
        t = self._track(track)
        return " & ".join(self.artists[a].name for a in t.artists)

    def _track(self, track: int) -> Track:
        if not _is_int(track) or not 0 <= track < len(self.tracks):
            raise IndexError(f"track {track!r} is outside range({len(self.tracks)})")
        return self.tracks[track]

    def track_label(self, track: int) -> str:
        """``"<track_artists> - <title>"``, plus ``" (<variation>)"`` when the track has a variation.

        Example: ``"Virtual Riot & 12th Planet - Codename X (REMIX)"``-style text. Featured artists are NOT in the
        label. Same ``IndexError`` rule as :meth:`track_artists`.
        """
        t = self._track(track)
        label = f"{self.track_artists(track)} - {t.title}"
        if t.variation is not None:
            label += f" ({t.variation})"
        return label

    def date_label(self, date: int | None) -> str | None:
        """``dates[date]``; ``None`` for ``None``. ``IndexError`` for any other out-of-range index."""
        if date is None:
            return None
        if not _is_int(date) or not 0 <= date < len(self.dates):
            raise IndexError(f"date {date!r} is outside range({len(self.dates)})")
        return self.dates[date]

    def sets(self) -> dict[tuple[int, int | None], tuple[int, ...]]:
        """Every set ``(group, date)`` mapped to its track IDs in play order (repeats kept).

        Keys are in FIRST-APPEARANCE order of ``selections``. The real world has 54 sets and 1,973 selections.
        """
        found: dict[tuple[int, int | None], list[int]] = {}
        for s in self.selections:
            found.setdefault((s.group, s.date), []).append(s.track)
        return {key: tuple(tracks) for key, tracks in found.items()}


def sha256_bytes(data: bytes) -> str:
    """Lower-case hex SHA-256 of ``data``."""
    return hashlib.sha256(data).hexdigest()


def _is_int(value: Any) -> bool:
    """An ``int`` that is not a ``bool`` (``bool`` is an ``int`` subclass in Python)."""
    return isinstance(value, int) and not isinstance(value, bool)


def _is_list(value: Any) -> bool:
    return isinstance(value, (list, tuple))


def _id(value: Any, bound: int, where: str) -> int:
    if not _is_int(value) or not 0 <= value < bound:
        raise WorldError(f"{where} must be an integer ID in range({bound}), got {value!r}")
    return value


def _ids(value: Any, bound: int, where: str) -> tuple[int, ...]:
    if not _is_list(value):
        raise WorldError(f"{where} must be a list of IDs, got {value!r}")
    return tuple(_id(x, bound, where) for x in value)


def _date(value: Any, bound: int, where: str) -> int | None:
    """``-1`` (no date) becomes ``None``; any other value must be an index into ``dates``."""
    if not _is_int(value) or not (value == -1 or 0 <= value < bound):
        raise WorldError(f"{where} must be -1 or an integer index in range({bound}), got {value!r}")
    return None if value == -1 else value





def parse_lostlands(doc: Mapping[str, Any], *, sha256: str = "") -> LostLands:
    """Decode and VALIDATE a JSON document (already parsed) into a :class:`LostLands`.

    Checks, in this order; the first violated one raises :class:`WorldError` (never ``KeyError``/``TypeError``):

    1. ``doc`` is a mapping whose ``schema`` equals :data:`SCHEMA`.
    2. every key of :data:`TOP_KEYS` is present (the message names the missing key).
    3. ``artists`` is a list of ``str``; ``dates`` is a list of ``str``.
    4. every ``tracks`` row has exactly 6 items of the documented types; every artist ID inside is in range.
       ``variation`` is ``None`` or ``str``. Messages say ``tracks[<row>]``.
    5. every ``selectorGroups`` row is ``[members, label, truncated]``; ``members`` IDs are in range; ``truncated``
       is ``0``/``1`` or ``False``/``True``.
    6. every ``selections`` row is 3 integers ``[track, group, date]`` and every ``transitions`` row is 4 integers
       ``[source, target, group, date]``; IDs in range; ``date`` is ``-1`` or in range. A ``bool`` is NEVER an
       integer here.
    7. ``meta`` is a mapping and ``meta["tracks"]``, ``meta["selectionEvents"]`` and ``meta["transitionEvents"]``
       equal the actual lengths (a missing or different count is a :class:`WorldError` naming the field).

    ``sha256`` is stored as given. IDs are list positions, so the order of the file is preserved exactly.
    """
    # 1. schema
    if not isinstance(doc, Mapping) or doc.get("schema") != SCHEMA:
        raise WorldError(f"schema must be {SCHEMA!r} in a JSON object")
    # 2. missing keys
    for key in TOP_KEYS:
        if key not in doc:
            raise WorldError(f"missing key {key!r}")
    # 3. artists and dates
    artists_doc = doc["artists"]
    if not _is_list(artists_doc) or not all(isinstance(x, str) for x in artists_doc):
        raise WorldError("artists must be a list of strings")
    dates_doc = doc["dates"]
    if not _is_list(dates_doc) or not all(isinstance(x, str) for x in dates_doc):
        raise WorldError("dates must be a list of strings")
    n_artists, n_dates = len(artists_doc), len(dates_doc)

    # 4. tracks
    tracks: list[Track] = []
    for i, row in enumerate(doc["tracks"]):
        where = f"tracks[{i}]"
        if not _is_list(row) or len(row) != 6:
            raise WorldError(f"{where} must be a list of 6 items")
        key, title, artists, featured, variation, variation_artists = row
        if not isinstance(key, str) or not isinstance(title, str):
            raise WorldError(f"{where}: key and title must be strings")
        if variation is not None and not isinstance(variation, str):
            raise WorldError(f"{where}: variation must be null or a string")
        tracks.append(Track(
            id=i,
            key=key,
            title=title,
            artists=_ids(artists, n_artists, f"{where}.artists"),
            featured=_ids(featured, n_artists, f"{where}.featured"),
            variation=variation,
            variation_artists=_ids(variation_artists, n_artists, f"{where}.variationArtists"),
        ))

    # 5. selector groups
    groups: list[SelectorGroup] = []
    for i, row in enumerate(doc["selectorGroups"]):
        where = f"selectorGroups[{i}]"
        if not _is_list(row) or len(row) != 3:
            raise WorldError(f"{where} must be a list of 3 items")
        members, label, truncated = row
        if not isinstance(label, str):
            raise WorldError(f"{where}.label must be a string")
        if isinstance(truncated, bool):
            flag = truncated
        elif _is_int(truncated) and truncated in (0, 1):
            flag = bool(truncated)
        else:
            raise WorldError(f"{where}.truncated must be 0, 1, false or true, got {truncated!r}")
        groups.append(SelectorGroup(
            id=i,
            label=label,
            members=_ids(members, n_artists, f"{where}.members"),
            truncated=flag,
        ))

    # 6. selections and transitions
    n_tracks, n_groups = len(tracks), len(groups)
    selections: list[Selection] = []
    for i, row in enumerate(doc["selections"]):
        where = f"selections[{i}]"
        if not _is_list(row) or len(row) != 3:
            raise WorldError(f"{where} must be a list of 3 integers")
        track, group, date = row
        selections.append(Selection(
            track=_id(track, n_tracks, f"{where}.track"),
            group=_id(group, n_groups, f"{where}.group"),
            date=_date(date, n_dates, f"{where}.date"),
        ))
    transitions: list[Transition] = []
    for i, row in enumerate(doc["transitions"]):
        where = f"transitions[{i}]"
        if not _is_list(row) or len(row) != 4:
            raise WorldError(f"{where} must be a list of 4 integers")
        source, target, group, date = row
        transitions.append(Transition(
            source=_id(source, n_tracks, f"{where}.source"),
            target=_id(target, n_tracks, f"{where}.target"),
            group=_id(group, n_groups, f"{where}.group"),
            date=_date(date, n_dates, f"{where}.date"),
        ))

    # 7. meta counts
    meta = doc["meta"]
    if not isinstance(meta, Mapping):
        raise WorldError("meta must be a JSON object")
    for field, actual in (("tracks", n_tracks), ("selectionEvents", len(selections)),
                          ("transitionEvents", len(transitions))):
        value = meta.get(field)
        if not _is_int(value) or value != actual:
            raise WorldError(f"meta.{field} must equal {actual}, got {value!r}")

    return LostLands(
        sha256=sha256,
        meta=dict(meta),
        artists=tuple(Artist(i, name) for i, name in enumerate(artists_doc)),
        tracks=tuple(tracks),
        groups=tuple(groups),
        dates=tuple(dates_doc),
        selections=tuple(selections),
        transitions=tuple(transitions),
    )


def load_lostlands(path: str | Path | None = None, *, expected_sha256: str | None = PINNED_SHA256) -> LostLands:
    """Read a ``.json.gz`` store, verify it and decode it with :func:`parse_lostlands`.

    * ``path=None`` means :data:`FIXTURE_PATH`. A missing file raises ``FileNotFoundError`` (not WorldError).
    * The SHA-256 of the RAW FILE BYTES is computed first. If ``expected_sha256`` is not ``None`` and differs
      (compare case-insensitively), raise :class:`IntegrityError` BEFORE decompressing anything. Pass
      ``expected_sha256=None`` to skip the check (the world's ``sha256`` is still the file's digest).
    * Bad gzip data (``OSError``/``EOFError`` from gzip) or invalid JSON/UTF-8 raises :class:`WorldError`; the
      message starts with ``"gzip:"`` or ``"json:"`` respectively.
    * On success ``world.sha256`` is the lower-case digest.
    """
    raw = (FIXTURE_PATH if path is None else Path(path)).read_bytes()
    digest = sha256_bytes(raw)
    if expected_sha256 is not None and digest != expected_sha256.lower():
        raise IntegrityError(f"sha256 mismatch: expected {expected_sha256.lower()}, got {digest}")
    try:
        text = gzip.decompress(raw)
    except (OSError, EOFError) as err:
        raise WorldError(f"gzip: {err}") from err
    try:
        doc = json.loads(text.decode("utf-8"))
    except ValueError as err:  # JSONDecodeError and UnicodeDecodeError are both ValueErrors
        raise WorldError(f"json: {err}") from err
    return parse_lostlands(doc, sha256=digest)


def check_transitions(world: LostLands) -> Judgment:
    """Do the ``transitions`` equal the consecutive pairs of each set's ``selections``? (the file's own invariant)

    * Consistent -> ``Judgment(Status.KNOWN, True, "transitions match the consecutive pairs of N sets")`` where
      ``N = len(world.sets())``.
    * Otherwise -> ``Judgment(Status.KNOWN, False, reason)`` for the FIRST bad set in first-appearance order of
      ``sets()``, with the reason EXACTLY ``f"set ({group}, {date}) has transitions that are not its consecutive
      pairs"`` (``date`` printed as the index or ``None``). If every set with selections is fine but some
      transition belongs to a ``(group, date)`` that has no selections, the reason is EXACTLY
      ``f"transition set ({group}, {date}) has no selections"`` (first such set in transition order).
    A set's expected pairs are ``list(zip(tracks, tracks[1:]))``; the transitions of a set are compared as an
    ORDERED list, in the order they appear in ``world.transitions``. KNOWN False is a real answer (we looked and it
    is inconsistent); this function never returns UNKNOWN.
    """
    sets = world.sets()
    actual: dict[tuple[int, int | None], list[tuple[int, int]]] = {}
    for t in world.transitions:
        actual.setdefault((t.group, t.date), []).append((t.source, t.target))
    for (group, date), tracks in sets.items():
        if actual.get((group, date), []) != list(zip(tracks, tracks[1:])):
            return Judgment(Status.KNOWN, False,
                            f"set ({group}, {date}) has transitions that are not its consecutive pairs")
    for t in world.transitions:
        if (t.group, t.date) not in sets:
            return Judgment(Status.KNOWN, False, f"transition set ({t.group}, {t.date}) has no selections")
    return Judgment(Status.KNOWN, True, f"transitions match the consecutive pairs of {len(sets)} sets")


def describe_provenance(values: Mapping[str, Any]) -> str:
    """The calculation behind ``px.lostlands.provenance``: ``values`` has ``sha256`` (str), ``commit`` (str) and
    ``counts`` (dict, see :func:`record_provenance`). Returns exactly::

        f"{counts['corpus']}: {counts['tracks']} tracks, {counts['artists']} artists, "
        f"{counts['selectorGroups']} selector groups, {counts['sets']} sets on {counts['dates']} dates, "
        f"{counts['selections']} selections, {counts['transitions']} transitions; "
        f"sha256 {sha256[:12]} @ {commit[:7]}"

    e.g. ``"lost-lands-2018: 1352 tracks, 817 artists, 50 selector groups, 54 sets on 8 dates, 1973 selections,
    1919 transitions; sha256 7e0b652aac54 @ 8b4d32b"`` (one line).
    """
    raise NotImplementedError


def record_provenance(world: LostLands, store: PxC | None = None) -> PxC:
    """Record where the world came from as dsdk.core Parts (and return the store).

    ``store=None`` creates a fresh :class:`dsdk.core.PxC`. Then, in this order (so receipts are reproducible):

    1. ``px.lostlands.source_sha256``  = ``Part(world.sha256)``
    2. ``px.lostlands.source_commit``  = ``Part(SOURCE_COMMIT)``
    3. ``px.lostlands.counts``         = ``Part(dict)`` with EXACTLY these keys in this order: ``corpus`` (meta's
       ``corpus``, or ``""`` if absent), ``artists``, ``tracks``, ``selectorGroups``, ``dates``, ``selections``,
       ``transitions`` (the lengths) and ``sets`` (``len(world.sets())``).
    4. ``fn.lostlands.describe``       = ``Part(describe_provenance)``
    5. ``px.lostlands.provenance``     = ``store.compose("px.lostlands.provenance", "fn.lostlands.describe",
       {"sha256": "px.lostlands.source_sha256", "commit": "px.lostlands.source_commit",
        "counts": "px.lostlands.counts"})`` (inputs in that order), so the provenance sentence has a real lineage
       DAG: ``dsdk.graph.lineage_graph`` of it has 5 nodes.

    Addresses are write-once: calling this twice on one store raises ``dsdk.core.AddressOccupiedError`` from the
    first ``set`` (nothing is overwritten). The world itself is not modified.
    """
    raise NotImplementedError

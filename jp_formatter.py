import argparse
import contextlib
import html
import io
import json
import re
import sqlite3
import sys
import unicodedata
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import quote
from typing import Any, Dict, List, Optional, Set, Tuple

from sudachipy import Dictionary, SplitMode


# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

DEFAULT_DB = BASE_DIR / "data" / "Main-dictonary.db"
DEFAULT_JMDICT = BASE_DIR / "data" / "JMdict.xml"
DEFAULT_CACHE = (
    BASE_DIR / "data" / "jmdict_reading_priority.json"
)

MAX_JMDICT_WORD_LENGTH = 12

# Rank given to a reading that has no JMdict priority at all.
NO_PRIORITY_RANK = 100000

# Bump this whenever the way ranks are computed changes. A cache
# written with a different version is thrown away and rebuilt.
CACHE_VERSION = 2

# Key under which the version is stored inside the cache file.
CACHE_META_KEY = "__meta__"


# ============================================================
# TERMINAL COLORS
# ============================================================

RESET = "\033[0m"
BOLD = "\033[1m"

CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BLUE = "\033[94m"
MAGENTA = "\033[95m"
WHITE = "\033[97m"


def enable_colors():
    if sys.platform == "win32":
        try:
            import os
            os.system("")
        except Exception:
            pass

    for stream in (sys.stdin, sys.stdout, sys.stderr):
        try:
            stream.reconfigure(
                encoding="utf-8",
                errors="replace",
            )
        except (AttributeError, OSError):
            pass


def info(text: str):
    print(f"{CYAN}[INFO]{RESET} {text}")


def ok(text: str):
    print(f"{GREEN}[OK]{RESET} {text}")


def warning(text: str):
    print(f"{YELLOW}[WARNING]{RESET} {text}")


def error(text: str):
    print(f"{RED}[ERROR]{RESET} {text}")


# ============================================================
# JAPANESE HELPERS
# ============================================================

def katakana_to_hiragana(text: str) -> str:
    result = []

    for char in text:
        code = ord(char)

        if 0x30A1 <= code <= 0x30F6:
            result.append(
                chr(code - 0x60)
            )
        else:
            result.append(char)

    return "".join(result)


def normalize_text(text: str) -> str:
    return unicodedata.normalize(
        "NFKC",
        text,
    )


def is_kanji(char: str) -> bool:
    code = ord(char)

    return (
        0x3400 <= code <= 0x4DBF
        or 0x4E00 <= code <= 0x9FFF
        or 0xF900 <= code <= 0xFAFF
        # Iteration mark 々, closing mark 〆 and the ideographic
        # zero 〇 are written like kanji and are read like kanji
        # (広々 = ひろびろ), so they must count as kanji.
        or 0x3005 <= code <= 0x3007
    )


def contains_kanji(text: str) -> bool:
    return any(
        is_kanji(char)
        for char in text
    )


def is_kana_only(text: str) -> bool:
    if not text:
        return False

    for char in text:

        code = ord(char)

        if (
            0x3040 <= code <= 0x309F
            or 0x30A0 <= code <= 0x30FF
            or char in "ー"
        ):
            continue

        return False

    return True


# ============================================================
# JAPANESE PARTICLES
# ============================================================

PARTICLES = {
    "は",
    "が",
    "を",
    "に",
    "へ",
    "で",
    "と",
    "も",
    "の",
    "から",
    "まで",
    "より",
    "だけ",
    "しか",
    "ほど",
    "くらい",
    "ぐらい",
    "ばかり",
    "など",
    "なり",
    "や",
    "か",
    "ね",
    "よ",
    "ぞ",
    "さ",
    "わ",
    "って",
}


# ============================================================
# POS
# ============================================================

POS_MAP = {
    "名詞": "Noun",
    "動詞": "Verb",
    "形容詞": "Adjective",
    "副詞": "Adverb",
    "連体詞": "Adnominal",
    "接続詞": "Conjunction",
    "感動詞": "Interjection",
    "助詞": "Particle",
    "助動詞": "Auxiliary",
    "代名詞": "Pronoun",
    "接頭辞": "Prefix",
    "接尾辞": "Suffix",
    "記号": None,
    "補助記号": None,
    "フィラー": None,
    "その他": "Other",
}


def map_pos(
    pos: List[str],
    surface: str,
) -> Optional[str]:
    """
    Convert Sudachi POS into the simpler labels used by the
    JSON output.

    There are some important overrides here because Jisho's
    sentence breakdown is not simply the first Sudachi POS field.

    Example:
        静寂 may be 名詞-...-副詞可能
        -> Adverb

        に
        -> Particle
    """

    # --------------------------------------------------------
    # Explicit particle override
    # --------------------------------------------------------

    if surface in PARTICLES:
        return "Particle"

    if not pos:
        return None

    # --------------------------------------------------------
    # Sudachi sometimes identifies things like 静寂 as a noun
    # with an adverb-compatible subcategory.
    # --------------------------------------------------------

    if "副詞可能" in pos:
        return "Adverb"

    # --------------------------------------------------------
    # Main POS
    # --------------------------------------------------------

    return POS_MAP.get(
        pos[0],
        pos[0],
    )


# ============================================================
# JMdict PRIORITY INDEX
# ============================================================

class JMdictPriorityIndex:

    def __init__(
        self,
        xml_path: Path,
        cache_path: Path,
    ):

        self.xml_path = xml_path
        self.cache_path = cache_path

        self.data: Dict[
            str,
            Dict[str, Any]
        ] = {}

    # --------------------------------------------------------
    # Priority
    # --------------------------------------------------------

    @staticmethod
    def priority_rank(
        codes: List[str]
    ) -> int:

        if not codes:
            return NO_PRIORITY_RANK

        best = NO_PRIORITY_RANK

        for code in codes:

            if code in {
                "news1",
                "ichi1",
                "spec1",
                "gai1",
            }:

                best = min(
                    best,
                    1,
                )

            elif code in {
                "news2",
                "ichi2",
                "spec2",
                "gai2",
            }:

                best = min(
                    best,
                    10,
                )

            elif code.startswith("nf"):

                try:

                    number = int(
                        code[2:]
                    )

                    best = min(
                        best,
                        100 + number,
                    )

                except ValueError:
                    pass

        return best

    # --------------------------------------------------------
    # Load cache
    # --------------------------------------------------------

    def load(self):

        if self.cache_path.exists():

            try:

                info(
                    "Loading JMdict reading priorities..."
                )

                with open(
                    self.cache_path,
                    "r",
                    encoding="utf-8",
                ) as file:

                    data = json.load(
                        file
                    )

                meta = (
                    data.get(CACHE_META_KEY)
                    if isinstance(data, dict)
                    else None
                )

                if (
                    isinstance(meta, dict)
                    and meta.get("version")
                    == CACHE_VERSION
                ):

                    self.data = data

                    ok(
                        f"Loaded {len(self.data) - 1:,} "
                        "JMdict reading records."
                    )

                    return

                # Cache was written by an older version of this
                # script (different ranking rules). Rebuild it.
                warning(
                    "JMdict priority cache is outdated; "
                    "rebuilding it."
                )

            except Exception as exc:

                warning(
                    "Could not load JMdict priority cache."
                )

                warning(
                    str(exc)
                )

        self.build()

    # --------------------------------------------------------
    # Build cache
    # --------------------------------------------------------

    def build(self):

        # Never keep stale data around.
        self.data = {}

        if not self.xml_path.exists():

            warning(
                f"JMdict XML not found:"
            )

            warning(
                f"    {self.xml_path.resolve()}"
            )

            warning(
                "Reading priorities disabled."
            )

            return

        info(
            "Building JMdict reading-priority cache..."
        )

        info(
            "This only needs to happen once."
        )

        count = 0

        context = ET.iterparse(
            self.xml_path,
            events=("end",),
        )

        for _, entry in context:

            if entry.tag != "entry":
                continue

            kanji_forms = []

            for keb in entry.findall(
                "k_ele"
            ):

                text = keb.findtext(
                    "keb"
                )

                if not text:
                    continue

                priorities = [
                    item.text
                    for item in keb.findall(
                        "ke_pri"
                    )
                    if item.text
                ]

                kanji_forms.append(
                    {
                        "text": text,
                        "priority": priorities,
                    }
                )

            # ------------------------------------------------
            # Collect every reading of the entry first, so we
            # know whether the entry marks any reading as
            # common before ranking the individual readings.
            # ------------------------------------------------

            entry_readings = []

            for reb in entry.findall(
                "r_ele"
            ):

                reading = reb.findtext(
                    "reb"
                )

                if not reading:
                    continue

                priorities = [
                    item.text
                    for item in reb.findall(
                        "re_pri"
                    )
                    if item.text
                ]

                restrictions = [
                    item.text
                    for item in reb.findall(
                        "re_restr"
                    )
                    if item.text
                ]

                entry_readings.append(
                    {
                        "text": reading,
                        "priority": priorities,
                        "restrictions": restrictions,
                        "rank": self.priority_rank(
                            priorities
                        ),
                    }
                )

            entry_has_common_reading = any(
                item["rank"] < NO_PRIORITY_RANK
                for item in entry_readings
            )

            for item in entry_readings:

                reading = item["text"]
                priorities = item["priority"]
                restrictions = item["restrictions"]
                reading_rank = item["rank"]

                if restrictions:

                    applicable_forms = [
                        form
                        for form in kanji_forms
                        if form["text"]
                        in restrictions
                    ]

                else:

                    applicable_forms = (
                        kanji_forms
                    )

                for form in applicable_forms:

                    key = (
                        form["text"]
                        + "\t"
                        + reading
                    )

                    form_rank = (
                        self.priority_rank(
                            form["priority"]
                        )
                    )

                    # ----------------------------------------
                    # A reading must NOT inherit the priority
                    # of the kanji form when it has none of
                    # its own while a sibling reading does.
                    #
                    # Example: 言う is common as いう, but also
                    # has an uncommon reading ゆう. Both belong
                    # to the same (common) kanji form, so
                    # taking min(reading, form) made them tie
                    # and the analyzer's own reading (ゆう) won.
                    # ----------------------------------------

                    if reading_rank < NO_PRIORITY_RANK:

                        combined_rank = min(
                            reading_rank,
                            form_rank,
                        )

                    elif entry_has_common_reading:

                        combined_rank = (
                            NO_PRIORITY_RANK
                        )

                    else:

                        # Nothing marks a reading as common in
                        # this entry, so fall back to the form.
                        combined_rank = form_rank

                    existing = self.data.get(
                        key
                    )

                    if (
                        existing is None
                        or combined_rank
                        < existing["rank"]
                    ):

                        self.data[key] = {
                            "rank":
                                combined_rank,

                            "priority":
                                priorities,
                        }

            count += 1

            if count % 10000 == 0:

                print(
                    f"\r    Processed "
                    f"{count:,} JMdict entries...",
                    end="",
                    flush=True,
                )

            entry.clear()

        print()

        ok(
            f"Processed {count:,} JMdict entries."
        )

        self.data[CACHE_META_KEY] = {
            "version": CACHE_VERSION,
        }

        try:

            self.cache_path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            with open(
                self.cache_path,
                "w",
                encoding="utf-8",
            ) as file:

                json.dump(
                    self.data,
                    file,
                    ensure_ascii=False,
                    separators=(",", ":"),
                )

            ok(
                f"Saved cache to "
                f"{self.cache_path.resolve()}"
            )

        except Exception as exc:

            warning(
                "Could not save cache."
            )

            warning(
                str(exc)
            )

    # --------------------------------------------------------
    # Get priority
    # --------------------------------------------------------

    def get(
        self,
        word: str,
        reading: str,
    ) -> Optional[Dict[str, Any]]:

        return self.data.get(
            word + "\t" + reading
        )

    # --------------------------------------------------------
    # Select reading
    # --------------------------------------------------------

    def choose(
        self,
        word: str,
        readings: List[str],
        fallback: str,
    ) -> Optional[str]:

        if not readings:

            return (
                fallback
                if fallback
                else None
            )

        candidates = []

        for reading in readings:

            priority = self.get(
                word,
                reading,
            )

            if priority:

                rank = priority[
                    "rank"
                ]

            else:

                rank = NO_PRIORITY_RANK

            # Prefer exact Sudachi reading if priority is tied.
            sudachi_penalty = (
                0
                if reading == fallback
                else 1
            )

            candidates.append(
                (
                    rank,
                    sudachi_penalty,
                    reading,
                )
            )

        candidates.sort()

        return candidates[0][2]


# ============================================================
# DATABASE
# ============================================================

def validate_database(
    connection: sqlite3.Connection,
):

    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
        """
    )

    tables = {
        row[0]
        for row in cursor.fetchall()
    }

    required = {
        "entries",
        "kanji_forms",
        "readings",
        "senses",
        "glosses",
    }

    missing = required - tables

    if missing:

        raise RuntimeError(
            "Database is missing tables: "
            + ", ".join(
                sorted(missing)
            )
        )

    connection.executescript(
        """
        CREATE INDEX IF NOT EXISTS idx_senses_entry_number
        ON senses(entry_id, sense_number);

        CREATE INDEX IF NOT EXISTS idx_glosses_sense_language
        ON glosses(sense_id, language);
        """
    )


def load_jmdict_headwords(
    connection: sqlite3.Connection,
) -> Set[str]:

    info(
        "Loading JMdict headwords from SQLite..."
    )

    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT DISTINCT text
        FROM kanji_forms
        """
    )

    headwords = {
        row[0]
        for row in cursor.fetchall()
        if row[0]
    }

    ok(
        f"Loaded {len(headwords):,} unique headwords."
    )

    return headwords


def get_word_readings(
    connection: sqlite3.Connection,
    word: str,
) -> List[str]:

    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT DISTINCT text
        FROM readings
        WHERE entry_id IN (
            SELECT entry_id
            FROM kanji_forms
            WHERE text = ?
        )
        ORDER BY id
        """,
        (word,),
    )

    return [
        row[0]
        for row in cursor.fetchall()
    ]


def get_meaning(
    connection: sqlite3.Connection,
    word: str,
    dictionary_forms: List[str],
) -> Optional[str]:

    cursor = connection.cursor()

    # --------------------------------------------------------
    # Try exact word first
    # --------------------------------------------------------

    search_words = [
        word,
        *dictionary_forms,
    ]

    # Preserve order and remove duplicates.
    search_words = list(
        dict.fromkeys(
            value
            for value in search_words
            if value
        )
    )

    for search_word in search_words:

        cursor.execute(
            """
            SELECT entry_id
            FROM kanji_forms
            WHERE text = ?
            ORDER BY entry_id
            LIMIT 1
            """,
            (search_word,),
        )

        row = cursor.fetchone()

        if row is None:
            continue

        entry_id = row[0]

        # ----------------------------------------------------
        # English gloss
        # ----------------------------------------------------

        cursor.execute(
            """
            SELECT g.text
            FROM senses s
            JOIN glosses g
                ON g.sense_id = s.id
            WHERE s.entry_id = ?
              AND g.language = 'eng'
            ORDER BY
                s.sense_number,
                g.id
            LIMIT 1
            """,
            (entry_id,),
        )

        meaning_row = cursor.fetchone()

        if meaning_row:

            return meaning_row[0]

    return None


# ============================================================
# RAW SUDACHI TOKEN
# ============================================================

def token_info(
    morpheme: Any,
) -> Dict[str, Any]:

    surface = morpheme.surface()

    reading = (
        morpheme.reading_form()
    )

    if reading:

        reading = katakana_to_hiragana(
            reading
        )

    # --------------------------------------------------------
    # Kana-only morphemes normally have no furigana, but they
    # still need to contribute their own kana when part of a
    # conjugated word.
    # --------------------------------------------------------

    if not reading and is_kana_only(
        surface
    ):

        reading = surface

    dictionary_form = (
        morpheme.dictionary_form()
    )

    pos = list(
        morpheme.part_of_speech()
    )

    return {
        "surface":
            surface,

        "reading":
            reading,

        "dictionary_form":
            dictionary_form,

        "pos":
            map_pos(
                pos,
                surface,
            ),

        "pos_raw":
            pos,
    }


# ============================================================
# JMDICT LONG-WORD MERGING
# ============================================================

def merge_dictionary_words(
    tokens: List[Dict[str, Any]],
    headwords: Set[str],
) -> List[Dict[str, Any]]:

    result = []

    i = 0

    while i < len(tokens):

        # ----------------------------------------------------
        # Find the longest dictionary headword beginning at
        # this token.
        # ----------------------------------------------------

        best_end = None
        best_word = None

        combined = ""

        max_end = min(
            len(tokens),
            i + MAX_JMDICT_WORD_LENGTH,
        )

        for j in range(
            i,
            max_end,
        ):

            combined += tokens[j][
                "surface"
            ]

            if combined in headwords:

                if (
                    best_word is None
                    or len(combined)
                    > len(best_word)
                ):

                    best_word = combined
                    best_end = j + 1

        # ----------------------------------------------------
        # Only use the dictionary merge when it actually
        # combines multiple analyzer tokens.
        # ----------------------------------------------------

        if (
            best_word
            and best_end is not None
            and best_end > i + 1
        ):

            group = tokens[
                i:best_end
            ]

            result.append(
                {
                    "surface":
                        best_word,

                    "reading":
                        "".join(
                            token["reading"]
                            for token in group
                            if token["reading"]
                        ),

                    "dictionary_forms":
                        list(
                            dict.fromkeys(
                                token[
                                    "dictionary_form"
                                ]
                                for token in group
                                if token[
                                    "dictionary_form"
                                ]
                            )
                        ),

                    "pos":
                        group[0]["pos"],

                    "source":
                        "jmdict_merge",
                }
            )

            i = best_end

            continue

        # ----------------------------------------------------
        # Normal token
        # ----------------------------------------------------

        result.append(
            {
                "surface":
                    tokens[i][
                        "surface"
                    ],

                "reading":
                    tokens[i][
                        "reading"
                    ],

                "dictionary_forms":
                    [
                        tokens[i][
                            "dictionary_form"
                        ]
                    ]
                    if tokens[i][
                        "dictionary_form"
                    ]
                    else [],

                "pos":
                    tokens[i]["pos"],

                "source":
                    "sudachi",
            }
        )

        i += 1

    return result


# ============================================================
# CONJUGATION MERGING
# ============================================================

def merge_conjugations(
    tokens: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:

    result = []

    i = 0

    while i < len(tokens):

        current = tokens[i]

        # ====================================================
        # Verb + auxiliary chain
        #
        # 漂っ + た
        # 食べ + て + い + ます
        # 読ん + で + い + る
        # ====================================================

        if current["pos"] == "Verb":

            group = [
                current
            ]

            j = i + 1

            while j < len(tokens):

                next_token = tokens[j]

                next_pos = (
                    next_token["pos"]
                )

                surface = (
                    next_token["surface"]
                )

                if (
                    next_pos == "Auxiliary"
                    or surface in {
                        "た",
                        "だ",
                        "て",
                        "で",
                        "ない",
                        "なかっ",
                        "なかった",
                        "いる",
                        "い",
                        "ます",
                        "まし",
                        "ました",
                        "ません",
                        "ませんでした",
                        "られる",
                        "させる",
                        "たい",
                        "たく",
                        "ない",
                    }
                ):

                    group.append(
                        next_token
                    )

                    j += 1

                    continue

                break

            if len(group) > 1:

                result.append(
                    {
                        "surface":
                            "".join(
                                token["surface"]
                                for token in group
                            ),

                        "reading":
                            "".join(
                                token["reading"]
                                for token in group
                                if token["reading"]
                            ),

                        "dictionary_forms":
                            [
                                current[
                                    "dictionary_forms"
                                ][0]
                            ]
                            if current[
                                "dictionary_forms"
                            ]
                            else [],

                        "pos":
                            "Verb",

                        "source":
                            "verb_conjugation",
                    }
                )

                i = j

                continue

        # ====================================================
        # Noun + し + て + い + ます
        #
        # 勉強しています
        # ====================================================

        if (
            current["pos"] == "Noun"
            and i + 4 < len(tokens)
        ):

            next_four = tokens[
                i + 1:i + 5
            ]

            surfaces = [
                token["surface"]
                for token in next_four
            ]

            if surfaces == [
                "し",
                "て",
                "い",
                "ます",
            ]:

                group = [
                    current,
                    *next_four,
                ]

                result.append(
                    {
                        "surface":
                            "".join(
                                token["surface"]
                                for token in group
                            ),

                        "reading":
                            "".join(
                                token["reading"]
                                for token in group
                                if token["reading"]
                            ),

                        "dictionary_forms":
                            current[
                                "dictionary_forms"
                            ],

                        "pos":
                            "Verb",

                        "source":
                            "suru_conjugation",
                    }
                )

                i += 5

                continue

        # ----------------------------------------------------
        # Normal
        # ----------------------------------------------------

        result.append(
            current
        )

        i += 1

    return result


# ============================================================
# POS REFINEMENT
# ============================================================

def refine_pos(
    token: Dict[str, Any],
) -> Optional[str]:

    surface = token[
        "surface"
    ]

    # --------------------------------------------------------
    # Particles
    # --------------------------------------------------------

    if surface in PARTICLES:

        return "Particle"

    # --------------------------------------------------------
    # Already determined
    # --------------------------------------------------------

    pos = token[
        "pos"
    ]

    if pos:

        return pos

    return None


# ============================================================
# PRONUNCIATION
# ============================================================

def choose_pronunciation(
    connection: sqlite3.Connection,
    priority_index: JMdictPriorityIndex,
    word: str,
    fallback: str,
) -> Optional[str]:

    # Kana-only words have no furigana requirement.
    if not contains_kanji(word):

        return None

    readings = get_word_readings(
        connection,
        word,
    )

    # --------------------------------------------------------
    # Exact JMdict word
    # --------------------------------------------------------

    if readings:

        selected = (
            priority_index.choose(
                word=word,
                readings=readings,
                fallback=fallback,
            )
        )

        if selected:

            return selected

    # --------------------------------------------------------
    # Fallback to analyzer
    # --------------------------------------------------------

    return fallback or None


# ============================================================
# ANALYZE
# ============================================================

def analyze_sentence(
    text: str,
    connection: sqlite3.Connection,
    priority_index: JMdictPriorityIndex,
    headwords: Set[str],
) -> List[Dict[str, Any]]:

    print()
    print("=" * 70)
    print("STARTING SUDACHI")
    print("=" * 70)

    sudachi_dictionary = Dictionary(
        dict="core"
    )

    tokenizer = (
        sudachi_dictionary.tokenizer(
            mode=SplitMode.C
        )
    )

    ok(
        "Sudachi loaded."
    )

    # --------------------------------------------------------
    # Tokenize
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print("RAW TOKENIZATION")
    print("=" * 70)

    info(
        f"Input: {text}"
    )

    morphemes = tokenizer.tokenize(
        text
    )

    raw_tokens = [
        token_info(
            morpheme
        )
        for morpheme in morphemes
        if morpheme.surface()
    ]

    print()

    for index, token in enumerate(
        raw_tokens
    ):

        print(
            f"[{index}] "
            f"{token['surface']} "
            f"-> "
            f"{token['reading']} "
            f"-> "
            f"{token['pos']}"
        )

    # --------------------------------------------------------
    # Dictionary merge
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print("JMdict WORD MATCHING")
    print("=" * 70)

    merged = merge_dictionary_words(
        raw_tokens,
        headwords,
    )

    for index, token in enumerate(
        merged
    ):

        if token["source"] == "jmdict_merge":

            print(
                f"{GREEN}"
                f"[MERGE] "
                f"{token['surface']}"
                f"{RESET}"
                f" <- JMdict"
            )

    ok(
        f"Dictionary stage produced "
        f"{len(merged)} tokens."
    )

    # --------------------------------------------------------
    # Conjugations
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print("CONJUGATION MERGING")
    print("=" * 70)

    grouped = merge_conjugations(
        merged
    )

    for index, token in enumerate(
        grouped
    ):

        if token["source"] in {
            "verb_conjugation",
            "suru_conjugation",
        }:

            print(
                f"{GREEN}"
                f"[MERGE] "
                f"{token['surface']}"
                f"{RESET}"
                f" <- conjugation"
            )

    ok(
        f"Final token count: "
        f"{len(grouped)}"
    )

    # --------------------------------------------------------
    # Final dictionary lookup
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print("FINAL DICTIONARY LOOKUP")
    print("=" * 70)

    results = []
    pronunciation_cache: Dict[Tuple[str, Optional[str]], Optional[str]] = {}
    meaning_cache: Dict[Tuple[str, Tuple[str, ...]], Optional[str]] = {}

    for index, token in enumerate(
        grouped
    ):

        word = token[
            "surface"
        ]

        fallback_reading = token[
            "reading"
        ]

        dictionary_forms = token[
            "dictionary_forms"
        ]

        # ----------------------------------------------------
        # Special case:
        #
        # For a verb in conjugated form, dictionary_forms
        # should contain its lemma.
        # ----------------------------------------------------

        pronunciation_key = (word, fallback_reading)
        if pronunciation_key not in pronunciation_cache:
            pronunciation_cache[pronunciation_key] = choose_pronunciation(
                connection=connection,
                priority_index=priority_index,
                word=word,
                fallback=fallback_reading,
            )
        pronunciation = pronunciation_cache[pronunciation_key]

        # ----------------------------------------------------
        # Meaning lookup
        # ----------------------------------------------------

        lookup_forms = list(
            dictionary_forms
        )

        # ----------------------------------------------------
        # For compound suru verbs:
        #
        # 勉強しています
        #
        # try:
        #
        # 勉強
        #
        # as well.
        # ----------------------------------------------------

        meaning_key = (word, tuple(lookup_forms))
        if meaning_key not in meaning_cache:
            meaning_cache[meaning_key] = get_meaning(
                connection=connection,
                word=word,
                dictionary_forms=lookup_forms,
            )
        meaning = meaning_cache[meaning_key]

        # ----------------------------------------------------
        # POS
        # ----------------------------------------------------

        pos = refine_pos(
            token
        )

        result = {
            "index":
                index,

            "word":
                word,

            "reading":
                pronunciation,

            "pos":
                pos,

            "meaning":
                meaning,
        }

        results.append(
            result
        )

        # ----------------------------------------------------
        # Console
        # ----------------------------------------------------

        print()
        print(
            f"{BOLD}{WHITE}"
            f"[{index}] {word}"
            f"{RESET}"
        )

        print(
            f"    Reading: "
            f"{GREEN}"
            f"{pronunciation or '-'}"
            f"{RESET}"
        )

        print(
            f"    POS: "
            f"{YELLOW}"
            f"{pos or '-'}"
            f"{RESET}"
        )

        print(
            f"    Meaning: "
            f"{meaning or '-'}"
        )

        print(
            f"    Source: "
            f"{token['source']}"
        )

    return results


# ============================================================
# JSON
# ============================================================

def save_json(
    data: List[Dict[str, Any]],
    output: Path,
):

    output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with open(
        output,
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=2,
        )


# ============================================================
# HTML RENDERING  (ported from api.php)
# ============================================================

# CJK ideographs + compatibility ideographs, plus the iteration
# mark 々 (U+3005), 〆 (U+3006) and 〇 (U+3007). Without 々 a word
# like 広々 is split into 広 + "々とした", which breaks the
# furigana alignment.
_KANJI_CLASS = "\u3400-\u9fff\uf900-\ufaff\u3005\u3006\u3007"
_KANJI_RE = re.compile(f"[{_KANJI_CLASS}]")
_KANJI_RUN_RE = re.compile(f"([{_KANJI_CLASS}]+)")


def escape_html(value: str) -> str:
    """Same output as PHP htmlspecialchars(ENT_QUOTES | ENT_SUBSTITUTE)."""
    return html.escape(value, quote=True).replace("&#x27;", "&#039;")


def html_contains_kanji(value: str) -> bool:
    return _KANJI_RE.search(value) is not None


def render_word_parts(
    word: str,
    reading: Optional[str],
) -> Tuple[str, str]:
    """
    Returns (furigana_html, text_html) for one token.

    Kanji runs get the matching slice of the reading as furigana.
    Kana between kanji (okurigana) is used as an anchor to find
    where each kanji run's reading ends.
    """

    if reading is None or not html_contains_kanji(word):
        return "", escape_html(word)

    parts = [
        part
        for part in _KANJI_RUN_RE.split(word)
        if part
    ]

    furigana = ""
    text = ""
    reading_offset = 0

    for part_index, part in enumerate(parts):

        if html_contains_kanji(part):

            next_kana = ""

            if (
                part_index + 1 < len(parts)
                and not html_contains_kanji(parts[part_index + 1])
            ):
                next_kana = parts[part_index + 1]

            furigana_text = reading[reading_offset:]

            if next_kana:

                match = re.compile(
                    r"(.*?)" + re.escape(next_kana)
                ).match(
                    reading,
                    reading_offset,
                )

                if match:
                    furigana_text = match.group(1)

            reading_offset += len(furigana_text)

            furigana += (
                '<span class="japanese_word__furigana" '
                f'data-text="{escape_html(part)}">'
                f"{escape_html(furigana_text)}</span>"
            )

            text += (
                '<span class="japanese_word__text_with_furigana">'
                f"{escape_html(part)}</span>"
            )

            continue

        furigana += (
            '<span class="japanese_word__furigana '
            "japanese_word__furigana-invisible "
            'japanese_word__furigana-invisible__last" data-text="">'
            f"{escape_html(part)}</span>"
        )

        text += (
            '<span class="japanese_word__text_without_furigana">'
            f"{escape_html(part)}</span>"
        )

        reading_offset += len(part)

    return furigana, text


def render_token_section(
    tokens: List[Dict[str, Any]],
) -> str:

    lines = [
        '<section id="zen_bar" class="japanese_gothic focus" lang="ja">',
        '    <ul class="clearfix">',
    ]

    for token_index, token in enumerate(tokens):

        word = str(token.get("word") or "")

        reading = token.get("reading")
        if not isinstance(reading, str):
            reading = None

        part_of_speech = token.get("pos")

        furigana, word_text = render_word_parts(
            word,
            reading,
        )

        pos_attributes = ""

        if part_of_speech is not None:
            pos_html = escape_html(str(part_of_speech))
            pos_attributes = (
                f' data-pos="{pos_html}" title="{pos_html}"'
            )

        css_class = "current" if token_index == 0 else ""

        anchor_open = (
            f'<a data-word="{escape_html(word)}" '
            f'class="{css_class}" '
            f'href="/search/{quote(word, safe="")}">'
        )

        if furigana == "":
            anchor = f"{anchor_open}{word_text}</a>"
        else:
            anchor = f"{anchor_open}\n{word_text}\n</a>"

        lines.extend(
            [
                f'        <li class="clearfix japanese_word"{pos_attributes} '
                'data-tooltip-direction="bottom" '
                'data-tooltip-color="black" '
                'data-tooltip-margin="10">',
                '            <span class="japanese_word__furigana_wrapper">'
                f"{furigana}</span>",
                '            <span class="japanese_word__text_wrapper">'
                f"{anchor}</span>",
                "        </li>",
            ]
        )

    lines.extend(
        [
            "    </ul>",
            "</section>",
        ]
    )

    return "\n".join(lines)


# ============================================================
# PUBLIC API
# ============================================================

def format_to_html(
    text: str,
    db: Path = DEFAULT_DB,
    jmdict: Path = DEFAULT_JMDICT,
    cache: Path = DEFAULT_CACHE,
    output: Optional[Path] = None,
    json_output: Optional[Path] = None,
    verbose: bool = False,
) -> str:
    """
    Analyze one Japanese sentence and return the rendered HTML.

    This is the main programmatic API. It can be imported from another
    Python program without going through argparse or the command line.

    Parameters
    ----------
    text:
        Japanese sentence to analyze.

    db:
        SQLite dictionary database.

    jmdict:
        JMdict XML file.

    cache:
        JMdict reading-priority cache.

    output:
        Optional path where the rendered HTML should also be saved.

    json_output:
        Optional path where the raw analysis JSON should also be saved.

    verbose:
        If True, show analyzer diagnostic output on stderr.

    Returns
    -------
    str
        The rendered HTML word bar.

    Raises
    ------
    FileNotFoundError
        If the SQLite database does not exist.

    Exception
        Any exception raised while loading the dictionaries or analyzing
        the sentence is allowed to propagate to the caller.
    """

    if not text or not text.strip():
        raise ValueError("No input text.")

    db = Path(db)
    jmdict = Path(jmdict)
    cache = Path(cache)

    if not db.exists():
        raise FileNotFoundError(
            f"Database not found: {db.resolve()}"
        )

    # Analyzer chatter goes to stderr when verbose, or is discarded
    # when called programmatically without verbose output.
    quiet_stream = sys.stderr if verbose else io.StringIO()

    with contextlib.redirect_stdout(quiet_stream):
        connection = sqlite3.connect(db)

        try:
            validate_database(connection)
            headwords = load_jmdict_headwords(connection)

            priority_index = JMdictPriorityIndex(
                xml_path=jmdict,
                cache_path=cache,
            )
            priority_index.load()

            results = analyze_sentence(
                text=text.strip(),
                connection=connection,
                priority_index=priority_index,
                headwords=headwords,
            )

            if json_output:
                save_json(results, Path(json_output))

            rendered = render_token_section(results)

        finally:
            connection.close()

    if output:
        output = Path(output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")

    return rendered


# ============================================================
# MAIN / CLI
# ============================================================

def main() -> int:

    enable_colors()

    parser = argparse.ArgumentParser(
        description=(
            "Japanese sentence analyzer (Sudachi + JMdict + SQLite) "
            "that prints the formatted HTML word bar."
        )
    )

    parser.add_argument(
        "text",
        nargs="?",
        help="Japanese sentence (omit to be prompted interactively)",
    )

    parser.add_argument(
        "--stdin",
        action="store_true",
        help="Read Japanese text from standard input",
    )

    parser.add_argument(
        "--db",
        type=Path,
        default=DEFAULT_DB,
        help="Main dictionary database",
    )

    parser.add_argument(
        "--jmdict",
        type=Path,
        default=DEFAULT_JMDICT,
        help="JMdict XML",
    )

    parser.add_argument(
        "--cache",
        type=Path,
        default=DEFAULT_CACHE,
        help="JMdict priority cache",
    )

    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=None,
        help="Also save the HTML to this file",
    )

    parser.add_argument(
        "--json-output",
        type=Path,
        default=None,
        help="Also save the raw analysis JSON to this file",
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show the analyzer's step-by-step log (sent to stderr)",
    )

    args = parser.parse_args()

    def fail(message: str) -> int:
        print(f"{RED}[ERROR]{RESET} {message}", file=sys.stderr)
        return 1

    try:

        # One-shot mode: text from argument or stdin
        if args.stdin or args.text:

            text = (
                sys.stdin.read()
                if args.stdin
                else args.text
            ).strip()

            if not text:
                return fail("No input text.")

            print(
                format_to_html(
                    text=text,
                    db=args.db,
                    jmdict=args.jmdict,
                    cache=args.cache,
                    output=args.output,
                    json_output=args.json_output,
                    verbose=args.verbose,
                )
            )

        # Interactive mode: keep prompting until an empty line
        else:

            print(
                "Enter Japanese text "
                "(empty line or Ctrl+D to quit).",
                file=sys.stderr,
            )

            while True:

                try:
                    text = input("> ").strip()
                except EOFError:
                    break

                if not text:
                    break

                try:
                    print()
                    print(
                        format_to_html(
                            text=text,
                            db=args.db,
                            jmdict=args.jmdict,
                            cache=args.cache,
                            output=args.output,
                            json_output=args.json_output,
                            verbose=args.verbose,
                        )
                    )
                    print()

                except Exception as exc:
                    fail(f"Analysis failed: {exc}")

    except Exception as exc:
        return fail(f"Analysis failed: {exc}")

    return 0


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    sys.exit(main())

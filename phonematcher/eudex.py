"""
this is a python port of https://github.com/ticki/eudex
"""
from typing import Optional

# Number of letters
LETTERS = 26
LETTERS_C1 = 33

# Trailing phones (ASCII)
PHONES = [
    0b00000000,  # a
    0b01001000,  # b
    0b00001100,  # c
    0b00011000,  # d
    0b00000000,  # e
    0b01000100,  # f
    0b00001000,  # g
    0b00000100,  # h
    0b00000001,  # i
    0b00000101,  # j
    0b00001001,  # k
    0b10100000,  # l
    0b00000010,  # m
    0b00010010,  # n
    0b00000000,  # o
    0b01001001,  # p
    0b10101000,  # q
    0b10100001,  # r
    0b00010100,  # s
    0b00011101,  # t
    0b00000001,  # u
    0b01000101,  # v
    0b00000000,  # w
    0b10000100,  # x
    0b00000001,  # y
    0b10010100,  # z
]

# Trailing phones (C1)
PHONES_C1 = [
    PHONES[18] ^ 1,  # ß
    0, 0, 0, 0, 0, 1, 0, PHONES[25] ^ 1, 1, 1, 1, 1, 1, 1, 1,
    0b00010101, 0b00010111, 0, 0, 0, 0, 1, 0xFF, 1, 1, 1, 1, 1,
    0b00010101, 1
]

# First-letter injective phones (ASCII)
INJECTIVE_PHONES = [
    0b10000100,  # a*
    0b00100100,  # b
    0b00000110,  # c
    0b00001100,  # d
    0b11011000,  # e*
    0b00100010,  # f
    0b00000100,  # g
    0b00000010,  # h
    0b11111000,  # i*
    0b00000011,  # j
    0b00000101,  # k
    0b01010000,  # l
    0b00000001,  # m
    0b00001001,  # n
    0b10010100,  # o*
    0b00100101,  # p
    0b01010100,  # q
    0b01010001,  # r
    0b00001010,  # s
    0b00001110,  # t
    0b11100000,  # u*
    0b00100011,  # v
    0b00000000,  # w
    0b01000010,  # x
    0b11100100,  # y*
    0b01001010,  # z
]

# First-letter injective phones (C1)
INJECTIVE_PHONES_C1 = [
    INJECTIVE_PHONES[18] ^ 1,  # ß
    INJECTIVE_PHONES[0] ^ 1,   # à
    INJECTIVE_PHONES[0] ^ 1,   # á
    0b10000000,  # â
    0b10000110,  # ã
    0b10100110,  # ä
    0b11000010,  # å
    0b10100111,  # æ
    0b01010100,  # ç
    INJECTIVE_PHONES[4] ^ 1,   # è
    INJECTIVE_PHONES[4] ^ 1,   # é
    INJECTIVE_PHONES[4] ^ 1,   # ê
    0b11000110,  # ë
    INJECTIVE_PHONES[8] ^ 1,   # ì
    INJECTIVE_PHONES[8] ^ 1,   # í
    INJECTIVE_PHONES[8] ^ 1,   # î
    INJECTIVE_PHONES[8] ^ 1,   # ï
    0b00001011,  # ð
    0b00001011,  # ñ
    INJECTIVE_PHONES[14] ^ 1,  # ò
    INJECTIVE_PHONES[14] ^ 1,  # ó
    INJECTIVE_PHONES[14] ^ 1,  # ô
    INJECTIVE_PHONES[14] ^ 1,  # õ
    0b11011100,  # ö
    0xFF,        # ÷
    0b11011101,  # ø
    INJECTIVE_PHONES[20] ^ 1,  # ù
    INJECTIVE_PHONES[20] ^ 1,  # ú
    INJECTIVE_PHONES[20] ^ 1,  # û
    INJECTIVE_PHONES[24] ^ 1,  # ü
    INJECTIVE_PHONES[24] ^ 1,  # ý
    0b00001011,  # þ
    INJECTIVE_PHONES[24] ^ 1,  # ÿ
]

# Weighted Hamming distance coefficients
BYTE_WEIGHTS = [128, 64, 32, 16, 8, 4, 2, 1]


def map_first(c: str) -> int:
    x = ord(c.lower())
    if ord('a') <= x <= ord('z'):
        return INJECTIVE_PHONES[x - ord('a')]
    elif 0xDF <= x <= 0xFF:
        return INJECTIVE_PHONES_C1[x - 0xDF]
    else:
        return 0


def filter_char(prev: int, c: str) -> Optional[int]:
    x = ord(c.lower())
    if ord('a') <= x <= ord('z'):
        val = PHONES[x - ord('a')]
    elif 0xDF <= x <= 0xFF:
        val = PHONES_C1[x - 0xDF]
    else:
        return None
    # Include if LSB differs from previous
    if (val & 1) != (prev & 1):
        return val
    return None


def eudex_hash(word: str) -> int:
    word = word.strip()
    if not word:
        return 0

    hash_bytes = [0] * 8
    # First character
    hash_bytes[0] = map_first(word[0])

    # Trailing characters
    prev = hash_bytes[0]
    pos = 1
    for c in word[1:]:
        if pos >= 8:
            break
        val = filter_char(prev, c)
        if val is not None:
            hash_bytes[pos] = val
            prev = val
            pos += 1

    # Combine bytes into 64-bit integer
    eudex_int = 0
    for b in hash_bytes:
        eudex_int = (eudex_int << 8) | b

    return eudex_int


def weighted_hamming_distance(h1: int, h2: int) -> int:
    dist = 0
    for i in range(8):
        b1 = (h1 >> (8 * (7 - i))) & 0xFF
        b2 = (h2 >> (8 * (7 - i))) & 0xFF
        xor = b1 ^ b2
        dist += bin(xor).count("1") * BYTE_WEIGHTS[i]
    return dist


def similar(h1: int, h2: int, threshold: int = 200) -> bool:
    return weighted_hamming_distance(h1, h2) <= threshold

class Hash:
    """Phonetic Eudex hash, equivalent to Rust's `Hash` struct."""

    def __init__(self, string: str):
        word = string.encode("utf-8")
        if not word:
            first_byte = 0
        else:
            first_byte = map_first(chr(word[0]))

        res = 0
        n = 1
        b = 0
        prev = 0

        while True:
            b += 1
            if n == 0 or b >= len(word):
                break

            val = filter_char(prev, chr(word[b]))
            if val is not None:
                res = (res << 8) | val
                prev = val
                n <<= 1  # match Rust shift

        self.hash = (first_byte << 56) | res

    def __sub__(self, other: "Hash") -> "Difference":
        return Difference(self.hash ^ other.hash)

    def __int__(self):
        return self.hash

    def __repr__(self):
        return f"Hash({self.hash:016x})"

    def __eq__(self, other):
        if isinstance(other, Hash):
            return self.hash == other.hash
        return self.hash == other


class Difference:
    """Difference between two Eudex hashes, equivalent to Rust's `Difference`."""

    def __init__(self, xor: int):
        self.xor = xor

    def dist(self) -> int:
        """Graduated distance: weighted Hamming per byte."""
        weights = [1, 2, 3, 5, 8, 13, 21, 34]
        total = 0
        for i, w in enumerate(weights):
            byte = (self.xor >> (8 * i)) & 0xFF
            total += bin(byte).count("1") * w
        return total

    def xor_val(self) -> int:
        """Raw XOR difference."""
        return self.xor

    def hamming(self) -> int:
        """Flat Hamming distance."""
        return bin(self.xor).count("1")

    def similar(self) -> bool:
        """Return True if the distance is small enough to consider words similar."""
        return self.dist() < 15


# Example usage
if __name__ == "__main__":
    h1 = Hash("hello")
    h2 = Hash("hellou")
    print("Hash hello:", h1)
    print("Hash hellou:", h2)
    diff = h1 - h2
    print("XOR:", diff.xor_val())
    print("Hamming:", diff.hamming())
    print("Weighted distance:", diff.dist())
    print("Similar?", diff.similar())

from itertools import product
from random import Random, randint
from string import ascii_uppercase,  ascii_lowercase


class Namer:
    """Random naming scope, guarantees uniqueness of names."""
    consonants = list("wrtpsdfgklzcvbnm")
    biconsonants = ["tr", "st", "sr", "pr", "pl", "sl", "kr", "kl", "kn", "dr", "wh"]
    vowels = list("euioa")
    dual_vowels = ["eu", "au", "oe", "ei", "oi", "ai"]

    sgrams = ["".join(p) for p in product(biconsonants, vowels)] + [""] * (len(biconsonants) * len(vowels))
    bigrams = ["".join(p) for p in product(consonants, vowels + dual_vowels)]
    trigrams = ["".join(p) for p in product(consonants, vowels, consonants)]
    reserved = [
        "map", "struct", "module", "long", "short", "unsigned", "if", "for", "while",
        "annotation", "const", "native", "typedef", "union", "switch", "case", "default",
        "enum", "fixed", "string", "sequence", "wstring", "float", "double", "char", "wchar",
        "boolean", "bool", "octet", "any", "bitset", "bitmap", "int", "uint", "true", "false",
        "del", "class", "not", "def"
    ]

    def __init__(self, seed, prefix, parent=None) -> None:
        self._random = Random(seed)
        self._prefix = prefix
        self._generated = set()
        self.parent = parent

    def short(self):
        while True:
            a = self._prefix + "".join(
                [self._random.choice(self.sgrams)] +
                self._random.choices(self.bigrams, k=self._random.randint(0, 1)) +
                [self._random.choice(self.trigrams)]
            )
            if a not in self._generated and a not in self.reserved and (not self.parent or a not in self.parent._generated):
                self._generated.add(a)
                return a

    def long(self):
        while True:
            a = self._prefix + "".join(
                [self._random.choice(self.sgrams)] +
                self._random.choices(self.bigrams, k=self._random.randint(1, 3)) +
                [self._random.choice(self.trigrams)]
            )
            if a not in self._generated and a not in self.reserved and (not self.parent or a not in self.parent._generated):
                self._generated.add(a)
                return a


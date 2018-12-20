# coding: utf-8
import codecs
import itertools
from typing import Optional, Tuple

cp1252_string = codecs.decode(bytearray(range(256)), 'cp1252', 'replace')
pd_modifications = [(5, 'ε'), (6, 'φ'), (12, 'λ'), (14, 'Ŋ'), (16, 'Ƥ'), (24, 'χ'), (26, 'ζ'), (160, '␣')]

decoding_list = list(cp1252_string)
encoding_table = dict(zip(range(256), (ord(c) for c in cp1252_string)))
for i, c in pd_modifications:
    decoding_list[i] = c
    encoding_table[ord(c)] = i

decoding_table = ''.join(decoding_list)

# Wow we are using some hardcore private API stuff here

class ParadocCodec(codecs.Codec):
    def encode(self, input_: str, errors: str = 'strict') -> Tuple[bytes, int]:
        return codecs.charmap_encode(input_, errors, encoding_table) # type: ignore

    def decode(self, input_: bytes, errors: str = 'strict') -> Tuple[str, int]:
        return codecs.charmap_decode(input_, errors, decoding_table) # type: ignore

def paradoc_lookup(name: str) -> Optional[codecs.CodecInfo]:
    if name != 'paradoc':
        return None
    return codecs.CodecInfo( # type: ignore
        name='paradoc',
        encode=ParadocCodec().encode,
        decode=ParadocCodec().decode,
    )

codecs.register(paradoc_lookup) # type: ignore

# vim:set tabstop=4 shiftwidth=4 expandtab fdm=marker:

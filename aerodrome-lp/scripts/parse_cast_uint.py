#!/usr/bin/env python3
"""Parse Foundry `cast` uint output (`INTEGER [SCI]`) to a canonical decimal integer.

Foundry prints `4665996001982801717720208990 [4.665e27]`. The first whitespace
token is the exact uint256; the bracket is a lossy annotation. Never use IEEE
float for wei.
"""

from __future__ import annotations

import re
import sys
from decimal import Decimal, InvalidOperation, getcontext

# uint256 is 78 digits; keep headroom for scientific mantissa + exponent.
getcontext().prec = 100

DIGITS_RE = re.compile(r"^[0-9]+$")
SCI_RE = re.compile(r"^[+-]?(?:\d+(?:\.\d*)?|\.\d+)[eE][+-]?\d+$")


def parse_cast_uint(raw: str | None) -> int:
    if raw is None:
        return 0
    text = str(raw).strip()
    if not text:
        return 0
    token = text.split()[0]
    if DIGITS_RE.fullmatch(token):
        return int(token)
    if SCI_RE.fullmatch(token):
        try:
            value = Decimal(token)
        except InvalidOperation as exc:
            raise ValueError(f"invalid scientific token: {token}") from exc
        if value < 0:
            raise ValueError(f"negative uint: {token}")
        integral = value.to_integral_value()
        if value != integral:
            raise ValueError(f"non-integral scientific token: {token}")
        return int(integral)
    raise ValueError(f"invalid cast uint: {token}")


def fmt_eth(wei: int) -> str:
    quantized = (Decimal(wei) / Decimal(10**18)).quantize(Decimal("0.000001"))
    return format(quantized, "f")


def main(argv: list[str]) -> int:
    try:
        if argv[:1] == ["--add"]:
            if len(argv) != 3:
                print("usage: parse_cast_uint.py --add A B", file=sys.stderr)
                return 2
            print(parse_cast_uint(argv[1]) + parse_cast_uint(argv[2]))
            return 0
        if argv[:1] == ["--gt"]:
            if len(argv) != 3:
                print("usage: parse_cast_uint.py --gt A B", file=sys.stderr)
                return 2
            print(int(parse_cast_uint(argv[1]) > parse_cast_uint(argv[2])))
            return 0
        if argv[:1] == ["--fmt-eth"]:
            raw = argv[1] if len(argv) > 1 else sys.stdin.read()
            print(fmt_eth(parse_cast_uint(raw)))
            return 0
        raw = " ".join(argv) if argv else sys.stdin.read()
        print(parse_cast_uint(raw))
        return 0
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

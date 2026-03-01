from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Shard:
    shard_id: int
    shard_gen: int
    shard_size: int | None = None  # in bits
    bitmask: bytes | None = None  # bit=1 => seen


def bitmask_nbytes(shard_size_bits: int) -> int:
    if shard_size_bits < 0:
        raise ValueError("shard_size_bits must be >= 0")
    return (shard_size_bits + 7) // 8


def make_empty_bitmask(shard_size_bits: int) -> bytes:
    return b"\x00" * bitmask_nbytes(shard_size_bits)


def is_seen(bitmask: bytes, bit_index: int) -> bool:
    """
    Checks whether bit_index is set in bitmask (LSB-first within each byte).

    Args:
        bitmask: Bytes representing a bitset.
        bit_index: 0-based index.

    Returns:
        True if the bit is 1, else False.
    """
    if bit_index < 0:
        raise ValueError("bit_index must be >= 0")
    byte_i = bit_index // 8
    bit_i = bit_index % 8
    if byte_i >= len(bitmask):
        return False
    return (bitmask[byte_i] & (1 << bit_i)) != 0


def set_seen(bitmask: bytes, bit_index: int) -> bytes:
    """
    Returns a new bitmask with bit_index set to 1 (LSB-first).

    Notes:
        bytes are immutable in Python, so we return a new bytes object.

    Args:
        bitmask: Existing bitset.
        bit_index: 0-based index.

    Returns:
        Updated bitmask bytes.
    """
    if bit_index < 0:
        raise ValueError("bit_index must be >= 0")
    byte_i = bit_index // 8
    bit_i = bit_index % 8
    if byte_i >= len(bitmask):
        raise ValueError("bit_index out of range for this bitmask length")

    b = bytearray(bitmask)
    b[byte_i] |= 1 << bit_i
    return bytes(b)

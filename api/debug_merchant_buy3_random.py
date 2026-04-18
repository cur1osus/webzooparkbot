from __future__ import annotations

import argparse
import random
from collections import Counter

RARITIES = ("_rare", "_epic", "_mythical", "_leg")


def parse_weights(raw: str) -> list[float]:
    weights = [float(part.strip()) for part in raw.split(",")]
    if len(weights) != len(RARITIES):
        raise ValueError("Need exactly 4 rarity weights")
    return weights


def simulate_catalog_purchase(quantity: int, weights: list[float], rng: random.Random):
    remaining = quantity
    unit_counts: Counter[str] = Counter()
    chunk_counts: Counter[str] = Counter()
    part_sizes: Counter[int] = Counter()
    chunks: list[tuple[str, int]] = []

    while remaining > 0:
        rarity = rng.choices(RARITIES, weights=weights, k=1)[0]
        part = rng.randint(1, remaining)
        remaining -= part
        unit_counts[rarity] += part
        chunk_counts[rarity] += 1
        part_sizes[part] += 1
        chunks.append((rarity, part))

    return unit_counts, chunk_counts, part_sizes, chunks


def fmt(counter: Counter, total: int) -> str:
    parts = []
    for rarity in RARITIES:
        value = counter[rarity]
        pct = (value / total * 100) if total else 0
        parts.append(f"{rarity}: {value} ({pct:.2f}%)")
    return "\n".join(parts)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=1000)
    parser.add_argument("--quantity", type=int, default=10)
    parser.add_argument("--weights", default="0.69,0.2,0.1,0.01")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--examples", type=int, default=5)
    args = parser.parse_args()

    if args.runs < 1:
        raise SystemExit("--runs must be >= 1")
    if args.quantity < 1:
        raise SystemExit("--quantity must be >= 1")

    weights = parse_weights(args.weights)
    rng = random.Random(args.seed)

    unit_totals: Counter[str] = Counter()
    chunk_totals: Counter[str] = Counter()
    part_size_totals: Counter[int] = Counter()
    examples: list[list[tuple[str, int]]] = []

    for run_index in range(args.runs):
        unit_counts, chunk_counts, part_sizes, chunks = simulate_catalog_purchase(
            quantity=args.quantity,
            weights=weights,
            rng=rng,
        )
        unit_totals.update(unit_counts)
        chunk_totals.update(chunk_counts)
        part_size_totals.update(part_sizes)
        if run_index < args.examples:
            examples.append(chunks)

    total_units = args.runs * args.quantity
    total_chunks = sum(chunk_totals.values())

    print(f"runs={args.runs}")
    print(f"quantity={args.quantity}")
    print(f"weights={weights}")
    print(f"seed={args.seed}")
    print()
    print("Unit distribution")
    print(fmt(unit_totals, total_units))
    print()
    print("Chunk distribution")
    print(fmt(chunk_totals, total_chunks))
    print()
    print("Chunk size distribution")
    for size in sorted(part_size_totals):
        value = part_size_totals[size]
        pct = value / total_chunks * 100 if total_chunks else 0
        print(f"{size}: {value} ({pct:.2f}%)")
    print()
    print("Example runs")
    for idx, chunks in enumerate(examples, start=1):
        rendered = ", ".join(f"{rarity}x{part}" for rarity, part in chunks)
        print(f"{idx}: {rendered}")


if __name__ == "__main__":
    main()

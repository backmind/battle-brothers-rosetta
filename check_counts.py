from pathlib import Path
from rosetta import extract
from collections import Counter

orig_file = Path(r"D:\GOG\Battle Brothers\!Downloads\bbros\bin\comparer\original\scripts\contracts\contracts\obtain_item_contract.nut")
trans_file = Path(r"D:\GOG\Battle Brothers\!Downloads\bbros\bin\comparer\spanish_tr\scripts\contracts\contracts\obtain_item_contract.nut")

orig_content = orig_file.read_text(encoding="utf-8")
trans_content = trans_file.read_text(encoding="utf-8")

orig_pairs = [p for p in extract(orig_content) if isinstance(p, dict)]
trans_pairs = [p for p in extract(trans_content) if isinstance(p, dict)]

print(f"Original: {len(orig_pairs)} strings")
print(f"Traducido: {len(trans_pairs)} strings")
print()

orig_ctx = Counter(p.get("_context", "") for p in orig_pairs)
trans_ctx = Counter(p.get("_context", "") for p in trans_pairs)

print("=== Contextos con diferente cantidad ===")
all_contexts = set(orig_ctx.keys()) | set(trans_ctx.keys())
for ctx in all_contexts:
    o = orig_ctx.get(ctx, 0)
    t = trans_ctx.get(ctx, 0)
    if o != t:
        print(f"{ctx}")
        print(f"  Original: {o}, Traducido: {t}")

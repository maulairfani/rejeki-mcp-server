"""
Quick add: catat transaksi dari teks natural language dalam 1 tool call.
Semua resolusi (akun, envelope, amount) terjadi di server.
"""

import re
from datetime import date
from difflib import get_close_matches
from rejeki.database import fetchall, fetchone
from rejeki.tools.transactions import add_transaction


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

_AMOUNT_PATTERN = re.compile(
    r"(\d[\d.,]*)\s*(rb|ribu|k|jt|juta|m)?",
    re.IGNORECASE,
)


def _parse_amount(text: str) -> float | None:
    """Ekstrak angka dari teks. Contoh: '15k' → 15000, '1.5jt' → 1500000."""
    m = _AMOUNT_PATTERN.search(text)
    if not m:
        return None
    num_str = m.group(1).replace(",", ".").replace(".", "")
    try:
        num = float(num_str)
    except ValueError:
        return None
    suffix = (m.group(2) or "").lower()
    if suffix in ("rb", "ribu", "k"):
        num *= 1_000
    elif suffix in ("jt", "juta", "m"):
        num *= 1_000_000
    return num


def _fuzzy_match(query: str, choices: list[dict], key: str) -> dict | None:
    """Cari dict di choices yang field `key`-nya paling mirip dengan query."""
    names = [c[key] for c in choices]
    matches = get_close_matches(query.lower(), [n.lower() for n in names], n=1, cutoff=0.4)
    if not matches:
        return None
    matched_name = matches[0]
    for c in choices:
        if c[key].lower() == matched_name:
            return c
    return None


def _extract_tokens(text: str) -> list[str]:
    """Pecah teks jadi token kata (tanpa angka dan suffix amount)."""
    cleaned = _AMOUNT_PATTERN.sub("", text)
    tokens = re.findall(r"[a-zA-Z]+", cleaned.lower())
    stopwords = {"aku", "abis", "beli", "dari", "ke", "di", "pake", "pakai", "via", "sama", "buat", "untuk", "tadi", "habis"}
    return [t for t in tokens if t not in stopwords]


# ---------------------------------------------------------------------------
# Main function
# ---------------------------------------------------------------------------

def quick_add(text: str) -> dict:
    """
    Catat transaksi dari teks natural language.
    Deteksi: amount, akun, envelope, payee.
    Kembalikan hasil transaksi + info apa yang di-match.
    """
    # 1. Parse amount
    amount = _parse_amount(text)
    if not amount:
        raise ValueError(f"Tidak bisa mendeteksi nominal dari: '{text}'")

    # 2. Load data dari DB
    accounts = fetchall("SELECT id, name, type FROM accounts ORDER BY name")
    envelopes = fetchall("SELECT id, name, icon FROM envelopes WHERE type = 'expense' ORDER BY name")

    if not accounts:
        raise ValueError("Belum ada rekening. Tambah rekening dulu.")

    # 3. Match akun dan envelope dari token kata
    tokens = _extract_tokens(text)

    matched_account = None
    matched_envelope = None
    remaining_tokens = list(tokens)

    # Coba match tiap token ke akun dulu
    for token in tokens:
        result = _fuzzy_match(token, accounts, "name")
        if result:
            matched_account = result
            remaining_tokens = [t for t in remaining_tokens if t != token]
            break

    # Sisa token → coba match ke envelope
    for token in remaining_tokens:
        result = _fuzzy_match(token, envelopes, "name")
        if result:
            matched_envelope = result
            remaining_tokens = [t for t in remaining_tokens if t != token]
            break

    # Fallback akun: ambil yang pertama kalau tidak ada match
    if not matched_account:
        matched_account = accounts[0]
        account_note = f"default ({matched_account['name']})"
    else:
        account_note = f"matched '{matched_account['name']}'"

    # 4. Payee dari sisa token
    payee = " ".join(remaining_tokens).title() or None

    # 5. Insert transaksi
    result = add_transaction(
        amount=amount,
        type="expense",
        account_id=matched_account["id"],
        envelope_id=matched_envelope["id"] if matched_envelope else None,
        payee=payee,
        memo=text,
    )

    return {
        **result,
        "matched": {
            "account": f"{matched_account['name']} ({account_note})",
            "envelope": matched_envelope["name"] if matched_envelope else None,
            "payee": payee,
            "amount": amount,
        },
    }

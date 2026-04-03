from datetime import datetime

from fastmcp import FastMCP

mcp = FastMCP()


@mcp.prompt()
def budget_review(period: str | None = None) -> str:
    """Review budget bulanan: analisis overspend dan saran rebalancing."""
    p = period or datetime.now().strftime("%Y-%m")
    return (
        f"Lakukan review budget bulan {p}:\n\n"
        f"1. Panggil finance_get_summary(period='{p}') untuk ringkasan income, expense, dan net.\n"
        f"2. Panggil finance_get_envelopes(period='{p}') untuk detail setiap envelope "
        f"(carryover, assigned, activity, available).\n"
        f"3. Identifikasi envelope yang overspend (available negatif).\n"
        f"4. Berikan ringkasan: envelope mana yang konsisten, mana yang perlu perhatian.\n"
        f"5. Cek finance_get_ready_to_assign(period='{p}') — jika ada RTA tersisa, sarankan alokasi ke envelope yang kekurangan."
    )


@mcp.prompt()
def monthly_planning(period: str | None = None) -> str:
    """Panduan distribusi budget awal bulan: cek RTA, lihat targets, assign hingga RTA = 0."""
    p = period or datetime.now().strftime("%Y-%m")
    return (
        f"Bantu planning budget bulan {p}:\n\n"
        f"1. Panggil finance_get_ready_to_assign(period='{p}') — lihat berapa uang yang belum dialokasikan.\n"
        f"2. Panggil finance_get_envelopes(period='{p}') — lihat target setiap envelope dan available saat ini.\n"
        f"3. Prioritaskan envelope dengan target 'monthly' yang belum terpenuhi.\n"
        f"4. Untuk envelope 'goal', cek apakah on track menuju deadline.\n"
        f"5. Distribusikan RTA ke envelope yang paling butuh hingga RTA = 0.\n"
        f"Gunakan finance_assign_to_envelope untuk setiap alokasi. Tanya user jika ada prioritas khusus."
    )

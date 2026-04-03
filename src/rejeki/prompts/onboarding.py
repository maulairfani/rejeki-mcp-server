from fastmcp import FastMCP

mcp = FastMCP()


@mcp.prompt()
def onboarding_guide() -> str:
    """Wizard setup Rejeki dari awal: rekening → envelope → budget."""
    return (
        "Bantu setup Rejeki dari awal:\n\n"
        "1. Baca finance://onboarding-status untuk melihat progress saat ini.\n"
        "2. Jika belum ada rekening: tambah dengan finance_add_account (type: bank | ewallet | cash).\n"
        "3. Buat kelompok envelope dengan finance_add_group (contoh: Kebutuhan, Keinginan, Tabungan).\n"
        "4. Buat envelope untuk setiap kategori dengan finance_add_envelope (type: income | expense).\n"
        "5. Set target dengan finance_set_target untuk envelope yang punya target bulanan atau goal.\n"
        "6. Assign budget ke setiap envelope dengan finance_assign_to_envelope hingga RTA = 0.\n\n"
        "Tanyakan user mau mulai dari step mana, atau ikuti step berikutnya yang belum selesai."
    )

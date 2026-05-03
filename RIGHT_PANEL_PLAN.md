# Right Panel Plan

Setiap halaman punya right panel (detail/inspector panel) yang kontekstual.
Panel selalu terlihat — isinya berubah sesuai item yang dipilih atau state halaman.

---

## Envelopes ✅ (done)

**Empty state (tidak ada envelope dipilih):**
- RTA amount besar dengan warna kontekstual
- RTA > 0: tombol "Fund all targets" + list envelope underfunded dengan input assign per item
- RTA = 0: checkmark + "All set"
- RTA < 0: banner merah + list envelope dengan assigned > 0 untuk dikurangi (input reduce)

**Selected state (envelope diklik):**
- Budget breakdown: carryover, assigned, funded, activity, available
- Assign section: input editable + tombol Save (persists ke backend)
- Cover overspent: list donor envelope (jika available < 0)
- Target editor: select type + amount + deadline + tombol "Save target"

Semua aksi punya feedback: loading spinner → success checkmark (1.5s) → idle, atau error (2s) → idle.

---

## Transactions ✅ (done)

**Empty state:**
- Filter aktif ringkas (period, akun, envelope)
- Summary: total income, total expense, net bulan ini

**Selected state (transaksi diklik):**
- Detail: tanggal, jumlah, tipe, payee, memo
- Aksi: Edit (inline form — amount, payee, memo, date, envelope, akun), Delete (konfirmasi)
- Tags: tampil + edit inline

---

## Accounts ✅ (done)

**Empty state:**
- Total balance semua akun
- Quick-add akun baru

**Selected state (akun diklik):**
- Balance saat ini (besar)
- Aksi: Update balance (reconcile) — input + Save
- 5 transaksi terakhir dari akun ini
- Edit nama/tipe akun

---

## Scheduled Transactions (belum)

**Empty state:**
- Berapa transaksi jatuh tempo bulan ini
- Berapa sudah diapprove

**Selected state:**
- Detail: amount, payee, jadwal, recurrence, envelope
- Aksi: Approve (mark as paid), Skip next, Edit jadwal, Delete

---

## Wishlist (belum)

**Empty state:**
- Total estimated price semua item "wanted"
- Estimasi bulan bisa beli item termahal berdasarkan saving rate

**Selected state:**
- Detail: nama, harga, prioritas, URL, notes
- Aksi: Edit, Mark as bought, Buat envelope dari item ini, Delete

---

## Analytics / Dashboard (belum)

Panel ini berfungsi sebagai **filter panel**:
- Filter period (range)
- Filter per akun
- Filter per envelope group
- Tidak ada selected state — selalu tampil sebagai kontrol filter

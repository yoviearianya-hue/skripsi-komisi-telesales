from datetime import datetime
import os
from tkinter import filedialog
import customtkinter as ctk
from logic_komisi import hitung_komisi

# Konfigurasi tema global CustomTkinter
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class AplikasiKomisiTelesales(ctk.CTk):
    """ Kelas utama Aplikasi Desktop 'Sistem Perhitungan Komisi Telesales'.

    Menggunakan pendekatan OOP dan terhubung dengan modul logic_komisi.py.
    """

    def __init__(self):
        super().__init__()

        # --- State / Penyimpanan Lokasi File (Path) ---
        self.folder_proyek: str = os.path.dirname(os.path.abspath(__file__))
        self.path_data_penjualan: str | None = None
        self.path_data_target: str | None = None

        self.daftar_bulan = [
            "Januari",
            "Februari",
            "Maret",
            "April",
            "Mei",
            "Juni",
            "Juli",
            "Agustus",
            "September",
            "Oktober",
            "November",
            "Desember",
        ]
        self.daftar_tahun = ["2025", "2026", "2027"]

        # --- Inisialisasi Jendela & UI ---
        self._konfigurasi_window()
        self._bangun_ui()

        # Log awal saat aplikasi dibuka
        self.tulis_log(
            f"Aplikasi Sistem Perhitungan Komisi Telesales siap digunakan. Folder aktif: {self.folder_proyek}",
            "INFO",
        )

    def _konfigurasi_window(self) -> None:
        """Mengatur ukuran, judul, dan tata letak grid utama jendela aplikasi."""
        self.title("Sistem Perhitungan Komisi Telesales")
        self.geometry("780x680")
        self.minsize(680, 600)

        # Pastikan jendela langsung tampil paling depan saat dibuka
        self.deiconify()
        self.lift()
        self.attributes("-topmost", True)
        self.after(600, lambda: self.attributes("-topmost", False))
        self.focus_force()

        # Konfigurasi grid utama (1 kolom penuh, baris ke-4 (area log) dapat melar)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(4, weight=1)

    def _bangun_ui(self) -> None:
        """Membangun seluruh komponen antarmuka pengguna (UI) secara terstruktur."""
        self._buat_header_section()
        self._buat_active_date_section()
        self._buat_upload_section()
        self._buat_tombol_proses_section()
        self._buat_log_section()

    def _buat_header_section(self) -> None:
        """1. Bagian Judul Aplikasi di bagian atas."""
        self.header_frame = ctk.CTkFrame(
            self, corner_radius=12, fg_color=("gray85", "#1E293B")
        )
        self.header_frame.grid(row=0, column=0, padx=24, pady=(20, 10), sticky="ew")
        self.header_frame.grid_columnconfigure(0, weight=1)

        self.lbl_judul = ctk.CTkLabel(
            self.header_frame,
            text="Sistem Perhitungan Komisi Telesales",
            font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"),
            text_color=("#0F172A", "#F8FAFC"),
        )
        self.lbl_judul.grid(row=0, column=0, padx=20, pady=(16, 4))

        self.lbl_subjudul = ctk.CTkLabel(
            self.header_frame,
            text="Kelola periode aktif, unggah data Excel, dan proses komisi agen secara otomatis",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=("gray40", "#94A3B8"),
        )
        self.lbl_subjudul.grid(row=1, column=0, padx=20, pady=(0, 16))

    def _buat_active_date_section(self) -> None:
        """2. Bagian Dropdown Bulan dan Tahun yang mewakili 'Active Date'."""
        self.date_frame = ctk.CTkFrame(self, corner_radius=12)
        self.date_frame.grid(row=1, column=0, padx=24, pady=10, sticky="ew")
        self.date_frame.grid_columnconfigure((1, 3), weight=1)

        self.lbl_active_date = ctk.CTkLabel(
            self.date_frame,
            text="📅  Active Date (Periode):",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
        )
        self.lbl_active_date.grid(
            row=0, column=0, columnspan=4, padx=20, pady=(14, 6), sticky="w"
        )

        # Dropdown Bulan (Januari - Desember)
        self.lbl_bulan = ctk.CTkLabel(
            self.date_frame,
            text="Bulan:",
            font=ctk.CTkFont(family="Segoe UI", size=13),
        )
        self.lbl_bulan.grid(row=1, column=0, padx=(20, 10), pady=(4, 16), sticky="w")

        self.dropdown_bulan = ctk.CTkOptionMenu(
            self.date_frame,
            values=self.daftar_bulan,
            height=36,
            corner_radius=8,
            font=ctk.CTkFont(family="Segoe UI", size=13),
            command=self._on_periode_berubah,
        )
        self.dropdown_bulan.set("Oktober")
        self.dropdown_bulan.grid(
            row=1, column=1, padx=(0, 20), pady=(4, 16), sticky="ew"
        )

        # Dropdown Tahun (2025, 2026, 2027)
        self.lbl_tahun = ctk.CTkLabel(
            self.date_frame,
            text="Tahun:",
            font=ctk.CTkFont(family="Segoe UI", size=13),
        )
        self.lbl_tahun.grid(row=1, column=2, padx=(10, 10), pady=(4, 16), sticky="w")

        self.dropdown_tahun = ctk.CTkOptionMenu(
            self.date_frame,
            values=self.daftar_tahun,
            height=36,
            corner_radius=8,
            font=ctk.CTkFont(family="Segoe UI", size=13),
            command=self._on_periode_berubah,
        )
        self.dropdown_tahun.set("2026")
        self.dropdown_tahun.grid(
            row=1, column=3, padx=(0, 20), pady=(4, 16), sticky="ew"
        )

    def _buat_upload_section(self) -> None:
        """3. Bagian Tombol Upload Data Penjualan & Data Target Agen (Excel)."""
        self.upload_frame = ctk.CTkFrame(self, corner_radius=12)
        self.upload_frame.grid(row=2, column=0, padx=24, pady=10, sticky="ew")
        self.upload_frame.grid_columnconfigure((0, 1), weight=1)

        self.lbl_upload_header = ctk.CTkLabel(
            self.upload_frame,
            text="📂  Unggah Dokumen Sumber (Excel)",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
        )
        self.lbl_upload_header.grid(
            row=0, column=0, columnspan=2, padx=20, pady=(14, 8), sticky="w"
        )

        # Tombol Upload Data Penjualan (Excel)
        self.btn_upload_penjualan = ctk.CTkButton(
            self.upload_frame,
            text="Upload Data Penjualan (Excel)",
            height=42,
            corner_radius=8,
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            command=self.upload_data_penjualan,
        )
        self.btn_upload_penjualan.grid(
            row=1, column=0, padx=(20, 10), pady=(4, 4), sticky="ew"
        )

        # Tombol Upload Data Target Agen (Excel)
        self.btn_upload_target = ctk.CTkButton(
            self.upload_frame,
            text="Upload Data Target Agen (Excel)",
            height=42,
            corner_radius=8,
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            command=self.upload_data_target,
        )
        self.btn_upload_target.grid(
            row=1, column=1, padx=(10, 20), pady=(4, 4), sticky="ew"
        )

        # Indikator nama file di bawah masing-masing tombol
        self.lbl_status_penjualan = ctk.CTkLabel(
            self.upload_frame,
            text="Belum ada file dipilih",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=("gray45", "#94A3B8"),
        )
        self.lbl_status_penjualan.grid(
            row=2, column=0, padx=(20, 10), pady=(0, 14), sticky="w"
        )

        self.lbl_status_target = ctk.CTkLabel(
            self.upload_frame,
            text="Belum ada file dipilih",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=("gray45", "#94A3B8"),
        )
        self.lbl_status_target.grid(
            row=2, column=1, padx=(10, 20), pady=(0, 14), sticky="w"
        )

    def _buat_tombol_proses_section(self) -> None:
        """4. Tombol besar 'Proses Perhitungan Komisi'."""
        self.btn_proses = ctk.CTkButton(
            self,
            text="⚡  Proses Perhitungan Komisi",
            height=52,
            corner_radius=10,
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            fg_color="#10B981",
            hover_color="#059669",
            text_color="#FFFFFF",
            command=self.jalankan_proses_komisi,
        )
        self.btn_proses.grid(row=3, column=0, padx=24, pady=10, sticky="ew")

    def _buat_log_section(self) -> None:
        """5. Area Text Box besar di bawah untuk menampilkan log."""
        self.log_frame = ctk.CTkFrame(self, corner_radius=12)
        self.log_frame.grid(row=4, column=0, padx=24, pady=(10, 20), sticky="nsew")
        self.log_frame.grid_columnconfigure(0, weight=1)
        self.log_frame.grid_rowconfigure(1, weight=1)

        self.lbl_log = ctk.CTkLabel(
            self.log_frame,
            text="📋  Log Aktivitas & Status Sistem",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
        )
        self.lbl_log.grid(row=0, column=0, padx=16, pady=(12, 4), sticky="w")

        self.textbox_log = ctk.CTkTextbox(
            self.log_frame,
            corner_radius=8,
            font=ctk.CTkFont(family="Consolas", size=12),
            wrap="word",
            state="disabled",
        )
        self.textbox_log.grid(
            row=1, column=0, padx=16, pady=(4, 16), sticky="nsew"
        )

    # =========================================================================
    # FUNGSI UTILITAS & EVENT HANDLER
    # =========================================================================

    def tulis_log(self, pesan: str, kategori: str = "INFO") -> None:
        """Menambahkan baris catatan waktu dan status ke dalam Text Box Log."""
        waktu = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        baris_log = f"[{waktu}] [{kategori}] {pesan}\n"

        self.textbox_log.configure(state="normal")
        self.textbox_log.insert("end", baris_log)
        self.textbox_log.see("end")
        self.textbox_log.configure(state="disabled")

    def ambil_active_date(self) -> tuple[str, str]:
        """Mengembalikan pasangan (bulan, tahun) yang sedang dipilih."""
        return self.dropdown_bulan.get(), self.dropdown_tahun.get()

    def _on_periode_berubah(self, _pilihan: str) -> None:
        """Callback ketika dropdown Bulan atau Tahun diubah."""
        bulan, tahun = self.ambil_active_date()
        self.tulis_log(f"Active Date diatur ke periode: {bulan} {tahun}", "INFO")

    def _pilih_file_excel(self, judul_dialog: str) -> str | None:
        """Membuka dialog pemilihan file khusus ekstensi Excel di folder proyek."""
        jalur_file = filedialog.askopenfilename(
            title=judul_dialog,
            initialdir=self.folder_proyek,
            filetypes=[
                ("Excel Files", "*.xlsx *.xls"),
                ("All Files", "*.*"),
            ],
        )
        return jalur_file if jalur_file else None

    def upload_data_penjualan(self) -> None:
        """Handler tombol 'Upload Data Penjualan (Excel)' untuk menangkap lokasi file."""
        jalur = self._pilih_file_excel("Pilih File Excel Data Penjualan")
        if jalur and os.path.isfile(jalur):
            self.path_data_penjualan = jalur
            nama_file = os.path.basename(jalur)
            self.lbl_status_penjualan.configure(
                text=f"✔ {nama_file}", text_color="#34D399"
            )
            self.tulis_log(
                f"Upload Data Penjualan berhasil. Lokasi file: {self.path_data_penjualan}",
                "BERHASIL",
            )
        else:
            self.tulis_log(
                "Upload Data Penjualan dibatalkan atau file tidak valid.",
                "GAGAL",
            )

    def upload_data_target(self) -> None:
        """Handler tombol 'Upload Data Target Agen (Excel)' untuk menangkap lokasi file."""
        jalur = self._pilih_file_excel("Pilih File Excel Data Target Agen")
        if jalur and os.path.isfile(jalur):
            self.path_data_target = jalur
            nama_file = os.path.basename(jalur)
            self.lbl_status_target.configure(
                text=f"✔ {nama_file}", text_color="#34D399"
            )
            self.tulis_log(
                f"Upload Data Target Agen berhasil. Lokasi file: {self.path_data_target}",
                "BERHASIL",
            )
        else:
            self.tulis_log(
                "Upload Data Target Agen dibatalkan atau file tidak valid.",
                "GAGAL",
            )

    # =========================================================================
    # LOGIKA PERHITUNGAN KOMISI (TERHUBUNG KE logic_komisi.py)
    # =========================================================================

    def jalankan_proses_komisi(self) -> None:
        """Memanggil fungsi hitung_komisi dari logic_komisi.py dan menampilkan hasilnya di Log UI."""
        nama_bulan, tahun_str = self.ambil_active_date()
        bulan_aktif = self.daftar_bulan.index(nama_bulan) + 1
        tahun_aktif = int(tahun_str)

        self.tulis_log(
            f"Memulai perhitungan komisi untuk Active Date: {nama_bulan} (Bulan {bulan_aktif}) Tahun {tahun_aktif}...",
            "PROSES",
        )

        # Validasi kelengkapan lokasi file Excel sebelum diproses
        if not self.path_data_penjualan:
            self.tulis_log(
                "Error: File 'Data Penjualan (Excel)' belum di-upload!",
                "GAGAL",
            )
            return

        if not self.path_data_target:
            self.tulis_log(
                "Error: File 'Data Target Agen (Excel)' belum di-upload!",
                "GAGAL",
            )
            return

        # Lempar variabel lokasi file penjualan, lokasi file target, bulan_aktif, dan tahun_aktif
        hasil_status = hitung_komisi(
            path_data_penjualan=self.path_data_penjualan,
            path_data_target=self.path_data_target,
            bulan_aktif=bulan_aktif,
            tahun_aktif=tahun_aktif,
        )

        # Tampilkan pesan berhasil atau error di text box log UI
        if hasil_status == "sukses":
            lokasi_output = os.path.join(
                self.folder_proyek,
                "Laporan_Komisi_Final.xlsx",
            )
            self.tulis_log(
                f"Status: {hasil_status.upper()} — Perhitungan komisi periode {nama_bulan} {tahun_aktif} "
                f"berhasil diselesaikan! File disimpan di: {lokasi_output}",
                "BERHASIL",
            )
        else:
            self.tulis_log(
                f"Gagal memproses komisi -> {hasil_status}",
                "ERROR",
            )


if __name__ == "__main__":
    app = AplikasiKomisiTelesales()
    app.mainloop()


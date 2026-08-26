# ═══════════════════════════════════════════════════════════════════════════════
# gui.py  —  Nova AGI — Grafik Kullanıcı Arayüzü (İkinci Pencere)
# ═══════════════════════════════════════════════════════════════════════════════
#
# Mevcut HİÇBİR dosyayı değiştirmez.
# nova_launcher.py tarafından başlatılır.
# main.py'nin tüm sistemini arka planda çalıştırırken bu pencereyi açar.
#
# Özellikler:
#   • Koyu tema (göz yormuyor, uzun oturumlar için)
#   • Canlı VRAM / Loss / Adım göstergesi (sağ panel)
#   • Komut kısayolları (! komutlarını butonla çalıştır)
#   • Konuşma geçmişi kaydırılabilir pencere
#   • GPU durum çubuğu (renk kodu: yeşil=GPU, sarı=CPU)
#   • Thread-safe queue ile Nova motoru ile iletişim
# ═══════════════════════════════════════════════════════════════════════════════

import queue
import threading
import time
import tkinter as tk
from tkinter import ttk, scrolledtext, font as tkfont
from datetime import datetime


# ══════════════════════════════════════════════════════════════════════════════
# RENK PALETİ  (Koyu tema)
# ══════════════════════════════════════════════════════════════════════════════
class Palet:
    ARKAPLAN        = "#0f0f17"   # Ana arka plan (çok koyu mor-siyah)
    PANEL           = "#1a1a2e"   # Panel arka planı
    KENAR           = "#16213e"   # Kenarlıklar
    GIRIS_BG        = "#1e1e30"   # Giriş kutusu arka planı
    GIRIS_AKTIF     = "#252540"   # Aktif giriş
    KULLANICI_BG    = "#1a2744"   # Kullanıcı mesaj balonu
    NOVA_BG         = "#1a2e1a"   # Nova mesaj balonu
    SISTEM_BG       = "#2a1a2a"   # Sistem mesajı balonu
    KULLANICI_METIN = "#7eb8f7"   # Kullanıcı metin rengi (açık mavi)
    NOVA_METIN      = "#7ef77e"   # Nova metin rengi (açık yeşil)
    SISTEM_METIN    = "#c77ef7"   # Sistem metin rengi (açık mor)
    ZAMAN_METIN     = "#555577"   # Zaman damgası rengi
    BASLIK          = "#e0e0ff"   # Başlık rengi
    ALTYAZI         = "#8888aa"   # Alt yazı rengi
    GONDER_DUGME    = "#3a5fc8"   # Gönder butonu
    GONDER_HOVER    = "#4a6fd8"   # Gönder hover
    TEMIZLE_DUGME   = "#c83a3a"   # Temizle butonu
    DURUM_GPU       = "#00cc66"   # GPU aktif (yeşil)
    DURUM_CPU       = "#ccaa00"   # CPU modu (sarı)
    DURUM_BEKLE     = "#cc6600"   # Yükleniyor (turuncu)
    KOMUT_DUGME     = "#2a3a5a"   # Komut butonu arka planı
    KOMUT_METIN     = "#aabbdd"   # Komut butonu metin
    SCROLLBAR       = "#2a2a45"   # Kaydırma çubuğu
    GRAFIKBG        = "#12121f"   # Grafik arka planı
    KAYIP_CIZGI     = "#ff6b6b"   # Loss grafiği çizgisi


# ══════════════════════════════════════════════════════════════════════════════
# ANA GUI SINIFI
# ══════════════════════════════════════════════════════════════════════════════

class NovaGUI:
    """
    Nova'nın grafik arayüzü.
    hafiza, beyin, beden nesnelerini alır ve onlarla doğrudan konuşur.
    """

    def __init__(self, root: tk.Tk, hafiza, beyin, beden):
        self.root   = root
        self.hafiza = hafiza
        self.beyin  = beyin
        self.beden  = beden

        # Thread-safe iletişim kuyrukları
        self._giris_q  = queue.Queue()   # GUI → Motor
        self._cikis_q  = queue.Queue()   # Motor → GUI

        # Durum değişkenleri
        self._bekliyor   = False
        self._loss_gecmis: list[float] = []
        self._adim_gecmis: list[int]   = []

        # Ana pencere
        self._pencere_ayarla()
        self._tema_ayarla()
        self._duzen_olustur()

        # Motor thread'ini başlat
        self._motor_thread = threading.Thread(
            target=self._motor_dongusu,
            daemon=True,
            name="NovaGUI-Motor"
        )
        self._motor_thread.start()

        # Periyodik güncelleme (100ms)
        self._gui_guncelle()

    # ══════════════════════════════════════════════════════════════════════════
    # PENCERE ve TEMA KURULUMU
    # ══════════════════════════════════════════════════════════════════════════

    def _pencere_ayarla(self):
        self.root.title("Nova AGI — Otonom Öğrenen Yapay Zeka")
        self.root.geometry("1280x780")
        self.root.minsize(900, 600)
        self.root.configure(bg=Palet.ARKAPLAN)
        self.root.protocol("WM_DELETE_WINDOW", self._kapat)

        # Uygulama ikonu (emoji fallback)
        try:
            self.root.iconbitmap("nova_icon.ico")
        except Exception:
            pass

    def _tema_ayarla(self):
        stil = ttk.Style()
        stil.theme_use("clam")

        # Genel widget stilleri
        stil.configure(".",
            background=Palet.PANEL,
            foreground=Palet.BASLIK,
            fieldbackground=Palet.GIRIS_BG,
            troughcolor=Palet.SCROLLBAR,
        )
        stil.configure("TFrame",     background=Palet.PANEL)
        stil.configure("TLabel",     background=Palet.PANEL,   foreground=Palet.BASLIK)
        stil.configure("TButton",    background=Palet.KOMUT_DUGME, foreground=Palet.KOMUT_METIN,
                        borderwidth=0, focuscolor="none", padding=6)
        stil.map("TButton",
            background=[("active", Palet.GONDER_HOVER), ("pressed", Palet.KENAR)]
        )
        stil.configure("TScrollbar",
            background=Palet.SCROLLBAR,
            troughcolor=Palet.PANEL,
            borderwidth=0,
        )
        stil.configure("TSeparator", background=Palet.KENAR)

    def _duzen_olustur(self):
        """Ana düzen: Başlık | Sol(Sohbet) | Sağ(Panel)"""
        # ── Başlık Çubuğu ─────────────────────────────────────────────────────
        self._baslik_olustur()

        # ── Ana İçerik (Sol + Sağ) ────────────────────────────────────────────
        ana = tk.Frame(self.root, bg=Palet.ARKAPLAN)
        ana.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        # Sol: Sohbet bölgesi
        sol = tk.Frame(ana, bg=Palet.ARKAPLAN)
        sol.pack(side="left", fill="both", expand=True)
        self._sohbet_alani_olustur(sol)
        self._giris_alani_olustur(sol)

        # Ayırıcı
        tk.Frame(ana, bg=Palet.KENAR, width=1).pack(side="left", fill="y", padx=4)

        # Sağ: Durum paneli
        sag = tk.Frame(ana, bg=Palet.PANEL, width=280)
        sag.pack(side="right", fill="y")
        sag.pack_propagate(False)
        self._durum_paneli_olustur(sag)

        # ── Alt Durum Çubuğu ──────────────────────────────────────────────────
        self._alt_cubuk_olustur()

    # ══════════════════════════════════════════════════════════════════════════
    # BAŞLIK
    # ══════════════════════════════════════════════════════════════════════════

    def _baslik_olustur(self):
        baslik_frame = tk.Frame(self.root, bg=Palet.PANEL, height=56)
        baslik_frame.pack(fill="x", padx=0, pady=0)
        baslik_frame.pack_propagate(False)

        # Logo ve isim
        logo = tk.Label(baslik_frame, text="🌟 NOVA",
                        font=("Consolas", 20, "bold"),
                        bg=Palet.PANEL, fg="#a0c0ff")
        logo.pack(side="left", padx=16, pady=10)

        alt = tk.Label(baslik_frame, text="Otonom Öğrenen AGI Prototipi",
                       font=("Segoe UI", 9),
                       bg=Palet.PANEL, fg=Palet.ALTYAZI)
        alt.pack(side="left", pady=14)

        # GPU durum badge
        self._gpu_etiket = tk.Label(baslik_frame, text="⚙ Başlatılıyor...",
                                    font=("Consolas", 9, "bold"),
                                    bg="#1a2a1a", fg=Palet.DURUM_BEKLE,
                                    padx=10, pady=4)
        self._gpu_etiket.pack(side="right", padx=16, pady=12)

        # Ayırıcı çizgi
        tk.Frame(self.root, bg=Palet.KENAR, height=1).pack(fill="x")

    # ══════════════════════════════════════════════════════════════════════════
    # SOHBET ALANI
    # ══════════════════════════════════════════════════════════════════════════

    def _sohbet_alani_olustur(self, parent: tk.Frame):
        cerceve = tk.Frame(parent, bg=Palet.ARKAPLAN)
        cerceve.pack(fill="both", expand=True, padx=0, pady=(6, 0))

        # Scrollbar
        sb = ttk.Scrollbar(cerceve)
        sb.pack(side="right", fill="y")

        # Ana metin alanı (Salt okunur)
        self._sohbet = tk.Text(
            cerceve,
            state="disabled",
            bg=Palet.ARKAPLAN,
            fg=Palet.BASLIK,
            font=("Consolas", 11),
            relief="flat",
            wrap="word",
            padx=14,
            pady=8,
            spacing3=4,
            selectbackground=Palet.GIRIS_AKTIF,
            cursor="arrow",
            yscrollcommand=sb.set,
        )
        self._sohbet.pack(fill="both", expand=True)
        sb.config(command=self._sohbet.yview)

        # Renk etiketleri
        self._sohbet.tag_configure("kullanici_isim",
            foreground=Palet.KULLANICI_METIN, font=("Consolas", 10, "bold"))
        self._sohbet.tag_configure("kullanici_metin",
            foreground="#d0e8ff",             font=("Consolas", 11))
        self._sohbet.tag_configure("nova_isim",
            foreground=Palet.NOVA_METIN,      font=("Consolas", 10, "bold"))
        self._sohbet.tag_configure("nova_metin",
            foreground="#d0ffd0",             font=("Consolas", 11))
        self._sohbet.tag_configure("sistem_isim",
            foreground=Palet.SISTEM_METIN,    font=("Consolas", 10, "bold"))
        self._sohbet.tag_configure("sistem_metin",
            foreground="#e8d0ff",             font=("Consolas", 10, "italic"))
        self._sohbet.tag_configure("zaman",
            foreground=Palet.ZAMAN_METIN,     font=("Consolas", 8))
        self._sohbet.tag_configure("bekliyor",
            foreground=Palet.DURUM_BEKLE,     font=("Consolas", 10, "italic"))
        self._sohbet.tag_configure("ayirac",
            foreground=Palet.KENAR)

        # Hoş geldin mesajı
        self._mesaj_ekle("sistem", "sistem",
            "Nova AGI sistemi hazır. Sohbet edebilir, "
            "komutlar yazabilir (! ile başlayanlar) veya "
            "sağdaki butonları kullanabilirsiniz.")

    def _mesaj_ekle(self, rol: str, isim: str, metin: str):
        """Thread-safe mesaj ekleme — sadece GUI thread'inden çağrılmalı."""
        self._sohbet.configure(state="normal")

        zaman = datetime.now().strftime("%H:%M")

        if rol == "kullanici":
            self._sohbet.insert("end", f"\n┌ Sen  ", "kullanici_isim")
            self._sohbet.insert("end", f"[{zaman}]\n", "zaman")
            self._sohbet.insert("end", f"│ {metin}\n", "kullanici_metin")
            self._sohbet.insert("end", "└─\n", "ayirac")

        elif rol == "nova":
            self._sohbet.insert("end", f"\n┌ Nova ", "nova_isim")
            self._sohbet.insert("end", f"[{zaman}]\n", "zaman")
            # Satırlara bölerek girintile
            for satir in metin.split("\n"):
                self._sohbet.insert("end", f"│ {satir}\n", "nova_metin")
            self._sohbet.insert("end", "└─\n", "ayirac")

        elif rol == "sistem":
            self._sohbet.insert("end", f"  ◈ ", "sistem_isim")
            self._sohbet.insert("end", f"{metin}\n", "sistem_metin")

        elif rol == "bekliyor":
            self._bekleme_idx = self._sohbet.index("end")
            self._sohbet.insert("end", "  ◌ Nova düşünüyor...\n", "bekliyor")

        self._sohbet.configure(state="disabled")
        self._sohbet.see("end")

    def _bekleme_kaldir(self):
        """'Nova düşünüyor...' satırını sil."""
        try:
            if hasattr(self, "_bekleme_idx"):
                self._sohbet.configure(state="normal")
                # Son "bekliyor" satırını bul ve sil
                start = self._sohbet.search("◌ Nova düşünüyor...",
                                            "1.0", "end")
                if start:
                    satir_no = int(start.split(".")[0])
                    self._sohbet.delete(f"{satir_no}.0", f"{satir_no+1}.0")
                self._sohbet.configure(state="disabled")
        except Exception:
            pass

    # ══════════════════════════════════════════════════════════════════════════
    # GİRİŞ ALANI
    # ══════════════════════════════════════════════════════════════════════════

    def _giris_alani_olustur(self, parent: tk.Frame):
        cerceve = tk.Frame(parent, bg=Palet.PANEL, pady=8)
        cerceve.pack(fill="x", padx=0)

        # Hızlı komut butonları
        buton_satiri = tk.Frame(cerceve, bg=Palet.PANEL)
        buton_satiri.pack(fill="x", padx=10, pady=(0, 6))

        hizli_komutlar = [
            ("📊 İstatistik",  "!istatistik"),
            ("🗂 Anılar",      "!anilar 5"),
            ("🌐 Tara",        "!tara "),
            ("🧠 Yetenekler",  "!yetenekler"),
            ("💾 Kaydet",      "!kaydet"),
            ("📋 Görevler",    "!gorevler"),
        ]

        for etiket, cmd in hizli_komutlar:
            b = tk.Button(
                buton_satiri,
                text=etiket,
                bg=Palet.KOMUT_DUGME,
                fg=Palet.KOMUT_METIN,
                relief="flat",
                font=("Segoe UI", 8),
                padx=8, pady=3,
                cursor="hand2",
                command=lambda c=cmd: self._hizli_gonder(c),
                activebackground=Palet.GONDER_HOVER,
                activeforeground="white",
            )
            b.pack(side="left", padx=2)

        # Giriş + Gönder
        giris_satiri = tk.Frame(cerceve, bg=Palet.PANEL)
        giris_satiri.pack(fill="x", padx=10)

        self._giris = tk.Text(
            giris_satiri,
            height=3,
            bg=Palet.GIRIS_BG,
            fg=Palet.BASLIK,
            font=("Consolas", 12),
            relief="flat",
            wrap="word",
            padx=10, pady=8,
            insertbackground="#a0c0ff",    # İmleç rengi
            selectbackground=Palet.GIRIS_AKTIF,
        )
        self._giris.pack(side="left", fill="x", expand=True)
        self._giris.bind("<Return>",       self._enter_gonder)
        self._giris.bind("<Shift-Return>", lambda e: None)  # Shift+Enter = yeni satır
        self._giris.bind("<Control-l>",    lambda e: self._temizle())
        self._giris.focus()

        # Placeholder efekti
        self._placeholder_goster()
        self._giris.bind("<FocusIn>",  lambda e: self._placeholder_kaldir())
        self._giris.bind("<FocusOut>", lambda e: self._placeholder_goster())

        # Butonlar sütunu
        buton_sutun = tk.Frame(giris_satiri, bg=Palet.PANEL)
        buton_sutun.pack(side="right", padx=(6, 0))

        gonder = tk.Button(
            buton_sutun,
            text="➤ Gönder",
            bg=Palet.GONDER_DUGME,
            fg="white",
            font=("Segoe UI", 10, "bold"),
            relief="flat",
            padx=14, pady=8,
            cursor="hand2",
            command=self._gonder,
            activebackground=Palet.GONDER_HOVER,
            activeforeground="white",
        )
        gonder.pack(fill="x", pady=(0, 4))

        temizle = tk.Button(
            buton_sutun,
            text="🗑 Temizle",
            bg=Palet.TEMIZLE_DUGME,
            fg="white",
            font=("Segoe UI", 9),
            relief="flat",
            padx=10, pady=5,
            cursor="hand2",
            command=self._temizle,
            activebackground="#dd4444",
            activeforeground="white",
        )
        temizle.pack(fill="x")

    def _placeholder_goster(self):
        if not self._giris.get("1.0", "end-1c").strip():
            self._giris.insert("1.0", "Nova'ya bir şey sor, ya da ! ile komut gir...")
            self._giris.configure(fg="#555566")

    def _placeholder_kaldir(self):
        if self._giris.get("1.0", "end-1c") == "Nova'ya bir şey sor, ya da ! ile komut gir...":
            self._giris.delete("1.0", "end")
            self._giris.configure(fg=Palet.BASLIK)

    def _enter_gonder(self, event):
        """Enter → gönder, Shift+Enter → yeni satır."""
        if not event.state & 0x1:   # Shift basılı değil
            self._gonder()
            return "break"

    def _hizli_gonder(self, cmd: str):
        """Hızlı komut butonundan gönder."""
        if cmd.endswith(" "):
            # URL gerektiren komutlar: giriş kutusuna yaz
            self._giris.delete("1.0", "end")
            self._giris.insert("1.0", cmd)
            self._giris.configure(fg=Palet.BASLIK)
            self._giris.focus()
        else:
            self._giris_gonder(cmd)

    def _gonder(self):
        metin = self._giris.get("1.0", "end-1c").strip()
        if not metin or metin == "Nova'ya bir şey sor, ya da ! ile komut gir...":
            return
        self._giris.delete("1.0", "end")
        self._giris_gonder(metin)

    def _giris_gonder(self, metin: str):
        """Girişi kuyruğa at, UI'da göster."""
        if self._bekliyor:
            self._mesaj_ekle("sistem", "", "Nova henüz cevap üretmekte, lütfen bekleyin.")
            return

        self._mesaj_ekle("kullanici", "kullanici", metin)
        self._giris_q.put(metin)
        self._bekliyor = True
        self._mesaj_ekle("bekliyor", "", "")

    def _temizle(self):
        self._sohbet.configure(state="normal")
        self._sohbet.delete("1.0", "end")
        self._sohbet.configure(state="disabled")
        self._mesaj_ekle("sistem", "", "Ekran temizlendi.")

    # ══════════════════════════════════════════════════════════════════════════
    # DURUM PANELİ (Sağ)
    # ══════════════════════════════════════════════════════════════════════════

    def _durum_paneli_olustur(self, parent: tk.Frame):
        # Başlık
        tk.Label(parent, text="⚡ CANLI DURUM",
                 font=("Consolas", 10, "bold"),
                 bg=Palet.PANEL, fg=Palet.ALTYAZI,
                 pady=10).pack(fill="x")
        tk.Frame(parent, bg=Palet.KENAR, height=1).pack(fill="x")

        # ── Model Metrikleri ──────────────────────────────────────────────────
        metrik_frame = tk.Frame(parent, bg=Palet.PANEL, pady=6)
        metrik_frame.pack(fill="x", padx=12)

        self._metrikler: dict[str, tk.StringVar] = {}

        metrik_tanimlari = [
            ("model_adim",    "Eğitim Adımı",  "0"),
            ("model_loss",    "Loss",           "∞"),
            ("model_lr",      "Öğrenme Hızı",  "—"),
            ("model_vocab",   "Vocab Boyutu",  "—"),
            ("bellek_ani",    "Epizodik Node", "—"),    # <-- Değişti
            ("bellek_bilgi",  "Semantik Node", "—"),  # <-- Değişti
            ("bellek_gorev",  "Aktif Thread",  "—"),   # <-- Değişti
        ]

        for anahtar, etiket, varsayilan in metrik_tanimlari:
            satir = tk.Frame(metrik_frame, bg=Palet.PANEL)
            satir.pack(fill="x", pady=2)
            tk.Label(satir, text=etiket + ":", width=16, anchor="w",
                     bg=Palet.PANEL, fg=Palet.ALTYAZI,
                     font=("Segoe UI", 9)).pack(side="left")
            var = tk.StringVar(value=varsayilan)
            self._metrikler[anahtar] = var
            tk.Label(satir, textvariable=var, anchor="e",
                     bg=Palet.PANEL, fg="#aad4ff",
                     font=("Consolas", 9, "bold")).pack(side="right")

        tk.Frame(parent, bg=Palet.KENAR, height=1).pack(fill="x", pady=4)

        # ── GPU Bellek Çubuğu ─────────────────────────────────────────────────
        tk.Label(parent, text="GPU VRAM",
                 font=("Segoe UI", 8), bg=Palet.PANEL,
                 fg=Palet.ALTYAZI).pack(padx=12, anchor="w")

        self._vram_cubuk = ttk.Progressbar(
            parent, orient="horizontal",
            length=200, mode="determinate"
        )
        self._vram_cubuk.pack(padx=12, pady=(2, 6), fill="x")

        self._vram_etiket = tk.Label(parent, text="— / — MB",
                                     font=("Consolas", 8),
                                     bg=Palet.PANEL, fg=Palet.ALTYAZI)
        self._vram_etiket.pack(anchor="center")

        tk.Frame(parent, bg=Palet.KENAR, height=1).pack(fill="x", pady=4)

        # ── Loss Mini Grafik ──────────────────────────────────────────────────
        tk.Label(parent, text="LOSS GRAFİĞİ",
                 font=("Segoe UI", 8), bg=Palet.PANEL,
                 fg=Palet.ALTYAZI).pack(padx=12, anchor="w", pady=(4, 2))

        self._grafik = tk.Canvas(
            parent, bg=Palet.GRAFIKBG,
            height=90, relief="flat",
            highlightthickness=0,
        )
        self._grafik.pack(padx=12, fill="x", pady=(0, 8))

        # ── Sistem Bilgisi ────────────────────────────────────────────────────
        tk.Frame(parent, bg=Palet.KENAR, height=1).pack(fill="x")
        self._sistem_etiket = tk.Label(
            parent, text="Sistem bilgisi yükleniyor...",
            font=("Segoe UI", 8), bg=Palet.PANEL,
            fg=Palet.ZAMAN_METIN, wraplength=260, justify="left"
        )
        self._sistem_etiket.pack(padx=12, pady=8, anchor="w")

        self._sistem_bilgisi_guncelle()

    def _sistem_bilgisi_guncelle(self):
        """Sabit sistem bilgisini doldur."""
        try:
            import platform
            os_str = f"{platform.system()} {platform.release()}"
            py_str = platform.python_version()
            self._sistem_etiket.configure(
                text=(
                    f"OS: {os_str}\n"
                    f"Python: {py_str}\n"
                    f"CPU: Ryzen 5600X (12T)\n"
                    f"GPU: RX 6500 XT (4GB)"
                )
            )
        except Exception:
            pass

    def _loss_grafigi_ciz(self):
        """Son N loss değerini mini kanvasa çiz."""
        canvas = self._grafik
        canvas.delete("all")
        g = self._loss_gecmis[-60:]   # Son 60 değer
        if len(g) < 2:
            canvas.create_text(
                130, 45, text="Veri bekleniyor...",
                fill=Palet.ZAMAN_METIN, font=("Consolas", 8)
            )
            return

        w = canvas.winfo_width()  or 256
        h = canvas.winfo_height() or 90
        pad = 8

        mn, mx = min(g), max(g)
        if mx == mn:
            mx = mn + 0.001

        def px(i):
            return pad + (i / (len(g) - 1)) * (w - 2 * pad)

        def py(v):
            return h - pad - ((v - mn) / (mx - mn)) * (h - 2 * pad)

        # Izgara çizgileri
        for yi in range(3):
            y = pad + yi * (h - 2 * pad) / 2
            canvas.create_line(pad, y, w - pad, y,
                                fill=Palet.KENAR, dash=(2, 4))

        # Loss eğrisi
        noktalar = [(px(i), py(v)) for i, v in enumerate(g)]
        for i in range(len(noktalar) - 1):
            x1, y1 = noktalar[i]
            x2, y2 = noktalar[i + 1]
            canvas.create_line(x1, y1, x2, y2,
                                fill=Palet.KAYIP_CIZGI, width=1.5, smooth=True)

        # Son değer noktası
        x, y = noktalar[-1]
        canvas.create_oval(x-3, y-3, x+3, y+3,
                            fill=Palet.KAYIP_CIZGI, outline="")

        # Etiketler
        canvas.create_text(pad, pad, text=f"{mx:.3f}",
                            anchor="nw", fill=Palet.ZAMAN_METIN,
                            font=("Consolas", 7))
        canvas.create_text(pad, h - pad, text=f"{mn:.3f}",
                            anchor="sw", fill=Palet.ZAMAN_METIN,
                            font=("Consolas", 7))

    # ══════════════════════════════════════════════════════════════════════════
    # ALT DURUM ÇUBUĞU
    # ══════════════════════════════════════════════════════════════════════════

    def _alt_cubuk_olustur(self):
        tk.Frame(self.root, bg=Palet.KENAR, height=1).pack(fill="x")
        cubuk = tk.Frame(self.root, bg=Palet.PANEL, height=24)
        cubuk.pack(fill="x")

        self._durum_str = tk.StringVar(value="Sistem başlatılıyor...")
        tk.Label(cubuk, textvariable=self._durum_str,
                 font=("Segoe UI", 8), bg=Palet.PANEL,
                 fg=Palet.ALTYAZI).pack(side="left", padx=10)

        self._zaman_str = tk.StringVar()
        tk.Label(cubuk, textvariable=self._zaman_str,
                 font=("Consolas", 8), bg=Palet.PANEL,
                 fg=Palet.ZAMAN_METIN).pack(side="right", padx=10)

    # ══════════════════════════════════════════════════════════════════════════
    # MOTOR THREAD'İ (Arka plan — Nova ile konuşur)
    # ══════════════════════════════════════════════════════════════════════════

    def _motor_dongusu(self):
        """
        GUI'den gelen mesajları alır, Nova motoruna gönderir,
        cevabı _cikis_q'ya koyar.
        """
        import re

        while True:
            try:
                girdi = self._giris_q.get(timeout=1)
            except queue.Empty:
                continue

            try:
                # !cikis komutu
                if girdi.strip().lower() in ("!cikis", "!çıkış", "exit", "quit"):
                    self._cikis_q.put(("sistem", "Kapatılıyor..."))
                    self.root.after(500, self._kapat)
                    continue

                # ! Komutları
                if girdi.startswith("!"):
                    cevap = self._komut_isle(girdi)
                    self._cikis_q.put(("sistem", cevap))
                    continue

                # Sıradan konuşma — Nova motoruna gönder
                self.hafiza.ani_kaydet("kullanici", girdi)
                baglam   = self.hafiza.rag_sorgula(girdi, k=3, max_karakter=300)
                son_anilar = self.hafiza.son_anilar_getir(limit=6)
                gecmis  = ""
                for ani in son_anilar[-4:]:
                    pref = "Kullanıcı" if ani["rol"] == "kullanici" else "Nova"
                    gecmis += f"{pref}: {ani['icerik']}\n"

                parcalar = []
                if baglam:
                    parcalar.append(f"[Bağlam: {baglam[:250]}]")
                if gecmis:
                    parcalar.append(gecmis.strip())
                parcalar.append(f"Kullanıcı: {girdi}\nNova:")
                tohum = "\n".join(parcalar)

                cevap_ham = self.beyin.uret(
                    tohum, uzunluk=260, sicaklik=0.85, top_k=50, top_p=0.92
                )

                # Temizle
                cevap = self._cevap_temizle(cevap_ham)
                self.hafiza.ani_kaydet("nova", cevap)

                # Eylem kontrolü
                eylem = re.search(r"\[EYLEM:\s*(.+?)\]", cevap, re.I)
                if eylem:
                    try:
                        eylem_sonuc = self.beden.gorevi_coz(eylem.group(1))
                        cevap += f"\n[Eylem sonucu: {eylem_sonuc[:200]}]"
                    except Exception as e:
                        cevap += f"\n[Eylem hatası: {e}]"

                self._cikis_q.put(("nova", cevap))

            except Exception as e:
                self._cikis_q.put(("sistem", f"Motor hatası: {e}"))

    def _komut_isle(self, girdi: str) -> str:
        """! komutlarını doğrudan işle."""
        parcalar = girdi[1:].split(maxsplit=1)
        cmd = parcalar[0].lower() if parcalar else ""
        arg = parcalar[1].strip() if len(parcalar) > 1 else ""

        if cmd == "istatistik":
            s = self.hafiza.istatistik()
            semantik_node = s.get('bilgi_sayisi', 0)
            epizodik_node = s.get('ani_sayisi', 0)
            toplam_node = semantik_node + epizodik_node
            
            try:
                param_sayisi = f"{self.beyin.model.param_sayisi():,}"
            except:
                param_sayisi = "~15,000,000"

            return (
                f"🧠 NOVA AGI — SİNİR AĞI VE NODE DURUMU\n"
                f" ├─ Toplam Veri : {toplam_node:,} Node\n"
                f" │   ├─ Semantik Ağ: {semantik_node:,} Düğüm\n"
                f" │   └─ Epizodik Ağ: {epizodik_node:,} Düğüm\n"
                f" ├─ İşlenmeyi Bekleyen: {s.get('egitilmemis', 0):,} Node\n"
                f" ├─ Sinir Ağı Bağları: {param_sayisi} Parametre\n"
                f" └─ Derin Öğrenme Adımı: {self.beyin.adim:,}"
            )
        elif cmd in ("anilar", "anılar"):
            n = int(arg) if arg.isdigit() else 5
            anilar = self.hafiza.son_anilar_getir(limit=n)
            satirlar = [f"📜 Son {n} Anı:"]
            for a in anilar:
                satirlar.append(f"[{a['zaman']}] {a['rol']}: {a['icerik'][:60]}")
            return "\n".join(satirlar)
        elif cmd == "tara":
            if not arg or not arg.startswith("http"):
                return "Kullanım: !tara https://..."
            metin = self.beden.url_tara(arg)
            if metin:
                self.hafiza.bilgi_kaydet(arg, arg, metin)
                return f"✓ Tarandı: {len(metin):,} karakter kaydedildi."
            return "✗ Taranamadı."
        elif cmd == "yetenekler":
            return "🧠 Yetenekler:\n" + "\n".join(
                f"  • {y}" for y in self.beden.yetenek_listele()
            )
        elif cmd == "kaydet":
            self.beyin.kaydet()
            return "✓ Model checkpoint'i kaydedildi."
        elif cmd == "gorevler":
            gorevler = self.hafiza.tum_gorevler()
            if not gorevler:
                return "Görev kuyruğu boş."
            return "\n".join(
                f"[{g['id']}] {g['durum']}: {g['tanim'][:50]}"
                for g in gorevler
            )
        elif cmd == "rag":
            if arg:
                return f"RAG: {self.hafiza.rag_sorgula(arg, k=2)[:400]}"
            return "Kullanım: !rag <sorgu>"
        elif cmd == "hf":
            from hf_auth import hf_durum_metni, hf_token_kaydet_ve_giris, hf_token_sil
            if not arg:
                return hf_durum_metni()
            elif arg.lower() in ("sil", "cikis", "çıkış", "logout"):
                hf_token_sil()
                return "Hugging Face token'ı silindi. Anonim moda geçildi."
            else:
                ok, msg = hf_token_kaydet_ve_giris(arg)
                return msg
        elif cmd in ("lang", "dil"):
            from config_manager import get_language, set_language
            if not arg:
                l = get_language() or "en"
                return f"🌐 Active language / Aktif dil: {'English (en)' if l=='en' else 'Türkçe (tr)'}"
            elif arg.lower() in ("en", "eng", "english", "1"):
                set_language("en")
                return "✓ Switched to English mode. (Wikipedia: 20231101.en)"
            elif arg.lower() in ("tr", "tur", "turkish", "türkçe", "2"):
                set_language("tr")
                return "✓ Türkçe moduna geçildi. (Wikipedia: 20231101.tr)"
            else:
                return "Usage: !lang en  or  !lang tr"
        elif cmd == "yardim":
            return (
                "📖 Komutlar:\n"
                "  !istatistik  !anilar [N]  !tara <url>\n"
                "  !yetenekler  !kaydet      !gorevler\n"
                "  !hf [token]  !lang [en|tr] !rag <sorgu> !cikis"
            )
        else:
            return f"Bilinmeyen komut: !{cmd}. !yardim deneyin."

    @staticmethod
    def _cevap_temizle(ham: str) -> str:
        """Tohum kalıntılarını ve fazla boşlukları temizle."""
        import re
        for tag in ["Nova:", "Kullanıcı:", "[Bağlam:"]:
            idx = ham.find(tag)
            if idx != -1:
                ham = ham[:idx]
        ham = re.sub(r"\n{3,}", "\n\n", ham).strip()
        paragraflar = [p.strip() for p in ham.split("\n\n") if p.strip()]
        cevap = "\n\n".join(paragraflar[:2])
        if len(cevap) > 700:
            cevap = cevap[:700].rsplit(" ", 1)[0] + "..."
        return cevap or "Anlıyorum. Daha fazla öğrendikçe daha iyi yanıt vereceğim."

    # ══════════════════════════════════════════════════════════════════════════
    # PERİYODİK GUI GÜNCELLEMESİ
    # ══════════════════════════════════════════════════════════════════════════

    def _gui_guncelle(self):
        """100ms'de bir çağrılır — cevapları, metrikleri günceller."""

        # Cevap kuyruğunu tüket
        while not self._cikis_q.empty():
            try:
                rol, metin = self._cikis_q.get_nowait()
                self._bekleme_kaldir()
                self._bekliyor = False
                self._mesaj_ekle(rol, rol, metin)
            except queue.Empty:
                break

        # ── Metrik güncellemesi (her 2 saniyede bir) ──────────────────────────
        if not hasattr(self, "_son_metrik"):
            self._son_metrik = 0

        simdi = time.monotonic()
        if simdi - self._son_metrik >= 2.0:
            self._son_metrik = simdi
            self._metrikleri_guncelle()

        # Zaman çubuğu
        self._zaman_str.set(datetime.now().strftime("%H:%M:%S"))

        # Bir sonraki güncelleme
        self.root.after(100, self._gui_guncelle)

    def _metrikleri_guncelle(self):
        """Canlı model metriklerini panele yaz."""
        try:
            # Model metrikleri
            adim = self.beyin.adim
            lr   = self.beyin.optimizer.param_groups[0]["lr"]

            son_loss = self.beyin.son_loss()
            if son_loss != float("inf") and son_loss > 0:
                self._loss_gecmis.append(son_loss)
                if len(self._loss_gecmis) > 200:
                    self._loss_gecmis = self._loss_gecmis[-200:]

            self._metrikler["model_adim"].set(f"{adim:,}")
            self._metrikler["model_loss"].set(
                f"{son_loss:.4f}" if son_loss != float("inf") else "—"
            )
            self._metrikler["model_lr"].set(f"{lr:.2e}")
            self._metrikler["model_vocab"].set(f"{len(self.beyin.char2id):,}")

            # DB metrikleri
            stat = self.hafiza.istatistik()
            self._metrikler["bellek_ani"].set(f"{stat['ani_sayisi']:,}")
            self._metrikler["bellek_bilgi"].set(f"{stat['bilgi_sayisi']:,}")
            self._metrikler["bellek_gorev"].set(f"{stat['gorev_bekleyen']}")

            # GPU VRAM
            self._vram_guncelle()

            # Loss grafiği
            self._loss_grafigi_ciz()

            # Durum çubuğu
            egitim = "🔥 Eğitim aktif" if self.beyin.is_training else "⏸ Eğitim bekliyor"
            self._durum_str.set(
                f"Adım: {adim:,}  |  {egitim}  |  "
                f"Vocab: {len(self.beyin.char2id)}"
            )

        except Exception:
            pass

    def _vram_guncelle(self):
        """GPU VRAM çubuğunu güncelle."""
        try:
            import torch
            if torch.cuda.is_available():
                toplam    = torch.cuda.get_device_properties(0).total_memory // (1024**2)
                kullanilan = torch.cuda.memory_allocated(0) // (1024**2)
                yuzde     = (kullanilan / toplam) * 100 if toplam else 0
                self._vram_cubuk["value"] = min(yuzde, 100)
                self._vram_etiket.configure(
                    text=f"{kullanilan} / {toplam} MB  ({yuzde:.1f}%)"
                )
                renk = Palet.DURUM_GPU if yuzde < 80 else Palet.TEMIZLE_DUGME
                self._gpu_etiket.configure(
                    text=f"🔥 AMD RX 6500 XT  {kullanilan}/{toplam} MB",
                    fg=renk
                )
            else:
                self._vram_cubuk["value"] = 0
                self._vram_etiket.configure(text="GPU yok (CPU modu)")
                self._gpu_etiket.configure(
                    text="💻 CPU — Ryzen 5600X (12T)",
                    fg=Palet.DURUM_CPU
                )
        except Exception:
            pass

    # ══════════════════════════════════════════════════════════════════════════
    # KAPAT
    # ══════════════════════════════════════════════════════════════════════════

    def _kapat(self):
        """Güvenli kapatma."""
        try:
            self.beyin.kaydet()
        except Exception:
            pass
        self.root.destroy()


# ══════════════════════════════════════════════════════════════════════════════
# BAĞIMSIZ TEST (sadece GUI'yi test eder)
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    # Dummy nesnelerle GUI'yi test et
    class DummyHafiza:
        def ani_kaydet(self, *a, **k): return 1
        def son_anilar_getir(self, **k): return []
        def rag_sorgula(self, *a, **k): return ""
        def istatistik(self): return {
            "ani_sayisi": 0, "bilgi_sayisi": 0,
            "egitilmemis": 0, "gorev_bekleyen": 0, "gorev_tamamlandi": 0
        }
        def tum_gorevler(self): return []
        def bilgi_kaydet(self, *a): return 1

    class DummyBeyin:
        adim = 42
        char2id = {"a": 0}
        is_training = True
        class optimizer:
            param_groups = [{"lr": 3e-4}]
        def uret(self, *a, **k): return "Bu bir test cevabıdır. Nova henüz yükleniyor."
        def kaydet(self): pass
        def son_loss(self): return 2.718

    class DummyBeden:
        def url_tara(self, url): return "Test içeriği"
        def yetenek_listele(self): return ["merhaba", "hesapla", "tarih_saat"]
        def gorevi_coz(self, t): return "Görev çözüldü."

    root = tk.Tk()
    app  = NovaGUI(root, DummyHafiza(), DummyBeyin(), DummyBeden())
    root.mainloop()

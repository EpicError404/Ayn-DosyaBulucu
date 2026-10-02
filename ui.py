from __future__ import annotations

import os
import queue
import re
import sys
import threading
from datetime import datetime
from pathlib import Path
from tkinter import PhotoImage, TclError, filedialog, messagebox

import customtkinter as ctk

from scanner import (
    DuplicateGroup,
    DriveInfo,
    export_results,
    find_duplicates,
    list_drives,
    move_file,
    rename_file,
    scan_files,
    send_to_trash,
)


PALETTE = {
    "canvas": "#F6F8F5",
    "panel": "#FFFFFF",
    "sidebar": "#E9F0E9",
    "mint": "#D9E9DC",
    "green": "#547A5C",
    "green_dark": "#365A40",
    "ink": "#233129",
    "muted": "#78837B",
    "line": "#E3E9E3",
    "coral": "#F4E0D9",
    "coral_ink": "#A35543",
    "blue": "#E2EAF2",
    "white": "#FFFFFF",
}


def _resource_path(filename: str) -> Path:
    base_path = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base_path / filename


EXTENSION_CATEGORIES = {
    "Resimler": {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tif", ".tiff", ".webp", ".heic"},
    "Videolar": {".mp4", ".mov", ".avi", ".mkv", ".wmv", ".flv", ".webm", ".m4v"},
    "Belgeler": {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".txt", ".rtf", ".odt", ".ods", ".csv"},
    "Uygulamalar": {".exe", ".msi", ".bat", ".cmd"},
    "Ses": {".mp3", ".wav", ".flac", ".aac", ".m4a", ".ogg"},
    "Arşivler": {".zip", ".rar", ".7z", ".tar", ".gz"},
}

ENGLISH_TEXT = {
    "Kopya Dosya Bulucu": "Duplicate File Finder",
    "Sürücüleri seç": "Select drives",
    "Taranacak sürücüler": "Drives to scan",
    "Sabit diskler varsayılan olarak seçilidir. Optik sürücüler taranmaz.": "Fixed drives are selected by default. Optical drives are skipped.",
    "USB / harici çıkarılabilir sürücüleri göster": "Show USB / removable drives",
    "Vazgeç": "Cancel",
    "Sürücüleri uygula": "Apply drives",
    "Kullanılabilir sürücü bulunamadı.": "No available drives found.",
    "Yerel disk": "Local disk",
    "USB / Harici": "USB / External",
    "Dosya türleri": "File types",
    "Tüm uzantıları seçin veya yalnızca istediğiniz türleri işaretleyin.": "Select all extensions or choose only the file types you need.",
    "Tüm uzantılar": "All extensions",
    "Diğer uzantılar": "Other extensions",
    "Uygula": "Apply",
    "Resimler": "Images",
    "Videolar": "Videos",
    "Belgeler": "Documents",
    "Uygulamalar": "Applications",
    "Ses": "Audio",
    "Arşivler": "Archives",
    "Hazır": "Ready",
    "Durduruluyor": "Stopping",
    "Taranıyor": "Scanning",
    "Hash hesaplanıyor": "Hashing",
    "Durduruldu": "Stopped",
    "Tamamlandı": "Complete",
    "ÇALIŞMA ALANI": "WORKSPACE",
    "Kopya dosyalar": "Duplicates",
    "Dışa aktarılanlar": "Exports",
    "YEREL TARAMA": "LOCAL SCAN",
    "Dosyalarınız cihazınızda kalır.": "Your files stay on your device.",
    "Aynı içerikli dosyaları güvenle inceleyin": "Review identical files with confidence",
    "▣  Sürücüler": "▣  Drives",
    "▧  Dosya türleri: Tümü": "▧  File types: All",
    "◷  En az 1 MB": "◷  Minimum 1 MB",
    "▣  {count} sürücü seçili": "▣  {count} drives selected",
    "▧  {count} uzantı seçili": "▧  {count} extensions selected",
    "◷  En az {amount} MB": "◷  Minimum {amount} MB",
    "Gizli / sistem dosyaları": "Include hidden / system files",
    "Taramayı başlat": "Start scan",
    "DOSYA": "FILES",
    "KLASÖR": "FOLDERS",
    "KOPYA GRUBU": "DUPLICATE GROUPS",
    "EŞLEŞEN DOSYA": "MATCHING FILES",
    "Sürücü seçin ve taramayı başlatın": "Select drives and start a scan",
    "Sonuçlar": "Results",
    "Kopyaları seç": "Select duplicates",
    "Orijinalleri koru": "Keep originals",
    "En eskiyi sil": "Delete oldest",
    "En yeniyi sil": "Delete newest",
    "Seçili dosyalar": "Selected files",
    "Yeniden adlandır": "Rename",
    "Taşı": "Move",
    "Çöp kutusuna gönder": "Move to Recycle Bin",
    "Henüz tarama sonucu yok": "No scan results yet",
    "Sürücüler taranıyor…": "Scanning drives…",
    "Eşleşen kopya bulunamadı": "No duplicate files found",
    "Taramayı durdur": "Stop scan",
    "Durduruluyor…": "Stopping…",
    "Dosyalar listeleniyor; sistem klasörleri atlanıyor": "Listing files; system folders are skipped",
    "İşlem hatası": "Operation error",
    "Dosya seçilmedi": "No files selected",
    "Önce işlem yapılacak dosyaları seçin.": "Select files to process first.",
    "Taşımak için dosya seçin.": "Select files to move.",
    "Tek dosya gerekli": "Select one file",
    "Yeniden adlandırmak için yalnızca bir dosya seçin.": "Select exactly one file to rename.",
    "Yeni dosya adı:": "New file name:",
    "Boyut filtresi": "Minimum size",
    "En küçük dosya boyutu (MB):": "Minimum file size (MB):",
    "Geçersiz değer": "Invalid value",
    "0 veya daha büyük bir MB değeri girin.": "Enter a value of 0 MB or greater.",
    "Dosya yeniden adlandırıldı.": "File renamed.",
    "Aç": "Open",
    "En eski": "Oldest",
    "En yeni": "Newest",
    "Dosya seçilmedi": "No files selected",
    "Önce işlem yapılacak dosyaları seçin.": "Select files to process first.",
    "Seçili dosyalar Çöp Kutusu'na gönderilsin mi?": "Move selected files to the Recycle Bin?",
    "Silme onayı": "Delete confirmation",
    "Taşıma onayı": "Move confirmation",
    "Hedef klasörü seç": "Select destination folder",
    "Yeniden adlandırma onayı": "Rename confirmation",
    "Dosya yeniden adlandırılsın mı?": "Rename this file?",
    "Tamamlandı": "Complete",
    "İşlem tamamlandı": "Operation complete",
    "Çöp Kutusu'na gönderildi": "moved to the Recycle Bin",
    "İşlem hatası": "Operation error",
    "Konum açılamadı": "Could not open location",
    "Sonuç yok": "No results",
    "Dışa aktarılacak kopya grubu bulunamadı.": "No duplicate groups to export.",
    "Raporu dışa aktar": "Export report",
    "dosyası": "file",
    "Dışa aktarıldı": "Exported",
    "Dışa aktarma başarısız": "Export failed",
    "Taşıma tamamlandı": "Move complete",
    "Her kopya grubundaki en eski oluşturulma tarihli dosyayı Çöp Kutusu'na göndermek istiyor musunuz?": "Move the oldest-created file in each duplicate group to the Recycle Bin?",
    "Her kopya grubundaki en yeni oluşturulma tarihli dosyayı Çöp Kutusu'na göndermek istiyor musunuz?": "Move the newest-created file in each duplicate group to the Recycle Bin?",
    "Seçili dosyalar Çöp Kutusu'na gönderilsin mi?": "Move selected files to the Recycle Bin?",
    "{count} seçili dosya buraya taşınsın mı?": "Move {count} selected files here?",
    "Dosya yeniden adlandırılsın mı?": "Rename this file?",
    "Dosya yeniden adlandırıldı.": "File renamed.",
    "{count} dosyada hata oluştu": "{count} file operation errors",
    "Taşıma tamamlandı": "Move complete",
    "Silme onayı": "Delete confirmation",
    "Taşıma onayı": "Move confirmation",
    "Yeniden adlandırma onayı": "Rename confirmation",
    "Dosyayı yeniden adlandır": "Rename file",
    "Dışa aktarma başarısız": "Export failed",
    "Yeniden adlandırma başarısız": "Rename failed",
    "Dosya yeniden adlandırıldı.": "File renamed.",
    "Çöp kutusuna gönderildi": "moved to the Recycle Bin",
    "Dosya seçilmedi": "No files selected",
    "Dosya sayısı: {count}": "Files: {count}",
    "Sürücüler": "Drives",
    "Tarama sürüyor  ·  {files} dosya  ·  {folders} klasör": "Scanning  ·  {files} files  ·  {folders} folders",
    "Ön filtrede {count} olası grup bulundu; içerikler karşılaştırılıyor": "Pre-filter found {count} candidate groups; comparing contents",
    "Hash hesaplanıyor  ·  {done} / {total} dosya": "Hashing  ·  {done} / {total} files",
    "{count} kopya grubu  ·  {matches} eşleşen dosya": "{count} duplicate groups  ·  {matches} matching files",
    "{size}  ·  {count} dosya  ·  {algorithm}": "{size}  ·  {count} files  ·  {algorithm}",
    "Oluşturulma: {created}  ·  Değiştirilme: {modified}": "Created: {created}  ·  Modified: {modified}",
    "Sayfa {page} / {pages}  ·  {count} dosya": "Page {page} / {pages}  ·  {count} files",
    "Sayfa 1 / 1  ·  0 dosya": "Page 1 / 1  ·  0 files",
    "{count} dosya Çöp Kutusu'na gönderildi.": "{count} files moved to the Recycle Bin.",
    "{count} dosya taşındı.": "{count} files moved.",
    "{count} dosyada hata oluştu:": "{count} file operation errors:",
    "Dosya yeniden adlandırılsın mı?": "Rename this file?",
    "Dosya yeniden adlandırıldı.": "File renamed.",
    "▶  Taramayı başlat": "▶  Start scan",
    "Taramayı durdur": "Stop scan",
}


def _translate_text(text: str, language: str) -> str:
    if language != "en":
        return text
    translated = ENGLISH_TEXT.get(text)
    if translated is not None:
        return translated
    patterns = (
        (r"Tarama sürüyor  ·  ([\d,]+) dosya  ·  ([\d,]+) klasör", "Scanning  ·  {} files  ·  {} folders"),
        (r"Ön filtrede ([\d,]+) olası grup bulundu; içerikler karşılaştırılıyor", "Pre-filter found {} candidate groups; comparing contents"),
        (r"Hash hesaplanıyor  ·  ([\d,]+) / ([\d,]+) dosya", "Hashing  ·  {} / {} files"),
        (r"([\d,]+) kopya grubu  ·  ([\d,]+) eşleşen dosya", "{} duplicate groups  ·  {} matching files"),
    )
    for pattern, template in patterns:
        match = re.fullmatch(pattern, text)
        if match:
            return template.format(*match.groups())
    return text


def _translate_widget_tree(widget, language: str) -> None:
    if language == "en":
        for option in ("text", "placeholder_text"):
            try:
                value = widget.cget(option)
                if isinstance(value, str):
                    translated = _translate_text(value, language)
                    if translated != value:
                        widget.configure(**{option: translated})
            except (AttributeError, KeyError, TclError, TypeError, ValueError):
                continue
    for child in widget.winfo_children():
        _translate_widget_tree(child, language)


def _format_size(size: int) -> str:
    value = float(size)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024 or unit == "TB":
            return f"{value:,.1f} {unit}"
        value /= 1024
    return f"{value:,.1f} TB"


class DrivePicker(ctk.CTkToplevel):
    def __init__(self, master: ctk.CTk, selected_roots: set[str], language: str = "tr"):
        super().__init__(master)
        self.language = language
        self.title(_translate_text("Sürücüleri seç", language))
        self.geometry("560x560")
        self.minsize(480, 440)
        self.configure(fg_color=PALETTE["canvas"])
        self.transient(master)
        self.grab_set()
        self.selected_roots: set[str] | None = None
        self.selected_before = {os.path.normcase(root) for root in selected_roots}
        has_removable_selection = any(
            drive.kind == "USB / Harici" and os.path.normcase(drive.root) in self.selected_before
            for drive in list_drives(include_removable=True)
        )
        self.include_removable = ctk.BooleanVar(value=has_removable_selection)
        self.drive_vars: dict[str, ctk.BooleanVar] = {}

        ctk.CTkLabel(self, text="Taranacak sürücüler", font=ctk.CTkFont("Segoe UI", 22, "bold"), text_color=PALETTE["ink"]).pack(anchor="w", padx=26, pady=(24, 4))
        ctk.CTkLabel(self, text="Sabit diskler varsayılan olarak seçilidir. Optik sürücüler taranmaz.", text_color=PALETTE["muted"]).pack(anchor="w", padx=26, pady=(0, 14))
        ctk.CTkCheckBox(
            self,
            text="USB / harici çıkarılabilir sürücüleri göster",
            variable=self.include_removable,
            command=self._render_drives,
            fg_color=PALETTE["green"],
            hover_color=PALETTE["green_dark"],
            text_color=PALETTE["ink"],
        ).pack(anchor="w", padx=26, pady=(0, 10))
        self.list_frame = ctk.CTkScrollableFrame(self, fg_color=PALETTE["panel"], corner_radius=16)
        self.list_frame.pack(fill="both", expand=True, padx=22, pady=(0, 16))
        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.pack(fill="x", padx=22, pady=(0, 20))
        ctk.CTkButton(footer, text="Vazgeç", fg_color=PALETTE["blue"], hover_color="#D5DFEA", text_color=PALETTE["ink"], command=self.destroy).pack(side="right", padx=(8, 0))
        ctk.CTkButton(footer, text="Sürücüleri uygula", fg_color=PALETTE["green"], hover_color=PALETTE["green_dark"], command=self._accept).pack(side="right")
        self._render_drives()
        _translate_widget_tree(self, self.language)

    def _render_drives(self) -> None:
        for child in self.list_frame.winfo_children():
            child.destroy()
        self.drive_vars.clear()
        drives = list_drives(include_removable=self.include_removable.get())
        if not drives:
            ctk.CTkLabel(self.list_frame, text=_translate_text("Kullanılabilir sürücü bulunamadı.", self.language), text_color=PALETTE["muted"]).pack(padx=16, pady=24)
            return
        for drive in drives:
            root_key = os.path.normcase(drive.root)
            default_selected = drive.kind == "Fixed"
            selected = root_key in self.selected_before if self.selected_before else default_selected
            variable = ctk.BooleanVar(value=selected)
            self.drive_vars[drive.root] = variable
            row = ctk.CTkFrame(self.list_frame, fg_color=PALETTE["canvas"], corner_radius=12)
            row.pack(fill="x", padx=10, pady=6)
            label = f"{drive.root}  {drive.label or _translate_text('Yerel disk', self.language)}"
            label = _translate_text(label, self.language)
            ctk.CTkCheckBox(row, text=label, variable=variable, fg_color=PALETTE["green"], hover_color=PALETTE["green_dark"], text_color=PALETTE["ink"]).pack(anchor="w", padx=14, pady=(10, 2))
            kind = _translate_text(drive.kind, self.language)
            free = "free" if self.language == "en" else "boş"
            ctk.CTkLabel(row, text=f"{kind}  ·  {_format_size(drive.free_bytes)} {free} / {_format_size(drive.total_bytes)}", text_color=PALETTE["muted"], font=ctk.CTkFont("Segoe UI", 11)).pack(anchor="w", padx=43, pady=(0, 10))
        _translate_widget_tree(self.list_frame, self.language)

    def _accept(self) -> None:
        self.selected_roots = {root for root, variable in self.drive_vars.items() if variable.get()}
        self.destroy()


class ExtensionPicker(ctk.CTkToplevel):
    def __init__(self, master: ctk.CTk, current: set[str] | None, language: str = "tr"):
        super().__init__(master)
        self.language = language
        self.title(_translate_text("Dosya türleri", language))
        self.geometry("560x650")
        self.minsize(480, 500)
        self.configure(fg_color=PALETTE["canvas"])
        self.transient(master)
        self.grab_set()
        self.extensions: set[str] | None = None
        self.applied = False
        self.all_var = ctk.BooleanVar(value=current is None)
        self.category_vars: dict[str, ctk.BooleanVar] = {}
        self.custom_entry: ctk.CTkEntry

        ctk.CTkLabel(self, text="Dosya türleri", font=ctk.CTkFont("Segoe UI", 22, "bold"), text_color=PALETTE["ink"]).pack(anchor="w", padx=26, pady=(24, 4))
        ctk.CTkLabel(self, text="Tüm uzantıları seçin veya yalnızca istediğiniz türleri işaretleyin.", text_color=PALETTE["muted"], wraplength=480, justify="left").pack(anchor="w", padx=26, pady=(0, 16))
        ctk.CTkCheckBox(self, text="Tüm uzantılar", variable=self.all_var, command=self._all_changed, fg_color=PALETTE["green"], hover_color=PALETTE["green_dark"], text_color=PALETTE["ink"]).pack(anchor="w", padx=28, pady=(0, 10))
        categories = ctk.CTkFrame(self, fg_color=PALETTE["panel"], corner_radius=16)
        categories.pack(fill="x", padx=22, pady=(0, 14))
        for category, values in EXTENSION_CATEGORIES.items():
            selected = current is not None and values.issubset(current)
            variable = ctk.BooleanVar(value=selected)
            self.category_vars[category] = variable
            category_label = _translate_text(category, self.language)
            ctk.CTkCheckBox(categories, text=f"{category_label}  ·  {', '.join(sorted(values))}", variable=variable, command=self._category_changed, fg_color=PALETTE["green"], hover_color=PALETTE["green_dark"], text_color=PALETTE["ink"]).pack(anchor="w", padx=18, pady=7)
        custom = ctk.CTkFrame(self, fg_color="transparent")
        custom.pack(fill="x", padx=24, pady=(0, 18))
        ctk.CTkLabel(custom, text="Diğer uzantılar", text_color=PALETTE["ink"]).pack(anchor="w", pady=(0, 6))
        self.custom_entry = ctk.CTkEntry(custom, placeholder_text=".iso, .dmg, .psd", height=40, corner_radius=12)
        self.custom_entry.pack(fill="x")
        self.custom_entry.bind("<KeyRelease>", self._custom_changed)
        if current is not None:
            known = set().union(*EXTENSION_CATEGORIES.values())
            custom_values = sorted(current - known)
            self.custom_entry.insert(0, ", ".join(custom_values))
        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.pack(fill="x", padx=22, pady=(0, 20))
        ctk.CTkButton(footer, text="Vazgeç", fg_color=PALETTE["blue"], hover_color="#D5DFEA", text_color=PALETTE["ink"], command=self.destroy).pack(side="right", padx=(8, 0))
        ctk.CTkButton(footer, text="Uygula", fg_color=PALETTE["green"], hover_color=PALETTE["green_dark"], command=self._accept).pack(side="right")
        _translate_widget_tree(self, self.language)

    def _all_changed(self) -> None:
        if self.all_var.get():
            for variable in self.category_vars.values():
                variable.set(False)
            self.custom_entry.delete(0, "end")

    def _category_changed(self) -> None:
        if any(variable.get() for variable in self.category_vars.values()):
            self.all_var.set(False)

    def _custom_changed(self, _event=None) -> None:
        if self.custom_entry.get().strip():
            self.all_var.set(False)

    def _accept(self) -> None:
        if self.all_var.get():
            self.extensions = None
        else:
            selected: set[str] = set()
            for category, variable in self.category_vars.items():
                if variable.get():
                    selected.update(EXTENSION_CATEGORIES[category])
            for item in self.custom_entry.get().split(","):
                extension = item.strip().casefold()
                if extension:
                    selected.add(extension if extension.startswith(".") else f".{extension}")
            self.extensions = selected
        self.applied = True
        self.destroy()


class DuplicateFinderApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode("light")
        self.language = "tr"
        self.title(_translate_text("Kopya Dosya Bulucu", self.language))
        self.iconbitmap(str(_resource_path("logo.ico")))
        self.geometry("1220x820")
        self.minsize(940, 680)
        self.configure(fg_color=PALETTE["canvas"])
        self.events: queue.Queue[tuple] = queue.Queue()
        self.candidate_queue: queue.Queue = queue.Queue()
        self.cancel_event = threading.Event()
        self.scan_thread: threading.Thread | None = None
        self.hash_thread: threading.Thread | None = None
        self.selected_roots: set[str] = set()
        self.extensions: set[str] | None = None
        self.groups: list[DuplicateGroup] = []
        self.selected_paths: set[str] = set()
        self.results_page = 0
        self.rows_per_page = 100
        self.progress_value = 0.0
        self.status_key = "Hazır"
        self.progress_text = "Sürücü seçin ve taramayı başlatın"
        self.file_count = 0
        self.folder_count = 0
        self.minimum_mb = 1.0
        self.include_hidden = ctk.BooleanVar(value=False)
        self.hash_algorithm = ctk.StringVar(value="SHA256")
        self.status_var = ctk.StringVar(value=self._t(self.status_key))
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self._build_interface()
        self.after(100, self._process_events)

    def _t(self, text: str) -> str:
        return _translate_text(text, self.language)

    def _build_interface(self) -> None:
        for child in self.winfo_children():
            child.destroy()
        self.status_var = ctk.StringVar(master=self, value=self._t(self.status_key))
        self.title(self._t("Kopya Dosya Bulucu"))
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self._build_sidebar()
        self._build_workspace()
        _translate_widget_tree(self, self.language)
        self.status_var.set(self._t(self.status_key))
        self.progress_label.configure(text=self._t(self.progress_text))
        self.progress.set(self.progress_value)
        if self.groups:
            self._render_groups()
        self._set_stats(self.file_count, self.folder_count, len(self.groups))

    def _select_language(self, value: str) -> None:
        language = "en" if value.endswith("EN") else "tr"
        if language == self.language:
            return
        self.language = language
        self._build_interface()

    def _build_sidebar(self) -> None:
        sidebar = ctk.CTkFrame(self, width=224, corner_radius=0, fg_color=PALETTE["sidebar"])
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_propagate(False)
        brand = ctk.CTkFrame(sidebar, fg_color="transparent")
        brand.pack(anchor="w", fill="x", padx=24, pady=(26, 38))
        self.logo_image = PhotoImage(file=str(_resource_path("logo.png"))).subsample(3, 3)
        ctk.CTkLabel(brand, image=self.logo_image, text="").pack(side="left", padx=(0, 10))
        ctk.CTkLabel(brand, text="DUPLI", font=ctk.CTkFont("Segoe UI", 24, "bold"), text_color=PALETTE["green_dark"]).pack(side="left")
        ctk.CTkLabel(sidebar, text="FILE STUDIO", font=ctk.CTkFont("Segoe UI", 10, "bold"), text_color=PALETTE["muted"]).pack(anchor="w", padx=86, pady=(0, 10))
        ctk.CTkLabel(sidebar, text="ÇALIŞMA ALANI", font=ctk.CTkFont("Segoe UI", 10, "bold"), text_color=PALETTE["muted"]).pack(anchor="w", padx=24, pady=(0, 10))
        self._side_item(sidebar, "◉", "Kopya dosyalar", active=True)
        self._side_item(sidebar, "▤", "Dışa aktarılanlar")
        spacer = ctk.CTkFrame(sidebar, fg_color="transparent")
        spacer.pack(expand=True, fill="both")
        ctk.CTkFrame(sidebar, height=1, fg_color="#D6E1D7").pack(fill="x", padx=22, pady=(0, 14))
        ctk.CTkLabel(sidebar, text="YEREL TARAMA", font=ctk.CTkFont("Segoe UI", 10, "bold"), text_color=PALETTE["muted"]).pack(anchor="w", padx=24, pady=(0, 6))
        ctk.CTkLabel(sidebar, text="Dosyalarınız cihazınızda kalır.", font=ctk.CTkFont("Segoe UI", 11), text_color=PALETTE["green_dark"]).pack(anchor="w", padx=24, pady=(0, 24))

    @staticmethod
    def _side_item(parent: ctk.CTkFrame, icon: str, label: str, active: bool = False) -> None:
        color = PALETTE["mint"] if active else "transparent"
        item = ctk.CTkFrame(parent, fg_color=color, corner_radius=12)
        item.pack(fill="x", padx=14, pady=3)
        ctk.CTkLabel(item, text=icon, width=28, text_color=PALETTE["green_dark"], font=ctk.CTkFont("Segoe UI", 16)).pack(side="left", padx=(8, 1), pady=10)
        ctk.CTkLabel(item, text=label, text_color=PALETTE["ink"], font=ctk.CTkFont("Segoe UI", 12, "bold" if active else "normal")).pack(side="left", padx=4, pady=10)

    def _build_workspace(self) -> None:
        workspace = ctk.CTkFrame(self, fg_color="transparent", corner_radius=0)
        workspace.grid(row=0, column=1, sticky="nsew", padx=30, pady=26)
        workspace.grid_columnconfigure(0, weight=1)
        workspace.grid_rowconfigure(4, weight=1)

        top = ctk.CTkFrame(workspace, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", pady=(0, 20))
        title_area = ctk.CTkFrame(top, fg_color="transparent")
        title_area.pack(side="left")
        ctk.CTkLabel(title_area, text="Kopya Dosya Bulucu", font=ctk.CTkFont("Segoe UI", 25, "bold"), text_color=PALETTE["ink"]).pack(anchor="w")
        ctk.CTkLabel(title_area, text="Aynı içerikli dosyaları güvenle inceleyin", font=ctk.CTkFont("Segoe UI", 12), text_color=PALETTE["muted"]).pack(anchor="w", pady=(3, 0))
        self.language_picker = ctk.CTkSegmentedButton(
            top,
            values=["🇹🇷 TR", "🇬🇧 EN"],
            command=self._select_language,
            selected_color=PALETTE["green"],
            selected_hover_color=PALETTE["green_dark"],
            unselected_color=PALETTE["canvas"],
            text_color=PALETTE["ink"],
            corner_radius=10,
            height=34,
        )
        self.language_picker.set("🇹🇷 TR" if self.language == "tr" else "🇬🇧 EN")
        self.language_picker.pack(side="right", padx=(10, 0), pady=4)
        self.status_pill = ctk.CTkLabel(top, textvariable=self.status_var, fg_color=PALETTE["mint"], text_color=PALETTE["green_dark"], corner_radius=16, padx=14, pady=8, font=ctk.CTkFont("Segoe UI", 11, "bold"))
        self.status_pill.pack(side="right", pady=4)

        options = ctk.CTkFrame(workspace, fg_color=PALETTE["panel"], corner_radius=18)
        options.grid(row=1, column=0, sticky="ew", pady=(0, 16))
        options.grid_columnconfigure(0, weight=1)
        settings_row = ctk.CTkFrame(options, fg_color="transparent")
        settings_row.pack(fill="x", padx=16, pady=(14, 10))
        self.drive_button = ctk.CTkButton(settings_row, text="▣  Sürücüler", command=self._choose_drives, fg_color=PALETTE["blue"], hover_color="#D5DFEA", text_color=PALETTE["ink"], corner_radius=11, height=38)
        self.drive_button.pack(side="left", padx=(0, 8))
        self.extension_button = ctk.CTkButton(settings_row, text="▧  Dosya türleri: Tümü", command=self._choose_extensions, fg_color=PALETTE["blue"], hover_color="#D5DFEA", text_color=PALETTE["ink"], corner_radius=11, height=38)
        self.extension_button.pack(side="left", padx=4)
        self.size_button = ctk.CTkButton(settings_row, text="◷  En az 1 MB", command=self._choose_minimum, fg_color=PALETTE["blue"], hover_color="#D5DFEA", text_color=PALETTE["ink"], corner_radius=11, height=38)
        self.size_button.pack(side="left", padx=4)
        ctk.CTkCheckBox(settings_row, text="Gizli / sistem dosyaları", variable=self.include_hidden, fg_color=PALETTE["green"], hover_color=PALETTE["green_dark"], text_color=PALETTE["ink"], font=ctk.CTkFont("Segoe UI", 11)).pack(side="left", padx=(14, 0))

        run_row = ctk.CTkFrame(options, fg_color="transparent")
        run_row.pack(fill="x", padx=16, pady=(0, 14))
        ctk.CTkLabel(run_row, text="HASH", text_color=PALETTE["muted"], font=ctk.CTkFont("Segoe UI", 10, "bold")).pack(side="left", padx=(2, 10))
        self.hash_picker = ctk.CTkSegmentedButton(run_row, values=["SHA256", "MD5"], variable=self.hash_algorithm, selected_color=PALETTE["green"], selected_hover_color=PALETTE["green_dark"], unselected_color=PALETTE["canvas"], text_color=PALETTE["ink"], corner_radius=10, height=34)
        self.hash_picker.pack(side="left")
        self.scan_button = ctk.CTkButton(run_row, text="▶  Taramayı başlat", command=self._toggle_scan, fg_color=PALETTE["green"], hover_color=PALETTE["green_dark"], corner_radius=11, height=40, font=ctk.CTkFont("Segoe UI", 12, "bold"))
        self.scan_button.pack(side="right")

        stats = ctk.CTkFrame(workspace, fg_color=PALETTE["panel"], corner_radius=16)
        stats.grid(row=2, column=0, sticky="ew", pady=(0, 14))
        self.file_stat = self._stat(stats, "DOSYA", "0", 0)
        self.folder_stat = self._stat(stats, "KLASÖR", "0", 1)
        self.group_stat = self._stat(stats, "KOPYA GRUBU", "0", 2)
        self.match_stat = self._stat(stats, "EŞLEŞEN DOSYA", "0", 3)
        for column in range(4):
            stats.grid_columnconfigure(column, weight=1)
            if column:
                ctk.CTkFrame(stats, width=1, height=40, fg_color=PALETTE["line"]).grid(row=0, column=column, sticky="w", pady=12)

        progress_row = ctk.CTkFrame(workspace, fg_color="transparent")
        progress_row.grid(row=3, column=0, sticky="ew", pady=(0, 12))
        self.progress = ctk.CTkProgressBar(progress_row, height=7, progress_color=PALETTE["green"], fg_color="#E2E9E2", corner_radius=8)
        self.progress.pack(fill="x", pady=(0, 6))
        self.progress.set(0)
        self.progress_label = ctk.CTkLabel(progress_row, text="Sürücü seçin ve taramayı başlatın", text_color=PALETTE["muted"], font=ctk.CTkFont("Segoe UI", 11))
        self.progress_label.pack(anchor="w")

        results_shell = ctk.CTkFrame(workspace, fg_color="transparent")
        results_shell.grid(row=4, column=0, sticky="nsew")
        results_shell.grid_columnconfigure(0, weight=1)
        results_shell.grid_rowconfigure(1, weight=1)
        toolbar = ctk.CTkFrame(results_shell, fg_color="transparent")
        toolbar.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        ctk.CTkLabel(toolbar, text="Sonuçlar", font=ctk.CTkFont("Segoe UI", 16, "bold"), text_color=PALETTE["ink"]).pack(side="left")
        self._toolbar_button(toolbar, "Kopyaları seç", self._select_duplicates).pack(side="right", padx=(6, 0))
        self._toolbar_button(toolbar, "Orijinalleri koru", self._keep_originals).pack(side="right", padx=(6, 0))
        self._toolbar_button(toolbar, "En eskiyi sil", lambda: self._delete_by_date(oldest=True)).pack(side="right", padx=(6, 0))
        self._toolbar_button(toolbar, "En yeniyi sil", lambda: self._delete_by_date(oldest=False)).pack(side="right", padx=(6, 0))
        self._toolbar_button(toolbar, "JSON", lambda: self._export(".json")).pack(side="right", padx=(6, 0))
        self._toolbar_button(toolbar, "CSV", lambda: self._export(".csv")).pack(side="right", padx=(6, 0))
        self._toolbar_button(toolbar, "TXT", lambda: self._export(".txt")).pack(side="right", padx=(6, 0))

        self.results = ctk.CTkScrollableFrame(results_shell, fg_color=PALETTE["canvas"], corner_radius=14)
        self.results.grid(row=1, column=0, sticky="nsew")
        pager = ctk.CTkFrame(results_shell, fg_color="transparent")
        pager.grid(row=2, column=0, sticky="ew", pady=(7, 0))
        self.previous_page_button = ctk.CTkButton(pager, text="‹", width=36, height=30, command=lambda: self._change_results_page(-1), fg_color=PALETTE["blue"], hover_color="#D5DFEA", text_color=PALETTE["ink"], corner_radius=9)
        self.previous_page_button.pack(side="left")
        self.page_label = ctk.CTkLabel(pager, text=self._t("Sayfa 1 / 1  ·  0 dosya"), text_color=PALETTE["muted"], font=ctk.CTkFont("Segoe UI", 10))
        self.page_label.pack(side="left", padx=10)
        self.next_page_button = ctk.CTkButton(pager, text="›", width=36, height=30, command=lambda: self._change_results_page(1), fg_color=PALETTE["blue"], hover_color="#D5DFEA", text_color=PALETTE["ink"], corner_radius=9)
        self.next_page_button.pack(side="left")
        actions = ctk.CTkFrame(workspace, fg_color=PALETTE["panel"], corner_radius=14)
        actions.grid(row=5, column=0, sticky="ew", pady=(12, 0))
        ctk.CTkLabel(actions, text="Seçili dosyalar", text_color=PALETTE["muted"], font=ctk.CTkFont("Segoe UI", 11)).pack(side="left", padx=14)
        ctk.CTkButton(actions, text="Yeniden adlandır", command=self._rename_selected, fg_color=PALETTE["blue"], hover_color="#D5DFEA", text_color=PALETTE["ink"], corner_radius=10, height=34).pack(side="right", padx=(6, 10), pady=8)
        ctk.CTkButton(actions, text="Taşı", command=self._move_selected, fg_color=PALETTE["blue"], hover_color="#D5DFEA", text_color=PALETTE["ink"], corner_radius=10, height=34).pack(side="right", padx=6, pady=8)
        ctk.CTkButton(actions, text="Çöp kutusuna gönder", command=self._delete_selected, fg_color=PALETTE["coral"], hover_color="#EBCFC5", text_color=PALETTE["coral_ink"], corner_radius=10, height=34).pack(side="right", padx=6, pady=8)
        self._show_empty()

    @staticmethod
    def _stat(parent: ctk.CTkFrame, label: str, value: str, column: int) -> ctk.CTkLabel:
        block = ctk.CTkFrame(parent, fg_color="transparent")
        block.grid(row=0, column=column, sticky="ew", padx=16, pady=11)
        ctk.CTkLabel(block, text=label, text_color=PALETTE["muted"], font=ctk.CTkFont("Segoe UI", 9, "bold")).pack(anchor="w")
        value_label = ctk.CTkLabel(block, text=value, text_color=PALETTE["ink"], font=ctk.CTkFont("Segoe UI", 19, "bold"))
        value_label.pack(anchor="w", pady=(1, 0))
        return value_label

    @staticmethod
    def _toolbar_button(parent: ctk.CTkFrame, label: str, command) -> ctk.CTkButton:
        return ctk.CTkButton(parent, text=label, command=command, fg_color=PALETTE["panel"], hover_color=PALETTE["mint"], border_width=1, border_color=PALETTE["line"], text_color=PALETTE["ink"], corner_radius=9, height=31, width=74, font=ctk.CTkFont("Segoe UI", 10))

    def _show_empty(self, text: str = "Henüz tarama sonucu yok") -> None:
        for child in self.results.winfo_children():
            child.destroy()
        empty = ctk.CTkFrame(self.results, fg_color=PALETTE["panel"], corner_radius=16)
        empty.pack(fill="x", padx=6, pady=6)
        ctk.CTkLabel(empty, text="⌕", font=ctk.CTkFont("Segoe UI", 30), text_color=PALETTE["green"]).pack(pady=(22, 4))
        ctk.CTkLabel(empty, text=self._t(text), font=ctk.CTkFont("Segoe UI", 14, "bold"), text_color=PALETTE["ink"]).pack(pady=(0, 22))

    def _choose_drives(self) -> None:
        dialog = DrivePicker(self, self.selected_roots, self.language)
        self.wait_window(dialog)
        if dialog.selected_roots is not None:
            self.selected_roots = dialog.selected_roots
            count = len(self.selected_roots)
            self.drive_button.configure(text=self._t("▣  {count} sürücü seçili").format(count=count))

    def _choose_extensions(self) -> None:
        dialog = ExtensionPicker(self, self.extensions, self.language)
        self.wait_window(dialog)
        if dialog.applied:
            self.extensions = dialog.extensions
            if self.extensions is None:
                self.extension_button.configure(text=self._t("▧  Dosya türleri: Tümü"))
            else:
                self.extension_button.configure(text=self._t("▧  {count} uzantı seçili").format(count=len(self.extensions)))

    def _choose_minimum(self) -> None:
        dialog = ctk.CTkInputDialog(text=self._t("En küçük dosya boyutu (MB):"), title=self._t("Boyut filtresi"))
        value = dialog.get_input()
        if value is None:
            return
        try:
            amount = float(value.replace(",", "."))
            if amount < 0:
                raise ValueError
        except ValueError:
            messagebox.showerror(self._t("Geçersiz değer"), self._t("0 veya daha büyük bir MB değeri girin."), parent=self)
            return
        self.minimum_mb = amount
        self.size_button.configure(text=self._t("◷  En az {amount} MB").format(amount=f"{amount:g}"))

    def _toggle_scan(self) -> None:
        if self._is_running():
            self.cancel_event.set()
            self.scan_button.configure(text=self._t("Durduruluyor…"), state="disabled")
            self.status_key = "Durduruluyor"
            self.status_var.set(self._t(self.status_key))
            return
        if not self.selected_roots:
            self._choose_drives()
        if not self.selected_roots:
            return
        self._start_scan()

    def _is_running(self) -> bool:
        return bool((self.scan_thread and self.scan_thread.is_alive()) or (self.hash_thread and self.hash_thread.is_alive()))

    def _start_scan(self) -> None:
        self.cancel_event.clear()
        self.candidate_queue = queue.Queue()
        self.groups = []
        self.selected_paths.clear()
        self.results_page = 0
        self.file_count = 0
        self.folder_count = 0
        self._set_stats(0, 0, 0)
        self._show_empty("Sürücüler taranıyor…")
        self.progress_value = 0
        self.progress.set(self.progress_value)
        self.scan_button.configure(text=self._t("Taramayı durdur"), state="normal")
        self.status_key = "Taranıyor"
        self.status_var.set(self._t(self.status_key))
        self.progress_text = "Dosyalar listeleniyor; sistem klasörleri atlanıyor"
        self.progress_label.configure(text=self._t(self.progress_text))
        roots = set(self.selected_roots)
        extensions = None if self.extensions is None else set(self.extensions)
        min_size_bytes = int(self.minimum_mb * 1024 * 1024)
        algorithm = self.hash_algorithm.get()
        include_hidden = self.include_hidden.get()
        self.hash_thread = threading.Thread(target=self._hash_worker, args=(algorithm,), daemon=True)
        self.scan_thread = threading.Thread(
            target=self._scan_worker,
            args=(roots, min_size_bytes, extensions, include_hidden),
            daemon=True,
        )
        self.hash_thread.start()
        self.scan_thread.start()

    def _scan_worker(self, roots: set[str], min_size: int, extensions: set[str] | None, include_hidden: bool) -> None:
        try:
            candidates = scan_files(
                roots,
                min_size,
                extensions,
                include_hidden,
                lambda files, folders: self.events.put(("scan_progress", files, folders)),
                self.cancel_event.is_set,
            )
            self.events.put(("scan_finished", len(candidates)))
            self.candidate_queue.put(candidates)
        except Exception as error:
            self.events.put(("error", str(error)))
            self.candidate_queue.put({})
        finally:
            self.candidate_queue.put(None)

    def _hash_worker(self, algorithm: str) -> None:
        candidates = self.candidate_queue.get()
        if candidates is None:
            return
        try:
            groups = find_duplicates(
                candidates,
                algorithm,
                lambda done, total: self.events.put(("hash_progress", done, total)),
                self.cancel_event.is_set,
            )
            self.events.put(("results", groups))
        except Exception as error:
            self.events.put(("error", str(error)))
        finally:
            self.events.put(("workers_finished",))

    def _process_events(self) -> None:
        try:
            processed_events = 0
            while processed_events < 100:
                event = self.events.get_nowait()
                processed_events += 1
                kind = event[0]
                if kind == "scan_progress":
                    self.file_count, self.folder_count = event[1], event[2]
                    self._set_stats(self.file_count, self.folder_count, len(self.groups))
                    self.progress_text = f"Tarama sürüyor  ·  {self.file_count:,} dosya  ·  {self.folder_count:,} klasör"
                    self.progress_label.configure(text=self._t(self.progress_text))
                elif kind == "scan_finished":
                    self.status_key = "Hash hesaplanıyor"
                    self.status_var.set(self._t(self.status_key))
                    self.progress_text = f"Ön filtrede {event[1]:,} olası grup bulundu; içerikler karşılaştırılıyor"
                    self.progress_label.configure(text=self._t(self.progress_text))
                    self.progress_value = 0
                    self.progress.set(self.progress_value)
                elif kind == "hash_progress":
                    completed, total = event[1], event[2]
                    self.progress_value = completed / total if total else 1
                    self.progress.set(self.progress_value)
                    self.progress_text = f"Hash hesaplanıyor  ·  {completed:,} / {total:,} dosya"
                    self.progress_label.configure(text=self._t(self.progress_text))
                elif kind == "results":
                    self.groups = event[1]
                    self._render_groups()
                    self._set_stats(self.file_count, self.folder_count, len(self.groups))
                elif kind == "error":
                    messagebox.showerror("İşlem hatası", event[1], parent=self)
                elif kind == "workers_finished":
                    self.scan_button.configure(text=self._t("▶  Taramayı başlat"), state="normal")
                    self.status_key = "Durduruldu" if self.cancel_event.is_set() else "Tamamlandı"
                    self.status_var.set(self._t(self.status_key))
                    total_matches = sum(len(group.files) for group in self.groups)
                    self.progress_text = f"{len(self.groups):,} kopya grubu  ·  {total_matches:,} eşleşen dosya"
                    self.progress_label.configure(text=self._t(self.progress_text))
                    self.progress_value = 1
                    self.progress.set(self.progress_value)
                    if not self.groups:
                        self._show_empty("Eşleşen kopya bulunamadı")
        except queue.Empty:
            pass
        self.after(100, self._process_events)

    def _set_stats(self, files: int, folders: int, groups: int) -> None:
        self.file_stat.configure(text=f"{files:,}")
        self.folder_stat.configure(text=f"{folders:,}")
        self.group_stat.configure(text=f"{groups:,}")
        self.match_stat.configure(text=f"{sum(len(group.files) for group in self.groups):,}")

    def _render_groups(self) -> None:
        for child in self.results.winfo_children():
            child.destroy()
        total_files = sum(len(group.files) for group in self.groups)
        page_count = max(1, (total_files + self.rows_per_page - 1) // self.rows_per_page)
        self.results_page = min(self.results_page, page_count - 1)
        page_start = self.results_page * self.rows_per_page
        page_end = min(page_start + self.rows_per_page, total_files)
        self.page_label.configure(
            text=self._t("Sayfa {page} / {pages}  ·  {count} dosya").format(
                page=self.results_page + 1,
                pages=page_count,
                count=total_files,
            )
        )
        self.previous_page_button.configure(state="normal" if self.results_page > 0 else "disabled")
        self.next_page_button.configure(state="normal" if self.results_page + 1 < page_count else "disabled")
        if not self.groups:
            self._show_empty("Eşleşen kopya bulunamadı")
            return
        file_offset = 0
        for group in self.groups:
            group_start = file_offset
            group_end = group_start + len(group.files)
            file_offset = group_end
            visible_start = max(page_start, group_start)
            visible_end = min(page_end, group_end)
            if visible_start >= visible_end:
                continue
            card = ctk.CTkFrame(self.results, fg_color=PALETTE["panel"], corner_radius=14)
            card.pack(fill="x", padx=4, pady=6)
            header = ctk.CTkFrame(card, fg_color="transparent")
            header.pack(fill="x", padx=15, pady=(12, 4))
            ctk.CTkLabel(header, text=f"{group.name}", text_color=PALETTE["ink"], font=ctk.CTkFont("Segoe UI", 13, "bold")).pack(side="left")
            header_text = self._t("{size}  ·  {count} dosya  ·  {algorithm}").format(
                size=_format_size(group.size), count=len(group.files), algorithm=group.algorithm
            )
            ctk.CTkLabel(header, text=header_text, text_color=PALETTE["muted"], font=ctk.CTkFont("Segoe UI", 10)).pack(side="right")
            for record in group.files[visible_start - group_start : visible_end - group_start]:
                row = ctk.CTkFrame(card, fg_color=PALETTE["canvas"], corner_radius=10)
                row.pack(fill="x", padx=12, pady=4)
                variable = ctk.BooleanVar(value=record.path in self.selected_paths)
                ctk.CTkCheckBox(
                    row,
                    text="",
                    width=24,
                    variable=variable,
                    command=lambda path=record.path, var=variable: self._toggle_path(path, var.get()),
                    fg_color=PALETTE["green"],
                    hover_color=PALETTE["green_dark"],
                ).pack(side="left", padx=(9, 1), pady=9)
                details = ctk.CTkFrame(row, fg_color="transparent")
                details.pack(side="left", fill="x", expand=True, padx=(4, 8), pady=5)
                ctk.CTkLabel(details, text=record.path, text_color=PALETTE["ink"], font=ctk.CTkFont("Segoe UI", 10), anchor="w").pack(fill="x")
                created = datetime.fromtimestamp(record.created).strftime("%Y-%m-%d %H:%M")
                modified = datetime.fromtimestamp(record.modified).strftime("%Y-%m-%d %H:%M")
                dates = self._t("Oluşturulma: {created}  ·  Değiştirilme: {modified}").format(created=created, modified=modified)
                ctk.CTkLabel(details, text=dates, text_color=PALETTE["muted"], font=ctk.CTkFont("Segoe UI", 9), anchor="w").pack(fill="x", pady=(2, 0))
                ctk.CTkButton(row, text=self._t("Aç"), width=48, height=28, corner_radius=8, fg_color=PALETTE["blue"], hover_color="#D5DFEA", text_color=PALETTE["ink"], command=lambda path=record.path: self._open_location(path)).pack(side="right", padx=9)

    def _change_results_page(self, offset: int) -> None:
        self.results_page = max(0, self.results_page + offset)
        self._render_groups()

    def _toggle_path(self, path: str, selected: bool) -> None:
        if selected:
            self.selected_paths.add(path)
        else:
            self.selected_paths.discard(path)

    def _select_duplicates(self) -> None:
        self.selected_paths.clear()
        for group in self.groups:
            if len(group.files) > 1:
                original = min(group.files, key=lambda record: record.created)
                self.selected_paths.update(record.path for record in group.files if record.path != original.path)
        self._render_groups()

    def _keep_originals(self) -> None:
        self._select_duplicates()

    def _delete_by_date(self, oldest: bool) -> None:
        selected: set[str] = set()
        for group in self.groups:
            if group.files:
                record = min(group.files, key=lambda item: item.created) if oldest else max(group.files, key=lambda item: item.created)
                selected.add(record.path)
        prompt = (
            "Her kopya grubundaki en eski oluşturulma tarihli dosyayı Çöp Kutusu'na göndermek istiyor musunuz?"
            if oldest
            else "Her kopya grubundaki en yeni oluşturulma tarihli dosyayı Çöp Kutusu'na göndermek istiyor musunuz?"
        )
        self._trash_paths(selected, prompt)

    def _selected(self) -> list[str]:
        return sorted(self.selected_paths)

    def _delete_selected(self) -> None:
        self._trash_paths(set(self._selected()), "Seçili dosyalar Çöp Kutusu'na gönderilsin mi?")

    def _trash_paths(self, paths: set[str], prompt: str) -> None:
        if not paths:
            messagebox.showinfo(self._t("Dosya seçilmedi"), self._t("Önce işlem yapılacak dosyaları seçin."), parent=self)
            return
        if not messagebox.askyesno(self._t("Silme onayı"), f"{self._t(prompt)}\n\n{self._t('Dosya sayısı: {count}').format(count=len(paths))}", parent=self):
            return
        removed: set[str] = set()
        errors: list[str] = []
        for path in sorted(paths):
            try:
                send_to_trash(path)
                removed.add(path)
                self.selected_paths.discard(path)
            except Exception as error:
                errors.append(f"{path}: {error}")
        self._remove_paths(removed)
        summary = self._t("{count} dosya Çöp Kutusu'na gönderildi.").format(count=len(removed))
        if errors:
            summary += f"\n\n{self._t('{count} dosyada hata oluştu:').format(count=len(errors))}\n" + "\n".join(errors[:5])
        messagebox.showinfo(self._t("İşlem tamamlandı"), summary, parent=self)

    def _move_selected(self) -> None:
        paths = self._selected()
        if not paths:
            messagebox.showinfo(self._t("Dosya seçilmedi"), self._t("Taşımak için dosya seçin."), parent=self)
            return
        destination = filedialog.askdirectory(title=self._t("Hedef klasörü seç"), parent=self)
        if not destination:
            return
        prompt = self._t("{count} seçili dosya buraya taşınsın mı?").format(count=len(paths))
        if not messagebox.askyesno(self._t("Taşıma onayı"), f"{prompt}\n\n{destination}", parent=self):
            return
        moved: set[str] = set()
        errors: list[str] = []
        for source in paths:
            try:
                move_file(source, destination)
                moved.add(source)
                self.selected_paths.discard(source)
            except Exception as error:
                errors.append(f"{source}: {error}")
        self._remove_paths(moved)
        self._show_action_summary("Taşıma tamamlandı", len(moved), errors)

    def _rename_selected(self) -> None:
        paths = self._selected()
        if len(paths) != 1:
            messagebox.showinfo(self._t("Tek dosya gerekli"), self._t("Yeniden adlandırmak için yalnızca bir dosya seçin."), parent=self)
            return
        source = paths[0]
        dialog = ctk.CTkInputDialog(text=self._t("Yeni dosya adı:"), title=self._t("Dosyayı yeniden adlandır"))
        new_name = dialog.get_input()
        if new_name is None or not new_name.strip():
            return
        if not messagebox.askyesno(self._t("Yeniden adlandırma onayı"), f"{self._t('Dosya yeniden adlandırılsın mı?')}\n\n{Path(source).name}  →  {new_name}", parent=self):
            return
        try:
            renamed = rename_file(source, new_name)
            self.selected_paths.discard(source)
            self._replace_path(source, renamed)
            self._render_groups()
            messagebox.showinfo(self._t("Tamamlandı"), self._t("Dosya yeniden adlandırıldı."), parent=self)
        except Exception as error:
            messagebox.showerror(self._t("Yeniden adlandırma başarısız"), str(error), parent=self)

    def _remove_paths(self, paths: set[str]) -> None:
        updated: list[DuplicateGroup] = []
        for group in self.groups:
            remaining = tuple(record for record in group.files if record.path not in paths)
            if len(remaining) > 1:
                updated.append(DuplicateGroup(group.name, group.size, group.algorithm, group.digest, remaining))
        self.groups = updated
        self._render_groups()
        self._set_stats(self.file_count, self.folder_count, len(self.groups))

    def _replace_path(self, old_path: str, new_path: str) -> None:
        updated: list[DuplicateGroup] = []
        for group in self.groups:
            records = tuple(
                type(record)(new_path, Path(new_path).name, record.size, record.created, record.modified)
                if record.path == old_path
                else record
                for record in group.files
            )
            updated.append(DuplicateGroup(group.name, group.size, group.algorithm, group.digest, records))
        self.groups = updated

    def _show_action_summary(self, title: str, count: int, errors: list[str]) -> None:
        text = self._t("{count} dosya taşındı.").format(count=count)
        if errors:
            text += f"\n\n{self._t('{count} dosyada hata oluştu:').format(count=len(errors))}\n" + "\n".join(errors[:5])
        messagebox.showinfo(self._t(title), text, parent=self)

    def _open_location(self, path: str) -> None:
        try:
            os.startfile(Path(path).parent)
        except OSError as error:
            messagebox.showerror(self._t("Konum açılamadı"), str(error), parent=self)

    def _export(self, extension: str) -> None:
        if not self.groups:
            messagebox.showinfo(self._t("Sonuç yok"), self._t("Dışa aktarılacak kopya grubu bulunamadı."), parent=self)
            return
        destination = filedialog.asksaveasfilename(
            title=self._t("Raporu dışa aktar"),
            defaultextension=extension,
            filetypes=[(f"{extension[1:].upper()} {self._t('dosyası')}", f"*{extension}")],
            parent=self,
        )
        if not destination:
            return
        try:
            export_results(self.groups, destination)
            messagebox.showinfo(self._t("Dışa aktarıldı"), f"{self._t('Rapor kaydedildi:')}\n{destination}", parent=self)
        except OSError as error:
            messagebox.showerror(self._t("Dışa aktarma başarısız"), str(error), parent=self)

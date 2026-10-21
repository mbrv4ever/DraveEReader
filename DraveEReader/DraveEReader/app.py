# -*- coding: utf-8 -*-
"""
DraveEReader - e-boeklezer & voorlezer (Dravenlock)

Een offline, toegankelijke donationware-app die zo goed als elk e-boekformaat
leest (EPUB, MOBI, AZW/AZW3, FB2, CBZ, PDF, XPS, TXT, HTML en afbeeldingen) en
de tekst kan voorlezen met een natuurlijke neurale stem (neuvoice).

Huisstijl: donker thema, grote knoppen, hoog contrast, instelbare lettergrootte.
Nederlands als basis met OS-taaldetectie en handmatige keuze (NL/EN).

Donatie: https://paypal.me/roger076   -   service@dravenlock.nl
"""
from __future__ import annotations

import os
import re
import sys
import json
import time
import tempfile
import threading

from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QSize, QLocale
from PyQt6.QtGui import (QIcon, QPixmap, QImage, QColor, QFont, QTextCharFormat,
                         QTextCursor, QKeySequence, QShortcut, QAction)
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QStackedWidget, QLabel, QPushButton,
    QVBoxLayout, QHBoxLayout, QGridLayout, QScrollArea, QTextEdit, QListWidget,
    QListWidgetItem, QFileDialog, QDialog, QComboBox, QSlider, QCheckBox,
    QInputDialog, QMessageBox, QFrame, QSizePolicy, QTextBrowser, QSpinBox,
)

try:
    import fitz  # PyMuPDF
except Exception as _e:  # noqa: BLE001
    fitz = None

from tts import TtsEngine

APP_NAME = "DraveEReader"
APP_VERSION = "0.1.6"
DONATIE_URL = "https://paypal.me/roger076"
CONTACT = "service@dravenlock.nl"

# ----------------------------------------------------------------------------
# Donker Dravenlock-palet
# ----------------------------------------------------------------------------
BG      = "#0e0e11"
PANEL   = "#16161b"
PANEL2  = "#1c1c22"
LINE    = "#2c2c34"
TEXT    = "#e0e0e4"
MUTED   = "#8c8c96"
ACCENT  = "#6fa3d6"
GOLD    = "#d4af5a"
GOOD    = "#7fb069"
WARN    = "#d68a6f"
# Lichte leesvlakken
READ_BG = {
    "donker": ("#15151a", "#e6e6ea"),
    "sepia":  ("#f3e9d2", "#3a2f1c"),
    "licht":  ("#f4f4f2", "#101012"),
}

SUPPORTED = (".epub", ".mobi", ".azw", ".azw3", ".prc", ".fb2", ".cbz",
             ".pdf", ".xps", ".oxps", ".txt", ".htm", ".html",
             ".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tiff")


# ----------------------------------------------------------------------------
# Bestandslocaties (ook correct in de .exe)
# ----------------------------------------------------------------------------
def resource_path(rel: str) -> str:
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, rel)


def config_dir() -> str:
    if sys.platform.startswith("win"):
        root = os.environ.get("APPDATA", os.path.expanduser("~"))
    elif sys.platform == "darwin":
        root = os.path.expanduser("~/Library/Application Support")
    else:
        root = os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))
    d = os.path.join(root, APP_NAME)
    os.makedirs(d, exist_ok=True)
    return d


CONFIG_PATH = os.path.join(config_dir(), "config.json")

DEFAULT_CONFIG = {
    "lang": "",           # "" = volg OS
    "font_size": 22,
    "read_bg": "donker",
    "voice": "",
    "speed": 1.05,
    "steps": 8,
    "sound": True,
    "auto_next": True,    # automatisch doorlezen naar volgende pagina
    "recent": [],         # [{path,title,page,total,ts}]
    "voices_cache": [],   # onthouden stemnamen (na 1x laden), voor de keuzelijst
}


def load_config() -> dict:
    cfg = dict(DEFAULT_CONFIG)
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg.update(json.load(f))
    except Exception:
        pass
    return cfg


def save_config(cfg: dict) -> None:
    try:
        tmp = CONFIG_PATH + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
        os.replace(tmp, CONFIG_PATH)
    except Exception:
        pass


# ----------------------------------------------------------------------------
# Taal (i18n) - NL basis + EN, OS-detectie + handmatige keuze
# ----------------------------------------------------------------------------
def detect_os_lang() -> str:
    try:
        name = QLocale.system().name().lower()  # bv. "nl_nl"
    except Exception:
        name = "nl"
    if name.startswith("en"):
        return "en"
    return "nl"  # Nederlands is de basis/fallback


TR = {
    "bibliotheek": {"nl": "Bibliotheek", "en": "Library"},
    "boek_openen": {"nl": "Boek openen...", "en": "Open book..."},
    "recent": {"nl": "Onlangs geopend", "en": "Recently opened"},
    "geen_recent": {"nl": "Nog geen boeken geopend.", "en": "No books opened yet."},
    "instellingen": {"nl": "Instellingen", "en": "Settings"},
    "snelgids": {"nl": "Snelgids", "en": "Quick guide"},
    "donatie": {"nl": "Donatie", "en": "Donate"},
    "vorige": {"nl": "Vorige", "en": "Previous"},
    "volgende": {"nl": "Volgende", "en": "Next"},
    "hoofdstukken": {"nl": "Hoofdstukken", "en": "Chapters"},
    "ga_naar": {"nl": "Ga naar...", "en": "Go to..."},
    "kleiner": {"nl": "Letter kleiner", "en": "Smaller text"},
    "groter": {"nl": "Letter groter", "en": "Larger text"},
    "weergave_tekst": {"nl": "Weergave: Tekst", "en": "View: Text"},
    "weergave_pagina": {"nl": "Weergave: Pagina", "en": "View: Page"},
    "voorlezen": {"nl": "Voorlezen", "en": "Read aloud"},
    "stop": {"nl": "Stop", "en": "Stop"},
    "pagina": {"nl": "Pagina", "en": "Page"},
    "van": {"nl": "van", "en": "of"},
    "taal": {"nl": "Taal", "en": "Language"},
    "taal_os": {"nl": "Volg computer", "en": "Follow computer"},
    "lettergrootte": {"nl": "Lettergrootte", "en": "Text size"},
    "leesachtergrond": {"nl": "Leesachtergrond", "en": "Reading background"},
    "stem": {"nl": "Stem", "en": "Voice"},
    "snelheid": {"nl": "Spreeksnelheid", "en": "Speaking speed"},
    "kwaliteit": {"nl": "Stemkwaliteit", "en": "Voice quality"},
    "geluid_aan": {"nl": "Geluid aan", "en": "Sound on"},
    "doorlezen": {"nl": "Automatisch doorlezen naar volgende pagina",
                  "en": "Automatically continue to next page"},
    "sluiten": {"nl": "Sluiten", "en": "Close"},
    "opslaan": {"nl": "Opslaan", "en": "Save"},
    "ga_pagina": {"nl": "Ga naar pagina", "en": "Go to page"},
    "geen_tekst": {"nl": "Geen tekst om voor te lezen op deze pagina.",
                   "en": "No text to read on this page."},
    "stem_laden": {"nl": "Stem voorbereiden...", "en": "Preparing voice..."},
    "stem_fout": {"nl": "Stem niet beschikbaar", "en": "Voice unavailable"},
    "openen_fout": {"nl": "Kon dit bestand niet openen", "en": "Could not open this file"},
    "klaar": {"nl": "Klaar", "en": "Ready"},
    "voorlezen_bezig": {"nl": "Aan het voorlezen...", "en": "Reading aloud..."},
    "titel_app": {"nl": "DraveEReader - e-boeklezer & voorlezer",
                  "en": "DraveEReader - e-book reader & narrator"},
    "ondertitel": {"nl": "Lees en laat elk e-boek voorlezen",
                   "en": "Read and have any e-book read aloud"},
    "auto_next_kort": {"nl": "Doorlezen", "en": "Continue"},
    "stemmen_laden": {"nl": "Stemmen laden", "en": "Load voices"},
    "stemmen_verversen": {"nl": "Stemmen verversen", "en": "Refresh voices"},
    "stemmen_bezig": {"nl": "Stemmen ophalen (eerste keer: downloaden)...",
                      "en": "Fetching voices (first time: downloading)..."},
    "stemmen_klaar": {"nl": "%d stemmen geladen", "en": "%d voices loaded"},
    "stemmen_fout": {"nl": "Stemmen ophalen mislukt",
                     "en": "Could not fetch voices"},
    "voice_auto": {"nl": "(automatisch - standaardstem)",
                   "en": "(automatic - default voice)"},
    "test_stem": {"nl": "Test stem", "en": "Test voice"},
    "test_bezig": {"nl": "Stem testen...", "en": "Testing voice..."},
    "test_zin": {"nl": "Dit is een test van de gekozen stem.",
                 "en": "This is a test of the selected voice."},
    "pauze": {"nl": "Pauze", "en": "Pause"},
    "hervat": {"nl": "Hervat", "en": "Resume"},
    "gepauzeerd": {"nl": "Gepauzeerd", "en": "Paused"},
    "lees_vanaf": {"nl": "Voorlezen vanaf de aangeklikte plek",
                   "en": "Read aloud from the clicked position"},
}

_LANG = "nl"


def set_lang(code: str):
    global _LANG
    _LANG = code if code in ("nl", "en") else "nl"


def t(key: str) -> str:
    d = TR.get(key, {})
    return d.get(_LANG, d.get("nl", key))


# ----------------------------------------------------------------------------
# Zinnen splitsen (met posities, voor markeren tijdens voorlezen)
# ----------------------------------------------------------------------------
_CLOSERS = '")]\u201d\u2019\u00bb'


def split_sentences(text: str):
    spans = []
    n = len(text)
    i = 0
    start = 0
    while i < n:
        ch = text[i]
        if ch in ".!?":
            j = i + 1
            while j < n and text[j] in _CLOSERS:
                j += 1
            seg = text[start:j]
            if seg.strip():
                spans.append((start, j, seg.strip()))
            while j < n and text[j] in " \t\r\n":
                j += 1
            start = j
            i = j
            continue
        if ch == "\n" and i + 1 < n and text[i + 1] == "\n":
            seg = text[start:i]
            if seg.strip():
                spans.append((start, i, seg.strip()))
            j = i
            while j < n and text[j] in " \t\r\n":
                j += 1
            start = j
            i = j
            continue
        i += 1
    if start < n:
        seg = text[start:n]
        if seg.strip():
            spans.append((start, n, seg.strip()))
    return spans


# ----------------------------------------------------------------------------
# Boek-motor (rond PyMuPDF)
# ----------------------------------------------------------------------------
REF_PAPER = "a5"
REF_FONT = 11


class Book:
    def __init__(self):
        self.doc = None
        self.path = ""
        self.title = ""
        self.count = 0
        self.toc = []
        self.reflowable = False
        self._tmpdir = None

    def open(self, path: str):
        if fitz is None:
            raise RuntimeError("PyMuPDF ontbreekt.")
        self.path = path
        ext = os.path.splitext(path)[1].lower()
        doc = None
        try:
            doc = fitz.open(path)
        except Exception:
            doc = None
        if doc is None and ext in (".azw", ".azw3", ".mobi", ".prc"):
            doc = self._open_via_mobi(path)
        if doc is None:
            # laatste poging: als tekst inlezen
            try:
                data = open(path, "rb").read()
                doc = fitz.open(stream=data, filetype="txt")
            except Exception as e:  # noqa: BLE001
                raise RuntimeError(str(e))
        self.doc = doc
        self.reflowable = bool(getattr(doc, "is_reflowable", False))
        if self.reflowable:
            try:
                doc.layout(rect=fitz.paper_rect(REF_PAPER), fontsize=REF_FONT)
            except Exception:
                pass
        self.count = doc.page_count
        try:
            self.toc = doc.get_toc() or []
        except Exception:
            self.toc = []
        meta = {}
        try:
            meta = doc.metadata or {}
        except Exception:
            meta = {}
        self.title = (meta.get("title") or "").strip() or \
            os.path.splitext(os.path.basename(path))[0]

    def _open_via_mobi(self, path):
        try:
            import mobi
        except Exception:
            return None
        try:
            tdir, fp = mobi.extract(path)
            self._tmpdir = tdir
            return fitz.open(fp)
        except Exception:
            return None

    def page_text(self, idx: int) -> str:
        if not self.doc or idx < 0 or idx >= self.count:
            return ""
        try:
            txt = self.doc[idx].get_text("text") or ""
        except Exception:
            txt = ""
        # nette witruimte
        txt = txt.replace("\r\n", "\n").replace("\r", "\n")
        txt = re.sub(r"[ \t]+\n", "\n", txt)
        txt = re.sub(r"\n{3,}", "\n\n", txt)
        return txt.strip("\n")

    def page_pixmap(self, idx: int, zoom: float = 1.4) -> QPixmap:
        if not self.doc or idx < 0 or idx >= self.count:
            return QPixmap()
        try:
            page = self.doc[idx]
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            img = QImage(pix.samples, pix.width, pix.height, pix.stride,
                         QImage.Format.Format_RGB888)
            return QPixmap.fromImage(img.copy())
        except Exception:
            return QPixmap()

    def close(self):
        try:
            if self.doc:
                self.doc.close()
        except Exception:
            pass
        self.doc = None
        if self._tmpdir:
            import shutil
            try:
                shutil.rmtree(self._tmpdir, ignore_errors=True)
            except Exception:
                pass
            self._tmpdir = None


# ----------------------------------------------------------------------------
# Voorlees-werker (achtergrondthread)
# ----------------------------------------------------------------------------
class VoorleesWorker(QThread):
    sentence = pyqtSignal(int)     # index van huidige zin
    page_done = pyqtSignal()       # pagina volledig voorgelezen
    status = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(self, engine: TtsEngine, sentences, lang, voice, steps, speed,
                 start_index=0):
        super().__init__()
        self.engine = engine
        self.sentences = sentences
        self.lang = lang
        self.voice = voice
        self.steps = steps
        self.speed = speed
        self.start_index = max(0, int(start_index))
        self._stop = threading.Event()
        self._pause = threading.Event()

    def stop(self):
        self._stop.set()
        self._pause.clear()  # zodat een wachtende lus kan stoppen

    def pause(self):
        self._pause.set()

    def resume(self):
        self._pause.clear()

    def is_paused(self) -> bool:
        return self._pause.is_set()

    def run(self):
        if not self.engine.ensure_ready(self.status.emit):
            self.failed.emit(self.engine.last_error or t("stem_fout"))
            return
        winsound = None
        if sys.platform.startswith("win"):
            try:
                import winsound as _ws
                winsound = _ws
            except Exception:
                winsound = None
        i = self.start_index
        n = len(self.sentences)
        while i < n:
            if self._stop.is_set():
                break
            # wachten zolang gepauzeerd
            while self._pause.is_set() and not self._stop.is_set():
                time.sleep(0.05)
            if self._stop.is_set():
                break
            text = self.sentences[i].strip()
            if not text:
                i += 1
                continue
            try:
                tmp = os.path.join(tempfile.gettempdir(),
                                   "draveereader_tts_%d.wav" % (i % 2))
                dur = self.engine.synth_to_wav(
                    text, tmp, self.lang, self.voice, self.steps, self.speed)
            except Exception:
                i += 1
                continue
            if self._stop.is_set():
                break
            if self._pause.is_set():
                # tijdens synthese gepauzeerd: dezelfde zin straks opnieuw
                continue
            self.sentence.emit(i)
            res = self._play(tmp, dur, winsound)
            if res == "pause":
                continue          # na hervatten dezelfde zin opnieuw
            if res == "stop" or self._stop.is_set():
                break
            i += 1
        if not self._stop.is_set():
            self.page_done.emit()

    def _play(self, path, dur, winsound):
        if winsound is not None:
            try:
                winsound.PlaySound(path, winsound.SND_FILENAME | winsound.SND_ASYNC)
            except Exception:
                pass
            end = time.time() + dur + 0.15
            while time.time() < end:
                if self._stop.is_set():
                    self._purge(winsound)
                    return "stop"
                if self._pause.is_set():
                    self._purge(winsound)
                    return "pause"
                time.sleep(0.04)
        else:
            # andere omgeving (bv. testsandbox): korte wachttijd, geen audio
            end = time.time() + min(dur, 0.25)
            while time.time() < end:
                if self._stop.is_set():
                    return "stop"
                if self._pause.is_set():
                    return "pause"
                time.sleep(0.04)
        return None

    @staticmethod
    def _purge(winsound):
        try:
            winsound.PlaySound(None, winsound.SND_PURGE)
        except Exception:
            pass


# ----------------------------------------------------------------------------
# Stijl & hulpjes
# ----------------------------------------------------------------------------
def _spin_arrows_dir() -> str:
    """Maak kleine, goed zichtbare op/neer-pijltjes voor de QSpinBox-knoppen.

    Geeft de map terug (met up.png/down.png). Zonder Pillow: lege string.
    """
    try:
        from PIL import Image, ImageDraw
    except Exception:
        return ""
    d = os.path.join(config_dir(), "ui")
    os.makedirs(d, exist_ok=True)
    up = os.path.join(d, "spin_up.png")
    down = os.path.join(d, "spin_down.png")
    try:
        W = H = 24
        col = (16, 16, 18, 255)  # donkere driehoek op transparant
        imu = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(imu).polygon([(5, 16), (19, 16), (12, 6)], fill=col)
        imu.save(up)
        imd = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(imd).polygon([(5, 8), (19, 8), (12, 18)], fill=col)
        imd.save(down)
        return d.replace("\\", "/")
    except Exception:
        return ""


def build_qss() -> str:
    _ad = _spin_arrows_dir()
    if _ad:
        _arrows = (
            "QSpinBox::up-arrow {{ image: url('%s/spin_up.png'); width: 16px; height: 16px; }}\n"
            "    QSpinBox::down-arrow {{ image: url('%s/spin_down.png'); width: 16px; height: 16px; }}"
            % (_ad, _ad)
        ).replace("{{", "{").replace("}}", "}")
    else:
        _arrows = ""
    return f"""
    QWidget {{ background: {BG}; color: {TEXT}; font-size: 15px; }}
    QMainWindow, QDialog {{ background: {BG}; }}
    QPushButton {{ background: {PANEL2}; color: {TEXT}; border: 2px solid {LINE};
        border-radius: 10px; padding: 12px 16px; font-size: 16px; }}
    QPushButton:hover {{ border-color: {ACCENT}; }}
    QPushButton:pressed {{ background: {PANEL}; }}
    QPushButton:focus {{ border-color: {ACCENT}; outline: none; }}
    QPushButton:disabled {{ color: {MUTED}; border-color: {LINE}; }}
    QPushButton#primary {{ background: {ACCENT}; color: #0e0e11; font-weight: bold;
        border: 2px solid {ACCENT}; }}
    QPushButton#primary:hover {{ background: #8bb8e2; border-color: #8bb8e2; }}
    QPushButton#donate {{ border-color: {WARN}; color: {WARN}; }}
    QPushButton#reading {{ background: {GOOD}; color: #0e0e11; font-weight: bold;
        border: 2px solid {GOOD}; }}
    QListWidget {{ background: {PANEL}; border: 1px solid {LINE}; border-radius: 8px;
        font-size: 16px; }}
    QListWidget::item {{ padding: 12px 10px; border-bottom: 1px solid {LINE}; }}
    QListWidget::item:selected {{ background: {ACCENT}; color: #0e0e11; }}
    QComboBox, QSpinBox {{ background: #d6d6d6; color: #101012; border: 1px solid {LINE};
        border-radius: 6px; padding: 7px 10px; font-size: 16px; min-height: 26px; }}
    QComboBox::drop-down {{ width: 26px; }}
    QSpinBox {{ padding-right: 34px; }}
    QSpinBox::up-button {{ subcontrol-origin: border; subcontrol-position: top right;
        width: 30px; background: #c4c4c4;
        border-left: 1px solid {LINE}; border-top-right-radius: 6px; }}
    QSpinBox::down-button {{ subcontrol-origin: border; subcontrol-position: bottom right;
        width: 30px; background: #c4c4c4;
        border-left: 1px solid {LINE}; border-bottom-right-radius: 6px; }}
    QSpinBox::up-button:hover, QSpinBox::down-button:hover {{ background: {ACCENT}; }}
    QSpinBox::up-button:pressed, QSpinBox::down-button:pressed {{ background: #9bbfe0; }}
    {_arrows}
    QComboBox QAbstractItemView {{ background: #f4f4f2; color: #101012;
        selection-background-color: {ACCENT}; selection-color: #0e0e11; }}
    QLabel {{ color: {TEXT}; }}
    QLabel#muted {{ color: {MUTED}; }}
    QLabel#title {{ font-size: 30px; font-weight: bold; color: {TEXT}; }}
    QLabel#h2 {{ font-size: 19px; font-weight: bold; color: {ACCENT}; }}
    QSlider::groove:horizontal {{ height: 8px; background: {LINE}; border-radius: 4px; }}
    QSlider::sub-page:horizontal {{ background: {ACCENT}; border-radius: 4px; }}
    QSlider::handle:horizontal {{ background: {ACCENT}; width: 22px; height: 22px;
        margin: -8px 0; border-radius: 11px; }}
    QCheckBox {{ font-size: 16px; spacing: 10px; }}
    QCheckBox::indicator {{ width: 24px; height: 24px; border: 2px solid {LINE};
        border-radius: 5px; background: #d6d6d6; }}
    QCheckBox::indicator:checked {{ background: {ACCENT}; border-color: {ACCENT}; }}
    QScrollBar:vertical {{ background: {PANEL}; width: 16px; margin: 0; }}
    QScrollBar::handle:vertical {{ background: #3a3a44; border-radius: 8px; min-height: 36px; }}
    QScrollBar::handle:vertical:hover {{ background: {ACCENT}; }}
    QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
    QScrollBar:horizontal {{ background: {PANEL}; height: 16px; }}
    QScrollBar::handle:horizontal {{ background: #3a3a44; border-radius: 8px; min-width: 36px; }}
    QFrame#bar {{ background: {PANEL}; border-bottom: 1px solid {LINE}; }}
    QFrame#bottombar {{ background: {PANEL}; border-top: 1px solid {LINE}; }}
    QToolTip {{ background: {PANEL2}; color: {TEXT}; border: 1px solid {ACCENT};
        padding: 6px; font-size: 14px; }}
    """


def on_click(btn: QPushButton, fn):
    # 'clicked' geeft een bool door -> vang die af (PyQt6-valkuil)
    btn.clicked.connect(lambda *_a, a=fn: a())


def make_button(text: str, tip: str = "", obj: str = "") -> QPushButton:
    b = QPushButton(text)
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    if tip:
        b.setToolTip(tip)
    if obj:
        b.setObjectName(obj)
    b.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
    return b


# ----------------------------------------------------------------------------
# Stemmen laden op de achtergrond (downloadt het model zo nodig)
# ----------------------------------------------------------------------------
class VoiceLoader(QThread):
    done = pyqtSignal(list)         # lijst stemnamen bij succes
    failed = pyqtSignal(str)
    status = pyqtSignal(str)

    def __init__(self, engine: TtsEngine):
        super().__init__()
        self.engine = engine

    def run(self):
        try:
            ok = self.engine.ensure_ready(lambda m: self.status.emit(m))
        except Exception as e:  # noqa: BLE001
            self.failed.emit(str(e))
            return
        if ok and self.engine.voices:
            self.done.emit(list(self.engine.voices))
        else:
            self.failed.emit(self.engine.last_error or t("stemmen_fout"))


class VoiceTester(QThread):
    """Synthetiseert een korte testzin met de gekozen stem en speelt die af."""
    done = pyqtSignal(list)        # eventueel bijgewerkte stemlijst
    failed = pyqtSignal(str)
    status = pyqtSignal(str)

    def __init__(self, engine: TtsEngine, voice, lang, steps, speed):
        super().__init__()
        self.engine = engine
        self.voice = voice
        self.lang = lang
        self.steps = steps
        self.speed = speed

    def run(self):
        try:
            if not self.engine.ensure_ready(lambda m: self.status.emit(m)):
                self.failed.emit(self.engine.last_error or t("stemmen_fout"))
                return
            tmp = os.path.join(tempfile.gettempdir(), "draveereader_test.wav")
            dur = self.engine.synth_to_wav(
                t("test_zin"), tmp, self.lang, self.voice,
                int(self.steps), float(self.speed))
        except Exception as e:  # noqa: BLE001
            self.failed.emit(str(e))
            return
        # afspelen (op Windows via winsound; elders stil)
        if sys.platform.startswith("win"):
            try:
                import winsound
                winsound.PlaySound(tmp, winsound.SND_FILENAME | winsound.SND_ASYNC)
                end = time.time() + dur + 0.15
                while time.time() < end:
                    time.sleep(0.05)
            except Exception:
                pass
        self.done.emit(list(self.engine.voices))


# ----------------------------------------------------------------------------
# Instellingen-dialoog
# ----------------------------------------------------------------------------
class SettingsDialog(QDialog):
    def __init__(self, parent, cfg, voices, engine=None):
        super().__init__(parent)
        self.engine = engine
        self._loader = None
        self._tester = None
        self.setWindowTitle(t("instellingen"))
        self.setMinimumWidth(600)
        self.cfg = dict(cfg)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(22, 22, 22, 22)
        lay.setSpacing(14)

        head = QLabel(t("instellingen"))
        head.setObjectName("title")
        lay.addWidget(head)

        grid = QGridLayout()
        grid.setVerticalSpacing(14)
        grid.setHorizontalSpacing(16)
        r = 0

        grid.addWidget(QLabel(t("taal") + ":"), r, 0)
        self.cb_lang = QComboBox()
        self.cb_lang.addItem(t("taal_os"), "")
        self.cb_lang.addItem("Nederlands", "nl")
        self.cb_lang.addItem("English", "en")
        idx = {"": 0, "nl": 1, "en": 2}.get(cfg.get("lang", ""), 0)
        self.cb_lang.setCurrentIndex(idx)
        grid.addWidget(self.cb_lang, r, 1)
        r += 1

        grid.addWidget(QLabel(t("lettergrootte") + ":"), r, 0)
        self.sp_font = QSpinBox()
        self.sp_font.setRange(14, 48)
        self.sp_font.setValue(int(cfg.get("font_size", 22)))
        self.sp_font.setSuffix(" px")
        grid.addWidget(self.sp_font, r, 1)
        r += 1

        grid.addWidget(QLabel(t("leesachtergrond") + ":"), r, 0)
        self.cb_bg = QComboBox()
        for key in ("donker", "sepia", "licht"):
            self.cb_bg.addItem(key.capitalize(), key)
        self.cb_bg.setCurrentIndex(["donker", "sepia", "licht"].index(
            cfg.get("read_bg", "donker")))
        grid.addWidget(self.cb_bg, r, 1)
        r += 1

        grid.addWidget(QLabel(t("stem") + ":"), r, 0)
        vrow = QHBoxLayout()
        self.cb_voice = QComboBox()
        self.cb_voice.addItem(t("voice_auto"), "")
        self._fill_voices(voices)
        self.cb_voice.setCurrentIndex(
            max(0, self.cb_voice.findData(cfg.get("voice", ""))))
        self.btn_voices = make_button(
            t("stemmen_verversen") if voices else t("stemmen_laden"))
        self.btn_voices.setToolTip(
            "Haalt de beschikbare stemmen op (model wordt zo nodig gedownload).")
        on_click(self.btn_voices, self._load_voices)
        self.btn_test = make_button("\U0001F50A " + t("test_stem"))
        self.btn_test.setToolTip(
            "Spreekt een korte testzin uit met de gekozen stem.")
        on_click(self.btn_test, self._test_voice)
        vrow.addWidget(self.cb_voice, 1)
        vrow.addWidget(self.btn_voices)
        vrow.addWidget(self.btn_test)
        grid.addLayout(vrow, r, 1)
        r += 1

        self.lb_voicestat = QLabel("")
        self.lb_voicestat.setStyleSheet("color:%s;" % MUTED)
        self.lb_voicestat.setWordWrap(True)
        grid.addWidget(self.lb_voicestat, r, 0, 1, 2)
        r += 1

        grid.addWidget(QLabel(t("snelheid") + ":"), r, 0)
        srow = QHBoxLayout()
        self.sl_speed = QSlider(Qt.Orientation.Horizontal)
        self.sl_speed.setRange(70, 200)
        self.sl_speed.setValue(int(float(cfg.get("speed", 1.05)) * 100))
        self.lb_speed = QLabel()
        self.lb_speed.setMinimumWidth(54)
        self.sl_speed.valueChanged.connect(
            lambda v: self.lb_speed.setText("%.2fx" % (v / 100.0)))
        self.lb_speed.setText("%.2fx" % (self.sl_speed.value() / 100.0))
        srow.addWidget(self.sl_speed)
        srow.addWidget(self.lb_speed)
        grid.addLayout(srow, r, 1)
        r += 1

        grid.addWidget(QLabel(t("kwaliteit") + ":"), r, 0)
        self.sp_steps = QSpinBox()
        self.sp_steps.setRange(3, 24)
        self.sp_steps.setValue(int(cfg.get("steps", 8)))
        grid.addWidget(self.sp_steps, r, 1)
        r += 1

        lay.addLayout(grid)

        self.ck_sound = QCheckBox(t("geluid_aan"))
        self.ck_sound.setChecked(bool(cfg.get("sound", True)))
        lay.addWidget(self.ck_sound)

        self.ck_auto = QCheckBox(t("doorlezen"))
        self.ck_auto.setChecked(bool(cfg.get("auto_next", True)))
        lay.addWidget(self.ck_auto)

        lay.addStretch(1)
        row = QHBoxLayout()
        row.addStretch(1)
        b_cancel = make_button(t("sluiten"))
        on_click(b_cancel, self.reject)
        b_save = make_button(t("opslaan"), obj="primary")
        on_click(b_save, self.accept)
        row.addWidget(b_cancel)
        row.addWidget(b_save)
        lay.addLayout(row)

    def _fill_voices(self, voices):
        # Behoud "(automatisch)" op index 0; vul de rest opnieuw.
        keep = self.cb_voice.currentData()
        while self.cb_voice.count() > 1:
            self.cb_voice.removeItem(1)
        for v in (voices or []):
            self.cb_voice.addItem(v, v)
        i = self.cb_voice.findData(keep)
        self.cb_voice.setCurrentIndex(i if i >= 0 else 0)

    def _load_voices(self):
        if self.engine is None or self._loader is not None:
            return
        self.btn_voices.setEnabled(False)
        self.lb_voicestat.setText(t("stemmen_bezig"))
        self._loader = VoiceLoader(self.engine)
        self._loader.status.connect(self.lb_voicestat.setText)
        self._loader.done.connect(self._voices_loaded)
        self._loader.failed.connect(self._voices_failed)
        self._loader.start()

    def _voices_loaded(self, voices):
        self._fill_voices(voices)
        self.lb_voicestat.setText(t("stemmen_klaar") % len(voices))
        self.btn_voices.setText(t("stemmen_verversen"))
        self.btn_voices.setEnabled(True)
        self._loader = None
        # geef de bijgewerkte lijst door zodat hij elders gecachet kan worden
        if callable(getattr(self, "on_voices_cached", None)):
            self.on_voices_cached(voices)

    def _voices_failed(self, msg):
        self.lb_voicestat.setText(t("stemmen_fout") + ": " + (msg or ""))
        self.btn_voices.setEnabled(True)
        self._loader = None

    def _test_voice(self):
        if self.engine is None or getattr(self, "_tester", None) is not None:
            return
        voice = self.cb_voice.currentData() or ""
        lang = "nl" if _LANG == "nl" else "en"
        steps = self.sp_steps.value()
        speed = round(self.sl_speed.value() / 100.0, 2)
        self.btn_test.setEnabled(False)
        self.btn_voices.setEnabled(False)
        self.lb_voicestat.setText(t("test_bezig"))
        self._tester = VoiceTester(self.engine, voice, lang, steps, speed)
        self._tester.status.connect(self.lb_voicestat.setText)
        self._tester.done.connect(self._test_done)
        self._tester.failed.connect(self._test_failed)
        self._tester.start()

    def _test_done(self, voices):
        # de stemlijst is nu bekend; vul hem zodat kiezen meteen kan
        if voices:
            self._fill_voices(voices)
            if callable(getattr(self, "on_voices_cached", None)):
                self.on_voices_cached(voices)
        self.lb_voicestat.setText(t("klaar"))
        self.btn_test.setEnabled(True)
        self.btn_voices.setEnabled(True)
        self.btn_voices.setText(t("stemmen_verversen"))
        self._tester = None

    def _test_failed(self, msg):
        self.lb_voicestat.setText(t("stemmen_fout") + ": " + (msg or ""))
        self.btn_test.setEnabled(True)
        self.btn_voices.setEnabled(True)
        self._tester = None

    def values(self) -> dict:
        self.cfg["lang"] = self.cb_lang.currentData()
        self.cfg["font_size"] = self.sp_font.value()
        self.cfg["read_bg"] = self.cb_bg.currentData()
        self.cfg["voice"] = self.cb_voice.currentData()
        self.cfg["speed"] = round(self.sl_speed.value() / 100.0, 2)
        self.cfg["steps"] = self.sp_steps.value()
        self.cfg["sound"] = self.ck_sound.isChecked()
        self.cfg["auto_next"] = self.ck_auto.isChecked()
        return self.cfg


# ----------------------------------------------------------------------------
# Snelgids-dialoog
# ----------------------------------------------------------------------------
GUIDE_NL = """
<h2 style="color:#6fa3d6;">DraveEReader - Snelgids</h2>
<p>DraveEReader leest bijna elk e-boek: EPUB, MOBI, AZW/AZW3, FB2, CBZ (strips),
PDF, XPS, TXT, HTML en afbeeldingen. De tekst kan worden <b>voorgelezen</b> met
een natuurlijke stem.</p>
<p><b>Een boek openen</b><br>
Klik op <b>Boek openen...</b> in de Bibliotheek, of kies een boek uit
<i>Onlangs geopend</i>. Uw leespositie wordt per boek onthouden.</p>
<p><b>Lezen</b><br>
Gebruik <b>Vorige</b> en <b>Volgende</b> (of de pijltjestoetsen / Page Up en
Page Down). Met <b>A-</b> en <b>A+</b> maakt u de letters kleiner of groter.
Via <b>Hoofdstukken</b> springt u naar een deel van het boek.</p>
<p><b>Voorlezen</b><br>
Klik op <b>Voorlezen</b> (of F5). De huidige zin wordt gemarkeerd. De eerste
keer wordt de stem automatisch gedownload; daarna werkt het meteen en offline.
Klik <b>ergens in de tekst</b> (of selecteer een stuk) en dan op <b>Voorlezen</b>
om vanaf die plek te beginnen. Met <b>Pauze</b> (of F6) zet je het lezen even
stil en hervat je het op dezelfde plek. Klik op <b>Stop</b> om te stoppen.</p>
<p><b>Weergave</b><br>
Wissel met <b>Weergave</b> tussen <i>Tekst</i> (grote, instelbare letters) en
<i>Pagina</i> (de echte opmaak, handig voor PDF en strips).</p>
<p><b>Instellingen</b><br>
Stel taal, lettergrootte, leesachtergrond (donker/sepia/licht), stem en
spreeksnelheid in.</p>
<p style="color:#8c8c96;">Alles werkt lokaal en offline. DraveEReader is
donationware - <b>service@dravenlock.nl</b> - paypal.me/roger076.</p>
"""

GUIDE_EN = """
<h2 style="color:#6fa3d6;">DraveEReader - Quick guide</h2>
<p>DraveEReader reads almost any e-book: EPUB, MOBI, AZW/AZW3, FB2, CBZ (comics),
PDF, XPS, TXT, HTML and images. The text can be <b>read aloud</b> with a natural
voice.</p>
<p><b>Open a book</b><br>
Click <b>Open book...</b> in the Library, or pick one under <i>Recently opened</i>.
Your reading position is remembered per book.</p>
<p><b>Reading</b><br>
Use <b>Previous</b> and <b>Next</b> (or the arrow keys / Page Up and Page Down).
<b>A-</b> and <b>A+</b> change the text size. <b>Chapters</b> jumps to a part of
the book.</p>
<p><b>Read aloud</b><br>
Click <b>Read aloud</b> (or F5). The current sentence is highlighted. The voice
downloads itself the first time; after that it works instantly and offline.
Click <b>anywhere in the text</b> (or select a passage) and then <b>Read aloud</b>
to start from that spot. Use <b>Pause</b> (or F6) to pause and resume at the same
place. Click <b>Stop</b> to stop.</p>
<p><b>View</b><br>
Switch with <b>View</b> between <i>Text</i> (large, adjustable letters) and
<i>Page</i> (true layout, handy for PDF and comics).</p>
<p style="color:#8c8c96;">Everything runs locally and offline. DraveEReader is
donationware - <b>service@dravenlock.nl</b> - paypal.me/roger076.</p>
"""


class GuideDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle(t("snelgids"))
        self.resize(640, 560)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 18, 18, 18)
        tb = QTextBrowser()
        tb.setOpenExternalLinks(True)
        tb.setStyleSheet(
            f"QTextBrowser{{background:{PANEL};color:{TEXT};border:1px solid {LINE};"
            f"border-radius:8px;padding:14px;font-size:17px;}}")
        tb.setHtml(GUIDE_NL if _LANG == "nl" else GUIDE_EN)
        lay.addWidget(tb)
        b = make_button(t("sluiten"), obj="primary")
        on_click(b, self.accept)
        row = QHBoxLayout()
        row.addStretch(1)
        row.addWidget(b)
        lay.addLayout(row)


# ----------------------------------------------------------------------------
# Bibliotheek (startscherm)
# ----------------------------------------------------------------------------
class HomeView(QWidget):
    def __init__(self, win):
        super().__init__()
        self.win = win
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        outer.addWidget(scroll)

        host = QWidget()
        scroll.setWidget(host)
        h = QHBoxLayout(host)
        h.addStretch(1)
        col = QVBoxLayout()
        col.setSpacing(16)
        col.setContentsMargins(20, 40, 20, 40)
        h.addLayout(col, 0)
        h.addStretch(1)
        host.setMaximumWidth(10000)

        logo = QLabel()
        pm = QPixmap(resource_path("assets/logo_t.png"))
        if pm.isNull():
            pm = QPixmap(resource_path("assets/logo.png"))
        if not pm.isNull():
            logo.setPixmap(pm.scaled(120, 120, Qt.AspectRatioMode.KeepAspectRatio,
                                     Qt.TransformationMode.SmoothTransformation))
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        col.addWidget(logo)

        self.lb_title = QLabel(APP_NAME)
        self.lb_title.setObjectName("title")
        self.lb_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        col.addWidget(self.lb_title)

        self.lb_sub = QLabel(t("ondertitel"))
        self.lb_sub.setObjectName("muted")
        self.lb_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        col.addWidget(self.lb_sub)

        self.btn_open = make_button(t("boek_openen"), obj="primary")
        self.btn_open.setMinimumHeight(58)
        f = self.btn_open.font(); f.setPointSize(13); self.btn_open.setFont(f)
        on_click(self.btn_open, self.win.choose_file)
        col.addWidget(self.btn_open)

        self.lb_recent = QLabel(t("recent"))
        self.lb_recent.setObjectName("h2")
        col.addWidget(self.lb_recent)

        self.recent = QListWidget()
        self.recent.setMinimumHeight(260)
        self.recent.setMinimumWidth(520)
        self.recent.itemActivated.connect(self._open_item)
        self.recent.itemDoubleClicked.connect(self._open_item)
        col.addWidget(self.recent)

        row = QHBoxLayout()
        self.btn_set = make_button(t("instellingen"))
        on_click(self.btn_set, self.win.open_settings)
        self.btn_guide = make_button(t("snelgids"))
        on_click(self.btn_guide, self.win.open_guide)
        self.btn_donate = make_button("\u2665 " + t("donatie"), CONTACT, obj="donate")
        on_click(self.btn_donate, self.win.open_donate)
        row.addWidget(self.btn_set)
        row.addWidget(self.btn_guide)
        row.addStretch(1)
        row.addWidget(self.btn_donate)
        col.addLayout(row)
        col.addStretch(1)

    def refresh(self):
        self.recent.clear()
        for entry in self.win.cfg.get("recent", []):
            page = entry.get("page", 0) + 1
            total = entry.get("total", 0)
            title = entry.get("title", "?")
            label = "%s\n    %s %d %s %d" % (title, t("pagina"), page, t("van"), total)
            it = QListWidgetItem(label)
            it.setData(Qt.ItemDataRole.UserRole, entry.get("path", ""))
            if not os.path.exists(entry.get("path", "")):
                it.setForeground(QColor(MUTED))
            self.recent.addItem(it)
        if self.recent.count() == 0:
            it = QListWidgetItem(t("geen_recent"))
            it.setForeground(QColor(MUTED))
            it.setData(Qt.ItemDataRole.UserRole, "")
            self.recent.addItem(it)

    def _open_item(self, it):
        path = it.data(Qt.ItemDataRole.UserRole)
        if path and os.path.exists(path):
            self.win.open_path(path)

    def retranslate(self):
        self.lb_sub.setText(t("ondertitel"))
        self.btn_open.setText(t("boek_openen"))
        self.lb_recent.setText(t("recent"))
        self.btn_set.setText(t("instellingen"))
        self.btn_guide.setText(t("snelgids"))
        self.btn_donate.setText("\u2665 " + t("donatie"))
        self.refresh()


# ----------------------------------------------------------------------------
# Lezer
# ----------------------------------------------------------------------------
class ReaderView(QWidget):
    def __init__(self, win):
        super().__init__()
        self.win = win
        self.book = Book()
        self.idx = 0
        self.view_mode = "text"
        self.spans = []
        self.reading = False
        self.worker = None
        self.entry = None

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ---- bovenbalk ----
        bar = QFrame(); bar.setObjectName("bar")
        bl = QHBoxLayout(bar)
        bl.setContentsMargins(12, 10, 12, 10)
        bl.setSpacing(8)
        self.btn_home = make_button("\u2302 " + t("bibliotheek"))
        on_click(self.btn_home, self.win.show_home)
        self.btn_toc = make_button(t("hoofdstukken"))
        on_click(self.btn_toc, self.toggle_toc)
        self.btn_goto = make_button(t("ga_naar"))
        on_click(self.btn_goto, self.goto_dialog)
        self.btn_view = make_button(t("weergave_tekst"))
        on_click(self.btn_view, self.toggle_view)
        self.btn_small = make_button("A\u2212", t("kleiner"))
        on_click(self.btn_small, lambda: self.change_font(-2))
        self.btn_big = make_button("A+", t("groter"))
        on_click(self.btn_big, lambda: self.change_font(2))
        self.btn_read = make_button("\U0001F50A " + t("voorlezen"), t("lees_vanaf"))
        on_click(self.btn_read, self.toggle_read)
        self.btn_pause = make_button("\u23F8 " + t("pauze"), t("pauze"))
        on_click(self.btn_pause, self.toggle_pause)
        self.btn_pause.setVisible(False)
        self.btn_set = make_button(t("instellingen"))
        on_click(self.btn_set, self.win.open_settings)
        self.btn_donate = make_button("\u2665", t("donatie"), obj="donate")
        on_click(self.btn_donate, self.win.open_donate)
        for b in (self.btn_home, self.btn_toc, self.btn_goto, self.btn_view,
                  self.btn_small, self.btn_big, self.btn_read, self.btn_pause):
            bl.addWidget(b)
        bl.addStretch(1)
        bl.addWidget(self.btn_set)
        bl.addWidget(self.btn_donate)
        root.addWidget(bar)

        # ---- midden: TOC + inhoud ----
        mid = QHBoxLayout()
        mid.setContentsMargins(0, 0, 0, 0)
        mid.setSpacing(0)
        self.toc = QListWidget()
        self.toc.setMaximumWidth(330)
        self.toc.setMinimumWidth(280)
        self.toc.itemActivated.connect(self._toc_jump)
        self.toc.itemClicked.connect(self._toc_jump)
        self.toc.hide()
        mid.addWidget(self.toc)

        self.stack = QStackedWidget()
        # tekstweergave (volle breedte, kleine binnenmarge)
        texthost = QWidget()
        th = QHBoxLayout(texthost)
        th.setContentsMargins(0, 0, 0, 0)
        self.text = QTextEdit()
        self.text.setReadOnly(True)
        self.text.setMinimumWidth(360)
        self.text.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.text.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        th.addWidget(self.text, 1)
        self.stack.addWidget(texthost)
        # paginaweergave (beeld)
        self.page_scroll = QScrollArea()
        self.page_scroll.setWidgetResizable(False)
        self.page_scroll.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.page_label = QLabel()
        self.page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.page_scroll.setWidget(self.page_label)
        self.stack.addWidget(self.page_scroll)
        mid.addWidget(self.stack, 1)
        root.addLayout(mid, 1)

        # ---- onderbalk ----
        bot = QFrame(); bot.setObjectName("bottombar")
        botl = QHBoxLayout(bot)
        botl.setContentsMargins(12, 10, 12, 10)
        self.btn_prev = make_button("\u25C0  " + t("vorige"))
        self.btn_prev.setMinimumHeight(52)
        on_click(self.btn_prev, self.prev_page)
        self.btn_next = make_button(t("volgende") + "  \u25B6")
        self.btn_next.setMinimumHeight(52)
        on_click(self.btn_next, self.next_page)
        self.lb_page = QLabel("")
        self.lb_page.setAlignment(Qt.AlignmentFlag.AlignCenter)
        f = self.lb_page.font(); f.setPointSize(12); f.setBold(True); self.lb_page.setFont(f)
        botl.addWidget(self.btn_prev)
        botl.addStretch(1)
        botl.addWidget(self.lb_page)
        botl.addStretch(1)
        botl.addWidget(self.btn_next)
        root.addWidget(bot)

        self.status = QLabel("")
        self.status.setObjectName("muted")
        self.status.setContentsMargins(14, 4, 14, 6)
        root.addWidget(self.status)

        # sneltoetsen
        self._shortcut(Qt.Key.Key_Left, self.prev_page)
        self._shortcut(Qt.Key.Key_Right, self.next_page)
        self._shortcut(Qt.Key.Key_PageUp, self.prev_page)
        self._shortcut(Qt.Key.Key_PageDown, self.next_page)
        self._shortcut(Qt.Key.Key_F5, self.toggle_read)
        self._shortcut(Qt.Key.Key_F6, self.toggle_pause)
        sc = QShortcut(QKeySequence("Ctrl+="), self); sc.activated.connect(lambda: self.change_font(2))
        sc2 = QShortcut(QKeySequence("Ctrl+-"), self); sc2.activated.connect(lambda: self.change_font(-2))
        sc3 = QShortcut(QKeySequence(Qt.Key.Key_Escape), self); sc3.activated.connect(self._escape)

        self._resize_timer = QTimer(self)
        self._resize_timer.setSingleShot(True)
        self._resize_timer.timeout.connect(self._maybe_render_page)

    # ---------- helpers ----------
    def _shortcut(self, key, fn):
        sc = QShortcut(QKeySequence(key), self)
        sc.activated.connect(lambda: fn())

    def _escape(self):
        if self.reading:
            self.stop_reading()
        else:
            self.win.show_home()

    @property
    def cfg(self):
        return self.win.cfg

    # ---------- boek laden ----------
    def load_book(self, path, start_page=0):
        self.stop_reading()
        try:
            self.book.close()
            self.book = Book()
            self.book.open(path)
        except Exception as e:  # noqa: BLE001
            QMessageBox.warning(self, APP_NAME, "%s:\n%s" % (t("openen_fout"), e))
            self.win.show_home()
            return False
        self.idx = max(0, min(start_page, self.book.count - 1))
        # TOC vullen
        self.toc.clear()
        for lvl, title, page in self.book.toc:
            indent = "   " * max(0, (lvl - 1))
            it = QListWidgetItem(indent + (title or "?"))
            it.setData(Qt.ItemDataRole.UserRole, max(0, page - 1))
            self.toc.addItem(it)
        self.btn_toc.setEnabled(self.toc.count() > 0)
        # beginweergave kiezen
        first_txt = self.book.page_text(self.idx)
        if not self.book.reflowable and not first_txt.strip():
            self.view_mode = "page"
        self._sync_view_button()
        self.win.setWindowTitle("%s - %s" % (self.book.title, APP_NAME))
        self.show_page()
        return True

    def _entry_save(self):
        if not self.book.path:
            return
        rec = self.cfg.setdefault("recent", [])
        rec[:] = [e for e in rec if e.get("path") != self.book.path]
        rec.insert(0, {
            "path": self.book.path,
            "title": self.book.title,
            "page": self.idx,
            "total": self.book.count,
            "ts": int(time.time()),
        })
        del rec[12:]
        save_config(self.cfg)

    # ---------- weergave ----------
    def apply_read_style(self):
        bg, fg = READ_BG.get(self.cfg.get("read_bg", "donker"), READ_BG["donker"])
        fs = int(self.cfg.get("font_size", 22))
        self.text.setStyleSheet(
            f"QTextEdit{{background:{bg};color:{fg};border:none;"
            f"padding:28px 34px;font-size:{fs}px;"
            f"selection-background-color:{ACCENT};selection-color:#0e0e11;}}")
        self.page_scroll.setStyleSheet(f"QScrollArea{{background:{PANEL};border:none;}}")

    def _apply_line_height(self):
        try:
            from PyQt6.QtGui import QTextBlockFormat
            cur = self.text.textCursor()
            cur.select(QTextCursor.SelectionType.Document)
            bf = QTextBlockFormat()
            bf.setLineHeight(142, 1)  # 1 = ProportionalHeight
            cur.mergeBlockFormat(bf)
            cur.clearSelection()
            self.text.setTextCursor(cur)
            self.text.moveCursor(QTextCursor.MoveOperation.Start)
        except Exception:
            pass

    def show_page(self):
        self.apply_read_style()
        text = self.book.page_text(self.idx)
        self.spans = split_sentences(text)
        if self.view_mode == "text":
            self.stack.setCurrentIndex(0)
            self.text.setExtraSelections([])
            self.text.setPlainText(text if text.strip() else "")
            if not text.strip():
                self.text.setPlainText("")
            self._apply_line_height()
            self.text.verticalScrollBar().setValue(0)
        else:
            self.stack.setCurrentIndex(1)
            self._render_page()
        self.lb_page.setText("%s %d %s %d" %
                             (t("pagina"), self.idx + 1, t("van"), self.book.count))
        self.btn_prev.setEnabled(self.idx > 0)
        self.btn_next.setEnabled(self.idx < self.book.count - 1)
        # huidige TOC markeren
        self._highlight_toc()
        self._entry_save()

    def _highlight_toc(self):
        best = -1
        for i in range(self.toc.count()):
            p = self.toc.item(i).data(Qt.ItemDataRole.UserRole)
            if p is not None and p <= self.idx:
                best = i
        if best >= 0:
            self.toc.blockSignals(True)
            self.toc.setCurrentRow(best)
            self.toc.blockSignals(False)

    def _render_page(self):
        if not self.book.doc:
            return
        try:
            r = self.book.doc[self.idx].rect
            w = max(1.0, r.width)
        except Exception:
            w = 595.0
        avail = max(360, self.page_scroll.viewport().width() - 28)
        zoom = max(0.4, min(3.0, avail / w))
        pm = self.book.page_pixmap(self.idx, zoom)
        if not pm.isNull():
            self.page_label.setPixmap(pm)
            self.page_label.resize(pm.size())
        self.page_scroll.verticalScrollBar().setValue(0)

    def _maybe_render_page(self):
        if self.view_mode == "page":
            self._render_page()

    def resizeEvent(self, ev):
        super().resizeEvent(ev)
        self._resize_timer.start(120)

    def _sync_view_button(self):
        self.btn_view.setText(t("weergave_tekst") if self.view_mode == "text"
                              else t("weergave_pagina"))

    def toggle_view(self):
        self.stop_reading()
        self.view_mode = "page" if self.view_mode == "text" else "text"
        self._sync_view_button()
        self.show_page()

    def change_font(self, delta):
        fs = int(self.cfg.get("font_size", 22)) + delta
        fs = max(14, min(48, fs))
        self.cfg["font_size"] = fs
        save_config(self.cfg)
        if self.view_mode == "text":
            self.apply_read_style()
            self._apply_line_height()

    def toggle_toc(self):
        self.toc.setVisible(not self.toc.isVisible())

    def _toc_jump(self, it):
        p = it.data(Qt.ItemDataRole.UserRole)
        if p is not None:
            self.stop_reading()
            self.idx = max(0, min(int(p), self.book.count - 1))
            self.show_page()

    def goto_dialog(self):
        if self.book.count <= 0:
            return
        n, ok = QInputDialog.getInt(self, t("ga_naar"), t("ga_pagina") + ":",
                                    self.idx + 1, 1, self.book.count)
        if ok:
            self.stop_reading()
            self.idx = n - 1
            self.show_page()

    def next_page(self):
        if self.idx < self.book.count - 1:
            was_reading = self.reading
            self.stop_reading()
            self.idx += 1
            self.show_page()
            if was_reading:
                self.start_reading()

    def prev_page(self):
        if self.idx > 0:
            self.stop_reading()
            self.idx -= 1
            self.show_page()

    # ---------- voorlezen ----------
    def toggle_read(self):
        if self.reading:
            self.stop_reading()
        else:
            # vanaf de aangeklikte/geselecteerde plek beginnen
            self.start_reading(self._sentence_at_cursor())

    def toggle_pause(self):
        if not self.reading or self.worker is None:
            return
        if self.worker.is_paused():
            self.worker.resume()
            self.btn_pause.setText("\u23F8 " + t("pauze"))
            self.status.setText(t("voorlezen_bezig"))
        else:
            self.worker.pause()
            self.btn_pause.setText("\u25B6 " + t("hervat"))
            self.status.setText(t("gepauzeerd"))

    def _sentence_at_cursor(self) -> int:
        """Zin-index bij de cursor/selectiebegin in de tekst (0 als onbekend)."""
        if self.view_mode != "text" or not self.spans:
            return 0
        try:
            pos = self.text.textCursor().selectionStart()
        except Exception:
            return 0
        for k, (a, b, _s) in enumerate(self.spans):
            if a <= pos < b:
                return k
            if pos < a:
                return k
        return 0

    def start_reading(self, from_sentence: int = 0):
        if self.view_mode != "text":
            # voor het voorlezen tonen we de tekst
            self.view_mode = "text"
            self._sync_view_button()
            self.show_page()
        text = self.book.page_text(self.idx)
        self.spans = split_sentences(text)
        if not self.spans:
            self.status.setText(t("geen_tekst"))
            return
        start_idx = min(max(0, int(from_sentence)), len(self.spans) - 1)
        self.reading = True
        self.btn_read.setText("\u25A0 " + t("stop"))
        self.btn_read.setObjectName("reading")
        self.btn_read.setStyleSheet("")  # objectName-stijl opnieuw toepassen
        self.style().unpolish(self.btn_read); self.style().polish(self.btn_read)
        self.btn_pause.setText("\u23F8 " + t("pauze"))
        self.btn_pause.setVisible(True)
        self.status.setText(t("stem_laden"))
        lang = "nl" if _LANG == "nl" else "en"
        sentences = [s for (_a, _b, s) in self.spans]
        self.worker = VoorleesWorker(
            self.win.engine, sentences, lang,
            self.cfg.get("voice", ""), int(self.cfg.get("steps", 8)),
            float(self.cfg.get("speed", 1.05)), start_index=start_idx)
        self.worker.sentence.connect(self.on_sentence)
        self.worker.page_done.connect(self.on_page_done)
        self.worker.status.connect(lambda m: self.status.setText(m))
        self.worker.failed.connect(self.on_failed)
        self.worker.start()

    def on_sentence(self, i):
        # stemmen die net door het model geladen zijn onthouden voor Instellingen
        eng = self.win.engine
        if eng.voices and self.cfg.get("voices_cache") != list(eng.voices):
            self.cfg["voices_cache"] = list(eng.voices)
            save_config(self.cfg)
        if i < 0 or i >= len(self.spans):
            return
        self.status.setText(t("voorlezen_bezig"))
        start, end, _seg = self.spans[i]
        sel = QTextEdit.ExtraSelection()
        fmt = QTextCharFormat()
        fmt.setBackground(QColor(GOLD))
        fmt.setForeground(QColor("#0e0e11"))
        sel.format = fmt
        cur = self.text.textCursor()
        cur.setPosition(start)
        cur.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
        sel.cursor = cur
        self.text.setExtraSelections([sel])
        vis = self.text.textCursor()
        vis.setPosition(start)
        self.text.setTextCursor(vis)
        self.text.ensureCursorVisible()

    def on_page_done(self):
        if self.reading and self.cfg.get("auto_next", True) and \
                self.idx < self.book.count - 1:
            self.idx += 1
            self.show_page()
            QTimer.singleShot(50, self.start_reading)
        else:
            self.stop_reading()

    def on_failed(self, msg):
        self.stop_reading()
        self.status.setText(t("stem_fout") + ": " + (msg or ""))
        QMessageBox.warning(self, APP_NAME, t("stem_fout") + ":\n" + (msg or ""))

    def stop_reading(self):
        self.reading = False
        if self.worker is not None:
            try:
                self.worker.stop()
                self.worker.wait(1500)
            except Exception:
                pass
            self.worker = None
        self.btn_read.setText("\U0001F50A " + t("voorlezen"))
        self.btn_read.setObjectName("")
        self.style().unpolish(self.btn_read); self.style().polish(self.btn_read)
        self.btn_pause.setVisible(False)
        self.btn_pause.setText("\u23F8 " + t("pauze"))
        self.text.setExtraSelections([])
        if self.status.text() in (t("voorlezen_bezig"), t("stem_laden"),
                                  t("gepauzeerd")):
            self.status.setText("")

    def retranslate(self):
        self.btn_home.setText("\u2302 " + t("bibliotheek"))
        self.btn_toc.setText(t("hoofdstukken"))
        self.btn_goto.setText(t("ga_naar"))
        self.btn_small.setToolTip(t("kleiner"))
        self.btn_big.setToolTip(t("groter"))
        self.btn_set.setText(t("instellingen"))
        self._sync_view_button()
        self.btn_prev.setText("\u25C0  " + t("vorige"))
        self.btn_next.setText(t("volgende") + "  \u25B6")
        if not self.reading:
            self.btn_read.setText("\U0001F50A " + t("voorlezen"))
        self.btn_read.setToolTip(t("lees_vanaf"))
        if not (self.worker and self.worker.is_paused()):
            self.btn_pause.setText("\u23F8 " + t("pauze"))
        self.btn_pause.setToolTip(t("pauze"))
        if self.book.doc:
            self.lb_page.setText("%s %d %s %d" %
                                 (t("pagina"), self.idx + 1, t("van"), self.book.count))


# ----------------------------------------------------------------------------
# Hoofdvenster
# ----------------------------------------------------------------------------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.cfg = load_config()
        set_lang(self.cfg.get("lang") or detect_os_lang())
        self.engine = TtsEngine()

        ico = QIcon(resource_path("assets/logo.ico"))
        if ico.isNull():
            ico = QIcon(resource_path("assets/logo.png"))
        self.setWindowIcon(ico)
        self.setWindowTitle(t("titel_app"))
        self.resize(1180, 800)
        self.setMinimumSize(820, 560)

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)
        self.home = HomeView(self)
        self.reader = ReaderView(self)
        self.stack.addWidget(self.home)
        self.stack.addWidget(self.reader)
        self.home.refresh()
        self.show_home()

    # ---------- navigatie ----------
    def show_home(self):
        try:
            self.reader.stop_reading()
        except Exception:
            pass
        self.home.refresh()
        self.stack.setCurrentWidget(self.home)
        self.setWindowTitle(t("titel_app"))

    def choose_file(self):
        exts = " ".join("*" + e for e in SUPPORTED)
        flt = "E-boeken (%s);;Alle bestanden (*.*)" % exts
        start = ""
        rec = self.cfg.get("recent", [])
        if rec and os.path.exists(os.path.dirname(rec[0].get("path", ""))):
            start = os.path.dirname(rec[0]["path"])
        path, _ = QFileDialog.getOpenFileName(self, t("boek_openen"), start, flt)
        if path:
            self.open_path(path)

    def open_path(self, path):
        start_page = 0
        for e in self.cfg.get("recent", []):
            if e.get("path") == path:
                start_page = e.get("page", 0)
                break
        self.stack.setCurrentWidget(self.reader)
        ok = self.reader.load_book(path, start_page)
        if not ok:
            self.show_home()

    # ---------- dialogen ----------
    def open_settings(self):
        # toon zowel eerder gecachte stemmen als al-geladen stemmen
        voices = list(self.cfg.get("voices_cache", []))
        for v in (self.engine.voices or []):
            if v not in voices:
                voices.append(v)
        dlg = SettingsDialog(self, self.cfg, voices, engine=self.engine)

        def _cache(vs):
            self.cfg["voices_cache"] = list(vs)
            save_config(self.cfg)
        dlg.on_voices_cached = _cache

        if dlg.exec() == QDialog.DialogCode.Accepted:
            old_lang = _LANG
            self.cfg = dlg.values()
            save_config(self.cfg)
            set_lang(self.cfg.get("lang") or detect_os_lang())
            if _LANG != old_lang:
                self.home.retranslate()
                self.reader.retranslate()
                self.setWindowTitle(t("titel_app") if self.stack.currentWidget() is self.home
                                    else self.windowTitle())
            # leesopmaak meteen toepassen
            if self.stack.currentWidget() is self.reader and self.reader.book.doc:
                self.reader.apply_read_style()
                if self.reader.view_mode == "text":
                    self.reader._apply_line_height()

    def open_guide(self):
        GuideDialog(self).exec()

    def open_donate(self):
        from PyQt6.QtGui import QDesktopServices
        from PyQt6.QtCore import QUrl
        QDesktopServices.openUrl(QUrl(DONATIE_URL))

    def closeEvent(self, ev):
        try:
            self.reader.stop_reading()
            self.reader._entry_save()
            self.reader.book.close()
        except Exception:
            pass
        super().closeEvent(ev)


def main():
    # crash-meldingen naar bestand (handig in de .exe)
    try:
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    except Exception:
        pass
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setStyleSheet(build_qss())
    base_font = QFont()
    base_font.setPointSize(11)
    app.setFont(base_font)

    win = MainWindow()
    win.show()

    # eventueel bestand meegegeven op de opdrachtregel
    for arg in sys.argv[1:]:
        if os.path.exists(arg) and arg.lower().endswith(SUPPORTED):
            win.open_path(arg)
            break

    try:  # Dravenlock: stille update-check (uit te zetten; Ctrl+Shift+U = met de hand)
        import drave_update
        drave_update.start(win, 'DraveEReader', APP_VERSION)
    except Exception:
        pass
    sys.exit(app.exec())


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # noqa: BLE001
        import traceback
        try:
            with open(os.path.join(config_dir(), "draveereader-fout.txt"),
                      "w", encoding="utf-8") as f:
                f.write(traceback.format_exc())
        except Exception:
            pass
        raise

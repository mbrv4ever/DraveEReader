# -*- coding: utf-8 -*-
"""
tts.py - Voorlees-engine voor DraveEReader (Dravenlock)

Gebruikt neuvoice (https://huggingface.co/thelamapi/neuvoice) voor on-device
neurale spraak. Het stemmodel downloadt zichzelf automatisch bij het eerste
gebruik; er zijn geen "neerslachtige" knoppen die op handmatige installatie
wachten. Vanuit broncode worden ontbrekende pakketten zo nodig zelf opgehaald;
in de .exe zijn neuvoice + onnxruntime meegebouwd.

Afspelen gebeurt zonder extra afhankelijkheid: de golfvorm wordt met de
standaardbibliotheek (wave) als 16-bit PCM weggeschreven en op Windows met
winsound afgespeeld.
"""
from __future__ import annotations

import os
import sys
import wave
import threading


class TtsEngine:
    """Laadt het neuvoice-model lui (lazy) en synthetiseert tekst naar WAV."""

    def __init__(self):
        self._tts = None
        self._lock = threading.Lock()
        self.sample_rate = 24000
        self.voices = []          # lijst met stemnamen, gevuld na laden
        self.ready = False
        self.last_error = ""

    # ---------- beschikbaarheid ----------
    @staticmethod
    def module_available() -> bool:
        try:
            import neuvoice  # noqa: F401
            return True
        except Exception:
            return False

    def _try_pip_install(self, progress=None) -> bool:
        """Alleen vanuit broncode: probeer ontbrekende pakketten zelf op te halen."""
        if getattr(sys, "frozen", False):
            return self.module_available()
        import subprocess
        for pkg in ("onnxruntime", "neuvoice"):
            try:
                __import__(pkg)
            except Exception:
                if progress:
                    progress("Stem-onderdelen installeren (%s)..." % pkg)
                try:
                    subprocess.run(
                        [sys.executable, "-m", "pip", "install",
                         "--only-binary=:all:", pkg],
                        check=False,
                    )
                except Exception:
                    pass
        return self.module_available()

    # ---------- model laden / downloaden ----------
    def ensure_ready(self, progress=None) -> bool:
        """Zorg dat het model geladen is. Downloadt het bij de eerste keer.

        progress(str): optionele callback voor statusmeldingen.
        Geeft True terug bij succes, anders False (zie last_error).
        """
        with self._lock:
            if self.ready and self._tts is not None:
                return True
            try:
                import neuvoice  # noqa: F401
            except Exception:
                if not self._try_pip_install(progress):
                    self.last_error = ("Stempakketten (neuvoice/onnxruntime) "
                                       "konden niet worden geladen.")
                    return False
            try:
                from neuvoice import TTS
                if progress:
                    progress("Stemmodel laden (eerste keer: downloaden)...")
                self._tts = TTS(auto_download=True)
                self.sample_rate = int(self._tts.sample_rate)
                self.voices = list(self._tts.voice_style_names)
                self.ready = True
                self.last_error = ""
                return True
            except Exception as e:  # noqa: BLE001
                self.last_error = str(e)
                self._tts = None
                self.ready = False
                return False

    def pick_voice(self, name: str) -> str:
        """Kies een geldige stem; val terug op de eerste beschikbare."""
        if not self.voices:
            return name or ""
        if name and name in self.voices:
            return name
        return self.voices[0]

    # ---------- synthese ----------
    def synth_to_wav(self, text: str, path: str, lang: str = "nl",
                     voice: str = "", steps: int = 8, speed: float = 1.05) -> float:
        """Synthetiseer 'text' naar een 16-bit PCM WAV op 'path'.

        Geeft de duur (seconden) terug. Vereist dat ensure_ready() gelukt is.
        """
        if self._tts is None:
            raise RuntimeError("Stemmodel is niet geladen.")
        import numpy as np

        voice_name = self.pick_voice(voice)
        style = self._tts.get_voice_style(voice_name)
        wav, _dur = self._tts.synthesize(
            text, voice_style=style,
            total_steps=int(steps), speed=float(speed), lang=lang,
        )
        arr = np.asarray(wav, dtype="float32").squeeze()
        arr = np.clip(arr, -1.0, 1.0)
        pcm = (arr * 32767.0).astype("<i2")
        tmp = path + ".part"
        with wave.open(tmp, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(self.sample_rate)
            w.writeframes(pcm.tobytes())
        os.replace(tmp, path)
        return len(pcm) / float(self.sample_rate)

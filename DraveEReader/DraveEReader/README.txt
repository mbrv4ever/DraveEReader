============================================================
  DraveEReader - e-boeklezer en voorlezer   (Dravenlock)
============================================================
Versie 0.1.0  -  offline donationware voor Windows
Donatie: https://paypal.me/roger076   -   service@dravenlock.nl

WAT IS HET
----------
DraveEReader leest bijna elk e-boek en kan de tekst laten VOORLEZEN met een
natuurlijke neurale stem. Het werkt volledig lokaal en offline.

Ondersteunde formaten:
  EPUB, MOBI, AZW / AZW3, FB2, CBZ (strips), PDF, XPS, TXT, HTML
  en losse afbeeldingen (PNG/JPG/...).

TOEGANKELIJK
------------
Donker thema, grote knoppen, hoog contrast en een instelbare lettergrootte.
De leeskolom blijft prettig smal, ook op brede schermen. Kies in Instellingen
tussen een donkere, sepia of lichte leesachtergrond.

STARTEN
-------
1. Dubbelklik op  run.bat
   - De eerste keer worden de benodigde onderdelen automatisch geinstalleerd
     (dit kan even duren). Daarna start de app meteen.
   - Er is GEEN handmatige installatie nodig: alles gebeurt vanzelf.
2. Klik op "Boek openen..." en kies een e-boek.

VOORLEZEN
---------
Klik in de lezer op "Voorlezen" (of druk op F5). De zin die wordt voorgelezen,
licht op. De eerste keer downloadt de stem zichzelf automatisch; daarna werkt
het meteen en offline.

Klik ergens in de tekst (of selecteer een stuk) en dan op "Voorlezen" om vanaf
die plek te beginnen. Met "Pauze" (of F6) zet u het lezen even stil en hervat
u het op dezelfde plek. Klik op "Stop" om te stoppen.

WEERGAVE
--------
Wissel met de knop "Weergave" tussen:
  - Tekst : grote, instelbare letters (fijn om te lezen en voor te lezen)
  - Pagina: de echte opmaak (handig voor PDF en strips)

INSTELLINGEN
------------
Taal (volgt standaard de computer, of kies zelf Nederlands/Engels),
lettergrootte, leesachtergrond, stem, spreeksnelheid en stemkwaliteit.
Uw leespositie wordt per boek onthouden.

PROBLEMEN OPLOSSEN
------------------
- start-debug.bat : start de app met zichtbare foutmeldingen.
- herstel.bat     : wist de installatiemap (.venv) en bouwt alles opnieuw op.
- Startfouten worden ook bewaard in:
    %APPDATA%\DraveEReader\draveereader-fout.txt

EEN .EXE MAKEN
--------------
Dubbelklik op  bouw-exe.bat
  Dit bouwt met PyInstaller EEN los uitvoerbaar bestand:
      dist\DraveEReader.exe
  De stem (neuvoice + onnxruntime) wordt meegebouwd, zodat voorlezen ook in
  de .exe werkt. Het stemmodel zelf downloadt bij het eerste gebruik.
  Let op: hierdoor is de .exe groot (enkele honderden MB). Dat is normaal.

BENODIGD
--------
Windows met Python 3.10 t/m 3.13 (van https://www.python.org).
De launchers kiezen automatisch de juiste versie en installeren de rest.

------------------------------------------------------------
DraveEReader is donationware. Bevalt het? Een kleine donatie wordt gewaardeerd:
https://paypal.me/roger076   -   service@dravenlock.nl
------------------------------------------------------------

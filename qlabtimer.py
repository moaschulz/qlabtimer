#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
==============================================================================
QLAB 5 FREE SCENE TIMER
==============================================================================

Funktioniert mit der kostenlosen Version von QLab 5 unter macOS.

Da in der kostenlosen Version von QLab keine Script-/Control-Cues erlaubt sind, 
nutzen wir normale WAIT CUES als Stoppuhren im Hintergrund. Wichtig ist für uns nur,
dass diese Cues laufen, solange eine Szene läuft. Alle Cues, die gerade in QLab laufen,
kann das Skript über AppleScript abfragen. Während das Skript läuft, fragt es diese 
aktiven Cues in einem festen Intervall ab und wertet sie aus. So werden Szenenwechsel 
registriert und die Laufzeiten der Szenen berechnet.

Dieses Skript beobachtet nur, welche Cues in QLab laufen - es hat keine Kontrolle 
über die Show und startet oder stoppt keine Cues.

------------------------------------------------------------------------------
EINRICHTUNG IN QLAB
------------------------------------------------------------------------------

1. WAIT CUES FÜR JEDE SZENE:
   - Lege für jede Szene einen Wait Cue mit einer sehr langen Laufzeit an, 
     länger als die maximale Szenenlaufzeit (z. B. pauschal 04:00:00).
   - Benenne jeden Wait Cue so, dass er mit dem SCENE_PREFIX (z.B. "Szene") anfängt 
     (also z. B. "Szene 1" oder "Szene 2a - Ophelia geht baden").

2. SZENEN-ÜBERGANG:
   - Am Ende von Szene 1 / Start von Szene 2 erstellst du:
     a) Einen Stop Cue (Target: Wait Cue von Szene 1)
     b) Einen neuen Wait Cue für Szene 2 (z. B. "Szene 2", Duration 99:99:00)
   - Starte den neuen Wait Cue per auto continue direkt nach dem Stop Cue oder
     binde beide in eine "Fire-all"-Gruppe ein.
   - D.h. jeder Szenenwechsel beinhaltet zwei Cues in QLab: vorherige stoppen, neue starten.

3. UNTERBRECHUNGEN / PAUSEN IN DER PROBE:
   - Drückst du in QLab im rechten Seitenmenü 'Pause', erkennt das Skript den Zustand, 
     friert die Szenenzeit ein und stoppt die Pausenzeit mit.
   - Setzt du die Szene anschließend fort, wird die Pausenzeit automatisch von der Szenen- 
     und Gesamtlaufzeit abgezogen. Der Endbericht gibt auch die Pausenzeit je Szene aus.
   - Geht ihr nach einer Unterbrechung innerhalb einer Szene zurück, ist es am einfachsten, 
     den Wait Cue pausiert zu lassen und manuell im Active-Cues-Fenster wieder zu starten, 
     wenn ihr die Stelle der Unterbrechung wieder erreicht.
   - Geht ihr nach einer Unterbrechung zum Beginn einer anderen Szene zurück, beende den 
     pausierten Wait Cue der unterbrochenen Szene und starte den Wait Cue der Szene, mit 
     der ihr neu beginnt.
   - Wird eine bereits gemessene Szene später erneut gestartet, wird ihre neue Laufzeit als 
     zusätzliche CSV-Zeile gespeichert; frühere Messungen werden nicht überschrieben.

4. STÜCKENDE:
   - Erstelle am Ende des Stücks einen Cue mit dem Namen aus END_CUE_NAME 
     (z. B. "Stückende").
   - Sobald dieser Cue läuft, schließt das Skript die Messung sauber ab,
     berücksichtigt eine laufende Pause bis zu diesem Zeitpunkt, schreibt die CSV und 
     beendet das Polling automatisch.

------------------------------------------------------------------------------
NUTZUNG DES TIMERS
------------------------------------------------------------------------------

VORBEDINGUNGEN:
   - macOS mit installiertem Python 3.x (z. B. via Homebrew: brew install python3)
   - Kostenlose Version von QLab 5 (https://qlab.app/download/) installiert und 
     Workspace konfiguriert (s.o.).

1. SKRIPT STARTEN:
   - Öffne in Finder den Ordner, in dem dieses Skript gespeichert ist.
   - Öffne über einen Rechtsklick auf den Ordner in der Pfadleiste unten im 
     Finder ein Terminal in diesem Ordner.
     (Alternativ kopiere den Pfad, öffne ein neues Terminal und wechsle das 
     Arbeitsverzeichnis dorthin: cd Pfad/Hier/Einfügen)
   - Starte das Skript mit: python3 qlabtimer.py

2. SHOW STARTEN:
   - Starte in QLab zu Stückbeginn den Wait Cue für die erste Szene
   - Fahre übrige Cues wie gewohnt.

3. SHOW BEENDEN:
   - Starte den Stückende-Cue. Danach kannst du die Show in QLab beenden.
   - Das Skript schreibt automatisch eine CSV-Datei mit allen Szenenlaufzeiten in das 
     aktuelle Arbeitsverzeichnis (bei Vorgehen nach (1): Ordner des Skripts).
   - Beende das Terminal (Cmd+Q).

==============================================================================
"""

import csv
import os
import sys
import time
import subprocess
from datetime import datetime
from typing import Optional, Tuple

# ==============================================================================
# KONFIGURATION
# ==============================================================================
SCENE_PREFIX = "Szene"       # Präfix für alle relevanten Szenen-Wait-Cues
END_CUE_NAME = "Stückende"   # Name/Präfix des Cues, der die Session beendet
POLL_INTERVAL = 0.5          # Abfrage-Intervall in Sekunden


def safe_print(msg: str):
    """Garantierte und fehlertolerante Ausgabe im Terminal."""
    try:
        print(msg, flush=True)
    except Exception:
        try:
            print(msg.encode("ascii", errors="replace").decode("ascii"), flush=True)
        except Exception:
            pass


def get_running_and_paused_cues():
    """Fragt QLab via AppleScript nach Namen UND Pausen-Status aller aktiven Cues.
    
    Rückgabe: Liste von Dictionaries, z. B. [{"name": "Szene 1", "paused": True}]
    """
    cmd = '''
    tell application "QLab"
        tell front workspace
            set theCues to active cues
            set cueData to ""
            repeat with cueRef in theCues
                set aCue to contents of cueRef
                set cName to q name of aCue
                set cPaused to paused of aCue
                set cueData to cueData & cName & "|||" & cPaused & ":::"
            end repeat
            return cueData
        end tell
        return ""
    end tell
    '''
    try:
        res = subprocess.run(["osascript", "-e", cmd], capture_output=True, text=True, timeout=5)

        if res.returncode != 0 or res.stderr.strip():
            safe_print(f"⚠️ AppleScript-Fehler: {res.stderr.strip()}")
            return []

        raw_output = res.stdout.strip()
        if not raw_output:
            return []

        cues = []
        # Parst den benutzerdefinierten String-Trennzeichen-Output
        for item in raw_output.split(":::"):
            if "|||" in item:
                parts = item.split("|||")
                cues.append({
                    "name": parts[0].strip(),
                    "paused": parts[1].strip().lower() == "true"
                })
        return cues
    except subprocess.TimeoutExpired:
        safe_print("⚠️ osascript-Aufruf hat zu lange gedauert (Timeout) – wird im nächsten Poll erneut versucht.")
        return []
    except Exception as e:
        safe_print(f"⚠️ Unerwarteter Fehler beim osascript-Aufruf: {e}")
        return []


def format_duration(seconds: float) -> str:
    """Formatiert eine Sekundenzahl als Standardzeit (z. B. 00:04:12)."""
    total_seconds = max(0, int(round(seconds)))
    hours, remainder = divmod(total_seconds, 3600)
    mins, secs = divmod(remainder, 60)
    return f"{hours:02d}:{mins:02d}:{secs:02d}"


def init_csv_file() -> Optional[str]:
    """Erstellt die CSV-Datei direkt im aktuellen Arbeitsverzeichnis (wd)."""
    timestamp = datetime.now().strftime("%Y%m%d%H%M")
    suffix = 0

    while True:
        suffix_text = f"_{suffix}" if suffix else ""
        filename = f"qlabtimer_{timestamp}{suffix_text}.csv"
        csv_path = os.path.join(os.getcwd(), filename)

        try:
            with open(csv_path, "x", encoding="utf-8", newline="") as f:
                writer = csv.writer(f, delimiter=";", lineterminator="\n")
                writer.writerow(("Szene", "Startzeit", "Endzeit", "Szenendauer", "Gesamtdauer", "Pausenzeit (Sek)"))
            return csv_path
        except FileExistsError:
            suffix += 1
        except (OSError, csv.Error, UnicodeError) as e:
            safe_print(f"⚠️ CSV-Datei konnte nicht erstellt werden: {e}")
            safe_print("⚠️ Bitte die Szenenzeiten im Terminal als Backup kopieren.")
            return None


def close_pause(end_dt: datetime, pause_start_dt: Optional[datetime], scene_pause_sec: float, session_pause_sec: float) -> Tuple[float, float]:
    if pause_start_dt is None:
        return scene_pause_sec, session_pause_sec

    pause_duration = (end_dt - pause_start_dt).total_seconds()
    return scene_pause_sec + pause_duration, session_pause_sec + pause_duration


def write_csv_row(csv_path: Optional[str], scene_name: str, start_dt: datetime, end_dt: datetime, session_start_dt: datetime, scene_pause_sec: float, session_pause_sec: float) -> Tuple[str, str, bool]:
    """Schreibt eine Szenenmessung bereinigt um etwaige Pausenzeiten in die CSV."""
    raw_scene_sec = (end_dt - start_dt).total_seconds()
    net_scene_sec = max(0.0, raw_scene_sec - scene_pause_sec)
    
    total_duration_sec = max(0.0, (end_dt - session_start_dt).total_seconds() - session_pause_sec)

    start_str = start_dt.strftime("%H:%M:%S")
    end_str = end_dt.strftime("%H:%M:%S")
    scene_dur_str = format_duration(net_scene_sec)
    total_dur_str = format_duration(total_duration_sec)

    if csv_path is None:
        return scene_dur_str, total_dur_str, False

    try:
        with open(csv_path, "a", encoding="utf-8", newline="") as f:
            writer = csv.writer(f, delimiter=";", lineterminator="\n")
            writer.writerow((
                scene_name,
                start_str,
                end_str,
                scene_dur_str,
                total_dur_str,
                round(scene_pause_sec, 1),
            ))
    except (OSError, csv.Error, UnicodeError) as e:
        safe_print(f"⚠️ FEHLER beim Schreiben in CSV ({csv_path}): {e}")
        safe_print("⚠️ Bitte die Szenenzeiten im Terminal als Backup kopieren.")
        return scene_dur_str, total_dur_str, False

    return scene_dur_str, total_dur_str, True


def main():
    safe_print("\n" + "#" * 65)
    safe_print(" QLAB 5 FREE SCENE TIMER")
    safe_print("#" * 65)

    csv_path = init_csv_file()
    if csv_path:
        safe_print(f"📁 CSV-Datei erstellt: {csv_path}")
    else:
        safe_print("⚠️ CSV-Ausgabe ist nicht verfügbar; bitte Szenenzeiten im Terminal als Backup kopieren.")
    safe_print(f"📂 Arbeitsverzeichnis: {os.getcwd()}")
    safe_print(f"🔍 Filter-Präfix: '{SCENE_PREFIX}' | End-Signal: '{END_CUE_NAME}'")
    safe_print(f"⏱️  Polling läuft ({POLL_INTERVAL}s Intervall)... [Abbruch mit STRG+C]\n")

    current_scene_name = ""
    current_scene_start_dt = None
    session_start_dt = None
    
    # Pausen-Management Status
    is_paused = False
    pause_start_dt = None
    scene_pause_sec = 0.0
    session_pause_sec = 0.0
    
    in_error_state = False

    try:
        while True:
            active_cues = get_running_and_paused_cues()

            # 1. PRÜFUNG: Läuft der End-Cue?
            if any(c["name"].startswith(END_CUE_NAME) for c in active_cues):
                if current_scene_name and current_scene_start_dt:
                    end_dt = datetime.now()
                    scene_pause_sec, session_pause_sec = close_pause(
                        end_dt, pause_start_dt, scene_pause_sec, session_pause_sec
                    )
                    scene_str, total_str, csv_written = write_csv_row(
                        csv_path, current_scene_name, current_scene_start_dt, end_dt, session_start_dt, scene_pause_sec, session_pause_sec
                    )
                    if not csv_written:
                        csv_path = None
                    safe_print(f"✓ {current_scene_name}: {scene_str} | Gesamtdauer: {total_str}")

                safe_print("\n" + "=" * 65)
                safe_print(f"⏹ ENDE-CUE '{END_CUE_NAME}' ERKANNT.")
                if csv_path:
                    safe_print(f"📄 Session beendet & gespeichert in: {csv_path}")
                else:
                    safe_print("⚠️ CSV konnte nicht vollständig gespeichert werden; Szenenzeiten bitte aus dem Terminal kopieren.")
                safe_print("=" * 65 + "\n")
                sys.exit(0)

            # 2. PRÜFUNG: Filtere alle aktiven Cues nach dem SCENE_PREFIX
            scene_cues = [c for c in active_cues if c["name"].startswith(SCENE_PREFIX)]

            # ------------------------------------------------------------------
            # SCENARIO EVALUATION
            # ------------------------------------------------------------------
            if len(scene_cues) == 1:
                target_cue = scene_cues[0]
                detected_name = target_cue["name"]
                cue_is_paused = target_cue["paused"]

                # A) PAUSEN-HANDLING
                if cue_is_paused and not is_paused:
                    is_paused = True
                    pause_start_dt = datetime.now()
                    safe_print(f"⏸ PROBE PAUSIERT in '{detected_name}' um {pause_start_dt.strftime('%H:%M:%S')} (Zeitzählung eingefroren)")

                elif not cue_is_paused and is_paused:
                    is_paused = False
                    if pause_start_dt is not None:
                        now_dt = datetime.now()
                        p_duration = (now_dt - pause_start_dt).total_seconds()
                        scene_pause_sec, session_pause_sec = close_pause(
                            now_dt, pause_start_dt, scene_pause_sec, session_pause_sec
                        )
                        safe_print(f"▶ PROBE FORTGESETZT (Pause dauerte {int(p_duration)}s)")
                    pause_start_dt = None

                # B) SZENEN-START & WECHSEL
                if not is_paused:
                    # Fall 1: Erstmaliger Session-Start
                    if not current_scene_name:
                        current_scene_start_dt = datetime.now()
                        session_start_dt = current_scene_start_dt
                        current_scene_name = detected_name
                        scene_pause_sec = 0.0
                        session_pause_sec = 0.0
                        in_error_state = False

                        safe_print("=" * 65)
                        safe_print(f"▶ SESSION GESTARTET um {current_scene_start_dt.strftime('%H:%M:%S')}")
                        safe_print(f"🎬 Erste Szene: {current_scene_name}")
                        safe_print("=" * 65)

                    # Fall 2: Wechsel zu einer NEUEN Szene
                    elif detected_name != current_scene_name:
                        now_dt = datetime.now()
                        scene_str, total_str, csv_written = write_csv_row(
                            csv_path, current_scene_name, current_scene_start_dt, now_dt, session_start_dt, scene_pause_sec, session_pause_sec
                        )
                        if not csv_written:
                            csv_path = None
                        safe_print(f"✓ {current_scene_name}: {scene_str} | Gesamtdauer: {total_str}")

                        current_scene_name = detected_name
                        current_scene_start_dt = now_dt
                        scene_pause_sec = 0.0
                        in_error_state = False

                    # Fall 3: Erholungsfall nach Konflikt-Zustand
                    elif in_error_state:
                        safe_print(f"✅ Konflikt gelöst. Fortfahren mit Szene: '{current_scene_name}'")
                        in_error_state = False

            elif len(scene_cues) > 1:
                # Szenario: Alter Szenen-Cue läuft noch, aber EIN NEUER ist gestartet
                new_cues = [c for c in scene_cues if c["name"] != current_scene_name]

                if len(new_cues) == 1:
                    new_cue = new_cues[0]
                    new_scene_name = new_cue["name"]
                    now_dt = datetime.now()

                    if current_scene_name and current_scene_start_dt and session_start_dt:
                        scene_pause_sec, session_pause_sec = close_pause(
                            now_dt, pause_start_dt, scene_pause_sec, session_pause_sec
                        )
                        scene_str, total_str, csv_written = write_csv_row(
                            csv_path, current_scene_name, current_scene_start_dt, now_dt, session_start_dt, scene_pause_sec, session_pause_sec
                        )
                        if not csv_written:
                            csv_path = None
                        safe_print(f"✓ {current_scene_name}: {scene_str} | Gesamtdauer: {total_str} (Überlappung aufgelöst)")

                    current_scene_name = new_scene_name
                    current_scene_start_dt = now_dt
                    scene_pause_sec = 0.0
                    is_paused = new_cue["paused"]
                    pause_start_dt = now_dt if is_paused else None
                    in_error_state = False

                else:
                    # Konflikt: Mehrere unbekannte Szenen-Cues laufen parallel
                    if not in_error_state:
                        conflict_names = [c["name"] for c in scene_cues]
                        safe_print("\n⚠️ " + "!" * 55)
                        safe_print(f"⚠️ KONFLIKT: {len(scene_cues)} Szenen-Cues laufen gleichzeitig!")
                        safe_print(f"⚠️ Betroffene Cues: {conflict_names}")
                        safe_print("⚠️ Messung pausiert, bis wieder EINDEUTIG 1 Szene läuft.")
                        safe_print("⚠️ " + "!" * 55 + "\n")
                        in_error_state = True

            elif len(scene_cues) == 0 and current_scene_name and not is_paused:
                # Szenario: Szene wurde manuell gestoppt (Abbruch / Wiederholung)
                # Skript wartet, ob dieselbe oder eine neue Szene gestartet wird.
                pass

            time.sleep(POLL_INTERVAL)

    except KeyboardInterrupt:
        safe_print("\n\n⏹ MESSUNG DURCH STRG+C MANUELL ABGEBROCHEN.")
        if current_scene_name and current_scene_start_dt:
            now_dt = datetime.now()
            scene_pause_sec, session_pause_sec = close_pause(
                now_dt, pause_start_dt, scene_pause_sec, session_pause_sec
            )
            scene_str, total_str, csv_written = write_csv_row(
                csv_path, current_scene_name, current_scene_start_dt, now_dt, session_start_dt, scene_pause_sec, session_pause_sec
            )
            if not csv_written:
                csv_path = None
            safe_print(f"✓ Letzte Szene ({current_scene_name}) gemessen: {scene_str} | Gesamtdauer: {total_str}")

        if csv_path:
            safe_print(f"📄 Bisherige Zeiten gespeichert in: {csv_path}\n")
        else:
            safe_print("⚠️ CSV konnte nicht vollständig gespeichert werden; Szenenzeiten bitte aus dem Terminal kopieren.\n")
        sys.exit(0)


if __name__ == "__main__":
    main()
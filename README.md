# Szenen-Timer für QLab
*🇬🇧 English version below.*

Python-Skript, funktioniert mit der kostenlosen Version von QLab 5 unter macOS.

Da in der kostenlosen Version von QLab keine Script-/Control-Cues erlaubt sind, nutzen wir normale WAIT CUES als Stoppuhren im Hintergrund. Wichtig ist für uns nur, dass diese Cues laufen, solange eine Szene läuft. Alle Cues, die gerade in QLab laufen (egal ob Edit or Show Mode), kann das Skript über AppleScript abfragen. Während das Skript läuft, fragt es diese aktiven Cues in einem festen Intervall ab und wertet sie aus. So werden Szenenwechsel registriert und die Laufzeiten der Szenen berechnet.

Dieses Skript beobachtet nur, welche Cues in QLab laufen - es hat keine Kontrolle über die Show und startet oder stoppt keine Cues.

## EINRICHTUNG IN QLAB

1. WAIT CUES FÜR JEDE SZENE:
   - Lege für jede Szene einen Wait Cue mit einer sehr langen Laufzeit an, länger als die maximale Szenenlaufzeit (z. B. pauschal 04:00:00).
   - Benenne jeden Wait Cue so, dass er mit dem SCENE_PREFIX (z.B. "Szene") anfängt (also z. B. "Szene 1" oder "Szene 2a - Ophelia geht baden").

2. SZENEN-ÜBERGANG:
   - Am Ende von Szene 1 / Start von Szene 2 erstellst du:
     a) Einen Stop Cue (Target: Wait Cue von Szene 1)
     b) Einen neuen Wait Cue für Szene 2 (z. B. "Szene 2", Duration 99:99:00)
   - Starte den neuen Wait Cue per auto continue direkt nach dem Stop Cue oder binde beide in eine "Fire-all"-Gruppe ein.
   - D.h. jeder Szenenwechsel beinhaltet zwei Cues in QLab: vorherige stoppen, neue starten.

3. UNTERBRECHUNGEN / PAUSEN IN DER PROBE:
   - Drückst du in QLab im rechten Seitenmenü 'Pause', erkennt das Skript den Zustand, friert die Szenenzeit ein und stoppt die Pausenzeit mit.
   - Setzt du die Szene anschließend fort, wird die Pausenzeit automatisch von der Szenen- und Gesamtlaufzeit abgezogen. Der Endbericht gibt auch die Pausenzeit je Szene aus.
   - Geht ihr nach einer Unterbrechung innerhalb einer Szene zurück, ist es am einfachsten, den Wait Cue pausiert zu lassen und manuell im Active-Cues-Fenster wieder zu starten, wenn ihr die Stelle der Unterbrechung wieder erreicht.
   - Geht ihr nach einer Unterbrechung zum Beginn einer anderen Szene zurück, beende den pausierten Wait Cue der unterbrochenen Szene und starte den Wait Cue der Szene, mit der ihr neu beginnt.
   - Wird eine bereits gemessene Szene später erneut gestartet, wird ihre neue Laufzeit als zusätzliche CSV-Zeile gespeichert; frühere Messungen werden nicht überschrieben.

4. STÜCKENDE:
   - Erstelle am Ende des Stücks einen Cue mit dem Namen aus END_CUE_NAME (z. B. "Stückende").
   - Sobald dieser Cue läuft, schließt das Skript die Messung sauber ab,berücksichtigt eine laufende Pause bis zu diesem Zeitpunkt, schreibt die CSV und beendet das Polling automatisch. Das Skript stoppt QLab-Cues nicht selbst; falls der pausierte Wait Cue ebenfalls gestoppt werden soll, muss der Stückende-Cue das in QLab auslösen.

## NUTZUNG DES TIMERS

VORBEDINGUNGEN:
   - macOS mit installiertem Python 3.x (z. B. via Homebrew: brew install python3)
   - Kostenlose Version von QLab 5 (https://qlab.app/download/) installiert und Workspace konfiguriert (s.o.).

1. SKRIPT STARTEN:
   - Öffne in Finder den Ordner, in dem dieses Skript gespeichert ist.
   - Öffne über einen Rechtsklick auf den Ordner in der Pfadleiste unten im Finder ein Terminal in diesem Ordner.
     (Alternativ kopiere den Pfad, öffne ein neues Terminal und wechsle das Arbeitsverzeichnis dorthin: cd Pfad/Hier/Einfügen)
   - Starte das Skript mit: python3 qlabtimer.py

2. SHOW STARTEN:
   - Starte in QLab zu Stückbeginn den Wait Cue für die erste Szene
   - Fahre übrige Cues wie gewohnt.

3. SHOW BEENDEN:
   - Starte den Stückende-Cue. Danach kannst du die Show in QLab beenden.
   - Das Skript schreibt automatisch eine CSV-Datei mit allen Szenenlaufzeiten in das aktuelle Arbeitsverzeichnis (bei Vorgehen nach (1): Ordner des Skripts).
   - Beende das Terminal (Cmd+Q).
  
=========

# Scene Timer for QLab

Python script working with the free version of QLab 5 on macOS.

Since script/control cues aren't available in the free version of QLab, we use normal WAIT CUES as background stopwatches. The only thing that matters for our purposes is that these cues are running while a scene is going. The script can query all cues currently running in QLab (no matter whether Edit or Show mode) via AppleScript. While running, the script periodically queries these active cues at a fixed interval and evaluates them. This is how scene changes are registered and scene durations are calculated.

This script only observes which cues are running in QLab - it has no control over the show and does not start or stop any cues.

## SETUP IN QLAB

1. WAIT CUES FOR EACH SCENE:

   - Create a wait cue with a very long duration for each scene, longer than the maximum scene duration (e.g., a flat 04:00:00).
   - Name each wait cue so that it starts with the SCENE_PREFIX (e.g., "Scene") (i.e. "Scene 1" or "Scene 2a - Ophelia goes swimming").

2. SCENE TRANSITION:
   - At the end of Scene 1 / start of Scene 2, create:
     a) A stop cue (Target: Wait cue for Scene 1)
     b) A new wait cue for Scene 2 (e.g., "Scene 2", duration 99:99:00)
   - Start the new wait cue via auto-continue directly after the stop cue, or combine both in a "fire all" group.
   - This means each scene change involves two cues in QLab: stop the previous one, start the new one.

3. REHEARSAL INTERRUPTIONS / BREAKS:
   - If you press 'Pause' in the right-hand sidebar in QLab, the script detects the state, freezes the scene time and tracks the time the scene cue is paused.
   - If you subsequently resume the scene, the pause time is automatically subtracted from the scene and total duration. The final report also details the paused time per scene.
   - If following a pause you jump back within a scene, I'd advise to leave the wait on pause and manually restart it in the active cues window once you reach the point at which you originally paused.
   - If following an interruption you jump back to the start of a different scene: End the paused wait cue of the interrupted scene and start the wait cue of the scene you are restarting with.
   - If a scene previously timed is started again later, its new duration is saved as an additional CSV row; previous measurements are never overwritten.

4. END OF SHOW:
   - Create a cue at the end of the show with the name from END_CUE_NAME (e.g., "The End").
   - As soon as this cue is running, the script winds down the timer, takes into account any pause times accrued, writes the CSV and stops polling.

## RUNNING THE TIMER

PREREQUISITES:
   - macOS with Python 3.x installed (e.g. via Homebrew: brew install python3)
   - Free version of QLab 5 (https://qlab.app/download/) installed and workspace configured (see above).

1. STARTING THE SCRIPT:
   - Open the folder where the script is saved in Finder.
   - Open a terminal in this folder by right-clicking the folder in the path bar at the bottom of Finder.
     (Else, copy the path and change the working directory in a new terminal: cd /Paste/Your/PathHere)
   - Start the script: python3 qlabtimer.py

2. STARTING THE SHOW:
   - Start the wait cue for the first scene in QLab at the beginning of the piece.
   - Run any other cues as usual.

3. ENDING THE SHOW:
   - Start the end-of-piece cue. Afterwards, you can end the show in QLab.
   - The script automatically writes a CSV file with all scene durations to the current working directory (if following (1): the script's folder).
   - Close the terminal (Cmd+Q).

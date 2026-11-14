# blender-fun

Versuche mit Blender-Python. Der Workflow **Render Blender winter scene** führt die hochgeladene Hermes-Winterszene mit **Blender 4.5.15 LTS** auf einem GitHub-hosted **Ubuntu-24.04-CPU-Runner** aus.

## Rendern über GitHub Actions

1. In [Actions → Render Blender winter scene](../../actions/workflows/blender-render.yml) wechseln.
2. **Run workflow** auswählen und `preview` (schnell) oder `final` wählen.
3. Nach erfolgreichem Lauf auf der Run-Seite unter **Artifacts** das ZIP `winter-scene-*` herunterladen. Es enthält `winter_scene.png`, `winter_scene.blend` und `blender.log`.

Ein Push auf `main`, der den Workflow oder die Szene verändert, startet automatisch einen **Preview**-Render. Das spart CI-Rechenzeit. Der `final`-Modus ist über **Run workflow** manuell auswählbar.

| Modus | Auflösung | Cycles-Samples | Gerät |
| --- | --- | --- | --- |
| `preview` | 960 × 540 | 8 | CPU (2 Threads) |
| `final` | 1920 × 1080 | 48 | CPU (2 Threads) |

Eine GitHub-hosted Actions-VM hat **keine CUDA-GPU**. Die Laufzeit wird von der GitHub-Runner-Hardware und eventuellen Warteschlangen beeinflusst. GitHub Actions ist eine temporäre Ausführungsumgebung; Blender wird pro Lauf aus dem offiziellen Archiv heruntergeladen und mit der zugehörigen `.sha256`-Datei überprüft. Die Renderartefakte werden 14 Tage aufbewahrt.

## Lokal rendern

```bash
mkdir -p output
blender --background --factory-startup --threads 2 \
  --python scenes/winter_scene.py -- "$PWD/output/winter_scene.png"
python3 scripts/check_render.py output/winter_scene.png output/winter_scene.blend
```

Das Skript basiert auf der von Hermes erstellten Winterszene. Für den Vergleich mit dem ursprünglichen Render bleiben die Standardeinstellungen bei **1920×1080 / 48 Samples**. Die Anpassungen beschränken sich auf zuverlässige Ausgabepfade, optionale Preview-Parameter und das Speichern einer editierbaren `.blend`-Datei.

Mit `BLENDER_SAMPLES=8 BLENDER_RESOLUTION_PERCENT=50` wird ein kleiner Vorschaurender erstellt. Benutze den Konfigurationsworkflow nur für vertrauenswürdige Blender-Python-Skripte: Sie können wie andere Programme auf dem Runner Dateien lesen und Befehle ausführen. Deshalb führt dieser Workflow keine fremden Pull Requests automatisch aus.

# blender-fun

Experimentier- und Benchmark-Repository für **echte Blender-Python-Szenen** und GitHub Actions als reproduzierbare CPU-Renderfarm (Blender **4.5.15 LTS**, Cycles, OpenImageDenoise).

## Neue Referenz: „Midnight at the Winter Cabin“

Der bewusst anspruchsvollere Referenzentwurf unter [`scenes/reference_winter.py`](scenes/reference_winter.py) verwendet ausschließlich prozedurale Geometrie und Materialien, ohne externe Texturen oder Add-ons. Die Szene kombiniert einen detaillierten Schneemann, tief verschneite Nadelbäume, eine beleuchtete Holzhütte mit Giebeldach, eisige Pfade und Fußabdrücke, Laternen, Zaun, Berge, Sterne, Vollmond und winterliches Gegenlicht. Ein deterministischer Seed gewährleistet Wiederholbarkeit. Das Ergebnis ist als **gestaltete stilisierte 3D-Illustration**, nicht als Fotorealismus, gedacht.

[**Referenz-Workflow starten**](../../actions/workflows/reference-winter.yml) – im Dropdown `final` (1920×1080 / 48 Samples) oder `preview` (960×540 / 8 Samples) wählen. Ein Push mit Änderungen an der Referenz startet automatisch den Finalrender. Der Runner erzeugt `reference_winter.png`, `reference_winter.blend` und `reference_render.log` als ZIP-Artefakt (30 Tage).

## Hermes-Ausgangsszene (Baseline)

Die unveränderte gestalterische Hermes-Baseline liegt unter [`scenes/winter_scene.py`](scenes/winter_scene.py). Ihr Workflow ist [**Render Blender winter scene**](../../actions/workflows/blender-render.yml). Der Baseline-Finalrender verwendet 1920×1080 und 48 Samples; Vorschaurender nutzen 960×540 und 8 Samples.

## Reproduzieren (Blender 4.5.15)

```bash
mkdir -p output
BLENDER_RESOLUTION_PERCENT=100 BLENDER_SAMPLES=48 \
  blender --background --factory-startup --threads 4 \
  --python scenes/reference_winter.py -- "$PWD/output/reference_winter.png"
python3 scripts/check_render.py output/reference_winter.png output/reference_winter.blend
```

Der Vergleich sollte neben dem Bild insbesondere Geometrie, Licht, Materialien, Tiefenwirkung, Komposition, Zuverlässigkeit sowie **kumulierte Agenten-Inferenzzeit vs. reine Blender-Renderzeit** bewerten. Ein aufwendigerer Referenzentwurf darf erheblich länger rendern als die einfache Hermes-Szene; daraus allein lässt sich keine höhere Agentenqualität ableiten.

GitHub-hosted Actions-Runner besitzen standardmäßig **keine CUDA-GPU**; die Referenz verwendet CPU-Cycles. Der Workflow lädt das offizielle Blender-Archiv von den Blender-Mirrors herunter und kontrolliert die zugehörige SHA256-Datei. Blender-Python ist ausführbarer Programmcode; deshalb erfolgen keine automatischen Renderläufe für fremde Pull Requests.

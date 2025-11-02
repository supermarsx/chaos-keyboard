# Placeholder audio assets

The runtime generates lightweight sine-wave clips on demand. Run the helper
pipeline to refresh them when packaging builds:

```bash
python -m pipelines.audio_assets
```

This produces the following loopable WAV files in this directory:

- ``music_loop.wav`` – upbeat chiptune-style base loop.
- ``music_underwater_loop.wav`` – low-pass variant for the underwater gag.
- ``key_bleep.wav`` – short per-key sound effect.

Replace these clips with themed masters when preparing a release build.

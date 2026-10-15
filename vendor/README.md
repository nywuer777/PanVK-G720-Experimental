# UMA F1 source archive

Place exactly one source archive here:

`vendor/PanVK-G720-UMA-F1-source.zip`

Expected SHA-256:

`c0f343adcfdb6779df5642f4252308baed2c7e8b462181af79864c7471023d4a`

This archive is a locally prepared **slim source tree**, containing the PanVK G720 beta.2 source with the E20 performance parity and UMA Fase 1 patches already applied. It is not a compiled driver. Its Android build has not been validated.

Upload this ZIP into this folder on the `exp/uma-inteligente-fase1` branch. The GitHub Actions workflow `build-uma-f1.yml` is restricted to this branch and triggers on the archive upload. Do not upload to `main`.

Do not unzip it in the GitHub browser and do not commit APKs, keys, saves or device personal data.

# Brand assets (Grundfos)

HACS/Home Assistant zoekt de merk-afbeeldingen voor deze integratie hier als
lokale fallback. Plaats de Grundfos-logobestanden in deze map met exact deze
namen, formaten en afmetingen.

## Vereiste bestanden

| Bestand         | Afmeting  | Vorm             | Opmerking                          |
| --------------- | --------- | ---------------- | ---------------------------------- |
| `icon.png`      | 256×256   | vierkant         | verplicht                          |
| `icon@2x.png`   | 512×512   | vierkant         | aanbevolen (hi-DPI)                |
| `logo.png`      | max 256px hoog | vrije breedte | optioneel (volledig woordmerk)     |
| `logo@2x.png`   | max 512px hoog | vrije breedte | optioneel (hi-DPI)                 |

## Eisen aan de afbeeldingen

- Formaat: **PNG** met **transparante achtergrond**.
- Bijgesneden: geen overtollige witruimte rond het logo (trim).
- `icon*.png` moet strikt **vierkant** zijn.
- Gebruik het officiële Grundfos-logo waarvoor je gebruiksrechten hebt.

## Officiële publicatie

Bovenstaande map werkt als lokale HACS-fallback. Voor volledige, permanente
ondersteuning in Home Assistant dien je dezelfde assets in bij de officiële
brands-repository via een pull request:

- Repo: https://github.com/home-assistant/brands
- Locatie: `custom_integrations/magna3/` (`icon.png`, `icon@2x.png`,
  optioneel `logo.png`, `logo@2x.png`)
- Richtlijnen: https://github.com/home-assistant/brands#adding-a-new-brand

# Linker – werkafspraken

- Taal van de app, teksten, commits en changelog: Nederlands.
- **Bij elke wijziging:**
  1. voeg een entry toe aan `CHANGELOG.md` (secties *Toegevoegd*, *Gewijzigd*, *Opgelost*, *Migratie*) met de vergelijkingslink onderaan;
  2. verhoog `app/VERSION` (semver: minor voor functies, patch voor kleine aanpassingen en fixes);
  3. commit met een beschrijvende boodschap;
  4. tag `vX.Y.Z` (annotated) en push commits én tags. GitHub Actions bouwt dan de image `ghcr.io/richrdj/linker:X.Y.Z` en maakt de release aan.
- **Geen persoonlijke gegevens in de repo** (die is openbaar): geen eigen IP-adressen, domeinen, hostnamen of back-ups in README, changelog, commits of codecommentaar. Gebruik verzonnen voorbeelden (`192.168.1.10`, `voorbeeld.nl`).
- Nooit een database of back-up committen (`config/` en `*.db` staan in `.gitignore`).
- Schemawijzigingen: idempotente migratie in `db.init()` via `_add_column`. Nieuwe instellingen: toevoegen aan `DEFAULT_SETTINGS`.
- Geen externe scripts, fonts of CDN's in de pagina: Linker moet ook zonder internet werken. Alleen het ophalen van iconen gebruikt internet, en dat gebeurt op de server.
- Begrippen: in de app heten het *categorieën* en *snelkoppelingen*; in de code en database heten ze `collections` en `links`. Teksten voor de gebruiker altijd met de app-begrippen.
- Lokaal draaien: `DATA_DIR=./config uvicorn app.main:app --reload --port 5656`.

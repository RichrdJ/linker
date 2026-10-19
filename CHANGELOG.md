# Changelog

Alle noemenswaardige wijzigingen per versie. Nieuwste bovenaan.
Versienummers volgen [Semantic Versioning](https://semver.org/lang/nl/): het middelste cijfer gaat omhoog bij nieuwe functies, het laatste bij kleine aanpassingen en fixes.

Updaten in Portainer: open de stack → **Pull and redeploy**. De database wordt bij het opstarten automatisch bijgewerkt en je links blijven bewaard.

## [0.1.0] - 2026-10-19

### Toegevoegd
- Eerste versie van Linker: een zelf-gehoste startpagina en linkbeheerder.
- **Collecties → secties → links.** Collecties in een zijbalk, wisselen met een klik of `Alt`+`1` tot `9`. Linker onthoudt de laatst geopende collectie; elke collectie heeft een eigen adres (`/#3`).
- Links als **kaarten** in een raster, met de omschrijving of het adres eronder.
- **Direct bewerken op de pagina**: knoppen verschijnen bij een kaart of sectie (bewerken, adres kopiëren, A-Z sorteren). Kaarten, secties en collecties zijn te verslepen, ook naar een andere collectie in de zijbalk.
- **Zoekbalk** die alle collecties doorzoekt tijdens het typen. Enter opent de beste treffer, pijltjes kiezen een andere, Shift+Enter zoekt op het web. Een getypt adres (bv. `nas.lan:5000`) opent direct. Beginnen met typen of `/` zet de cursor in de zoekbalk.
- **Iconen**: automatisch de favicon van de site (ook voor diensten in je thuisnetwerk), een appnaam uit dashboard-icons of selfh.st/icons, een eigen upload, een afbeeldingsadres of een emoji. Iconen worden lokaal bewaard.
- **Bereikbaarheidscontrole** per link met een groen of rood bolletje, optioneel met een apart controle-adres. Een collectie met een onbereikbare dienst krijgt een rood bolletje in de zijbalk.
- **Uiterlijk**: licht, donker, OLED of automatisch, accentkleur, normale of compacte kaarten, en een eigen achtergrondafbeelding.
- **Importeren** van ctrlTAB-back-ups, Linkwarden-exports en browserbladwijzers (HTML uit Chrome, Firefox, Edge of Safari).
- **Back-up** downloaden en terugzetten als JSON.
- Optioneel **wachtwoord** om bewerken af te schermen; de startpagina zelf blijft voor iedereen bruikbaar.
- Installeerbaar als app (PWA).
- Docker-image voor amd64 en arm64 via GitHub Actions, met PUID/PGID.

[0.1.0]: https://github.com/RichrdJ/linker/releases/tag/v0.1.0

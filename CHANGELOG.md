# Changelog

Alle noemenswaardige wijzigingen per versie. Nieuwste bovenaan.
Versienummers volgen [Semantic Versioning](https://semver.org/lang/nl/): het middelste cijfer gaat omhoog bij nieuwe functies, het laatste bij kleine aanpassingen en fixes.

Updaten in Portainer: open de stack → **Pull and redeploy**. De database wordt bij het opstarten automatisch bijgewerkt en je links blijven bewaard.

## [0.2.2] - 2026-10-19

### Gewijzigd
- De standaard accentkleur is nu hetzelfde blauw als het logo, in plaats van geel. Dat geldt voor knoppen, de actieve categorie, de zoekbalk en selecties. Geel staat nog bij de keuzekleuren in *Instellingen → Thema*.

### Migratie
- Had je de gele standaardkleur, dan wordt die bij het opstarten automatisch blauw. Een zelf gekozen andere kleur blijft staan.

## [0.2.1] - 2026-10-19

### Gewijzigd
- Het logo is blauw in plaats van geel, en heeft een vaste kleur los van de accentkleur. Ook het tabbladicoon en het app-icoon (PWA) zijn aangepast.

## [0.2.0] - 2026-10-19

### Toegevoegd
- **Snel snelkoppelingen toevoegen**: een knop *+ Snelkoppeling* naast de zoekbalk. Vul alleen het adres in; de naam wordt automatisch de titel van de pagina (voor de voorpagina van een site de korte sitenaam).
- **Plakken en slepen**: plak een adres met Ctrl+V ergens op de pagina, of sleep een link of het adres uit een ander tabblad op de pagina. Het toevoegvenster opent dan met het adres al ingevuld.
- **Bladwijzer-knop "+ Naar Linker"** (in *Instellingen*): sleep hem naar je bladwijzerbalk en bewaar elke website met één klik. Na het opslaan ga je terug naar de pagina.
- Bij de eerste start staan de categorieën **Privé** en **Werk** klaar.

### Gewijzigd
- *Collecties* heten nu **categorieën** en links heten **snelkoppelingen**. De zijbalk heeft het kopje *Categorieën*.
- Het toevoegvenster is korter: adres, naam en categorie staan bovenaan; omschrijving, icoon en online-controle zitten onder *Meer opties*.
- Na het toevoegen spring je naar de categorie waar de snelkoppeling in staat.
- De online-controle staat voor nieuwe snelkoppelingen alleen standaard aan bij adressen in je thuisnetwerk (IP-adres, `.lan`, `.local` en dergelijke). Bestaande snelkoppelingen houden hun instelling.
- Onder een snelkoppeling staat het adres zonder `www.`.

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

[0.2.2]: https://github.com/RichrdJ/linker/compare/v0.2.1...v0.2.2
[0.2.1]: https://github.com/RichrdJ/linker/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/RichrdJ/linker/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/RichrdJ/linker/releases/tag/v0.1.0

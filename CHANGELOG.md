# Changelog

Alle noemenswaardige wijzigingen per versie. Nieuwste bovenaan.
Versienummers volgen [Semantic Versioning](https://semver.org/lang/nl/): het middelste cijfer gaat omhoog bij nieuwe functies, het laatste bij kleine aanpassingen en fixes.

Updaten in Portainer: open de stack → **Pull and redeploy**. De database wordt bij het opstarten automatisch bijgewerkt en je links blijven bewaard.

## [0.8.0] - 2026-10-19

### Toegevoegd
- **Eigen kleur per categorie**: kies bij het bewerken van een categorie (het potlood in de zijbalk) een kleur, of laat hem de algemene accentkleur volgen. Open je die categorie, dan kleuren de knoppen, de selecties, het logo en het icoon in je browsertabblad mee. In de zijbalk krijgt elke categorie haar eigen tint. Het icoon op je beginscherm houdt de algemene kleur.
- **Weer in de zijbalk**: vul onder *Instellingen → Weergave* bij *Weer voor* een plaats in. Onder de klok staan dan de temperatuur, een klein icoontje en het weertype, bijvoorbeeld *12° Half bewolkt · Utrecht*. Als de zijbalk is ingeklapt, staan alleen het icoontje en de temperatuur er. Het weer komt van Open-Meteo (gratis, zonder account), wordt alleen door de server opgehaald en elk kwartier ververst. Op je telefoon blijft het verborgen, net als de klok.

### Migratie
- De database krijgt automatisch een kolom voor de kleur van een categorie. Bestaande categorieën volgen de algemene accentkleur.

## [0.7.5] - 2026-10-19

### Gewijzigd
- Ook in de **uitgeklapte zijbalk** is de actieve categorie geen vol gekleurd vlak meer. Hij krijgt een zachte tint van je accentkleur, een dunne rand en een accentlijntje aan de linkerkant; het aantal en het potlood staan in de accentkleur. Op je telefoon krijgt het actieve pilletje dezelfde zachte tint.

## [0.7.4] - 2026-10-19

### Gewijzigd
- De **ingeklapte zijbalk** ziet er verfijnder uit. Elke categorie is een klein omlijnd tegeltje van gelijke maat, netjes onder het logo uitgelijnd. Een dunne lijn scheidt het logo van de categorieën. De actieve categorie krijgt een zachte tint van je accentkleur met een dun lijntje aan de linkerkant, in plaats van een groot gekleurd vlak. Het rode bolletje voor een onbereikbare snelkoppeling staat op de hoek van het tegeltje.

## [0.7.3] - 2026-10-19

### Gewijzigd
- Het **online-bolletje** staat nu rechtsonder in de kaart in plaats van rechtsboven.

## [0.7.2] - 2026-10-19

### Gewijzigd
- De **klok en datum** staan nu rustig onderin de zijbalk, boven *Instellingen*: kleiner en in grijstinten. Als de zijbalk is ingeklapt, staat alleen de tijd er. Op je telefoon blijft de klok verborgen.
- Rechtsboven staat alleen nog *+ Sectie*. Als je niet mag bewerken, is die regel helemaal weg, zodat de snelkoppelingen direct bovenaan beginnen.

## [0.7.1] - 2026-10-19

### Gewijzigd
- Smallere kaarten, zodat er meer snelkoppelingen naast elkaar passen. Ze vullen de rij nog steeds precies tot de rand. Het icoon is iets kleiner, en bij *Compact* zijn de kaarten ook smaller.

## [0.7.0] - 2026-10-19

### Toegevoegd
- **Vanzelf op meest bezocht**: kies onder *Instellingen → Weergave → Volgorde snelkoppelingen* voor *Meest bezocht eerst, vanzelf*. Elke sectie zet dan de snelkoppelingen die je het vaakst opent bovenaan, zonder dat je op een knop hoeft te drukken. Bij een gelijk aantal komt de laatst geopende eerst, daarna blijft je eigen volgorde staan. De nieuwe volgorde zie je zodra je de pagina opnieuw opent, zodat er niets verspringt terwijl je klikt.
- In deze stand kun je snelkoppelingen niet slepen en zijn de sorteerknoppen verborgen. Secties slepen kan nog wel. Zet de volgorde terug op *Eigen volgorde* en je oude volgorde is er weer.

## [0.6.0] - 2026-10-19

### Toegevoegd
- **Sorteren op meest bezocht**: Linker telt hoe vaak je een snelkoppeling opent: met een klik, in een nieuw tabblad (Ctrl-klik of middelste muisknop) of met Enter vanuit zoeken. Naast *Sorteren van A tot Z* staat bij elke sectie een knop *Sorteren op meest bezocht*. Bij een gelijk aantal komt de laatst geopende eerst. Net als A tot Z zet de knop de volgorde één keer vast; daarna kun je nog gewoon slepen.
- Beweeg over een snelkoppeling om te zien hoe vaak je hem hebt geopend.

### Migratie
- De database krijgt automatisch twee kolommen voor het aantal bezoeken. Tellen begint vanaf deze versie, dus in het begin staan alle tellers op 0.

## [0.5.1] - 2026-10-19

### Gewijzigd
- Minder lege ruimte bovenaan de pagina: de klok en de knop *+ Sectie* staan dichter bij de bovenrand, en de eerste sectie begint direct daaronder.

## [0.5.0] - 2026-10-19

### Toegevoegd
- **Loginpagina**: zet *Inloggen verplicht voor de hele startpagina* aan onder *Instellingen → Wachtwoord en inloggen*. Zonder login is dan alleen een nette loginpagina te zien, dus je kunt Linker via een reverse proxy met HTTPS aan internet koppelen. Kies of je 30 dagen ingelogd blijft of na 12 uur wordt uitgelogd. Uitloggen kan onderin de zijbalk.
- **Bescherming tegen raden**: na 5 foute pogingen vanaf hetzelfde adres volgt een blokkade van 15 minuten. Bij meer dan 30 foute pogingen in totaal binnen 15 minuten worden alle logins tijdelijk geweigerd. Mislukte pogingen komen in het log.
- Het sessiecookie krijgt automatisch de vlag *Secure* als Linker via HTTPS wordt geopend. Extra beveiligingsheaders, en met verplicht inloggen mag de pagina niet in een frame van een andere site worden geladen.
- **Wachtwoord vergeten**: start de container eenmalig met `RESET_PASSWORD=1`.

### Gewijzigd
- Een nieuw wachtwoord moet minstens 8 tekens hebben. Je huidige wachtwoord blijft gewoon werken.
- Na een nieuw wachtwoord zijn alle andere apparaten uitgelogd.
- Een back-up terugzetten verandert niets aan het verplicht inloggen.

### Migratie
- Had je bewerken al beveiligd met een wachtwoord? Dan moet je na de update op elk apparaat één keer opnieuw ontgrendelen.

## [0.4.1] - 2026-10-19

### Gewijzigd
- Het **potlood om een categorie te bewerken** staat nu in de zijbalk, bij elke categorie zelf. Het verschijnt als je met de muis over de categorie beweegt, op de plek van het aantal. Op je telefoon staat het in het pilletje van de actieve categorie.
- De knoppen **Bewerken** en **Adres kopiëren** op een snelkoppeling staan nu klein onder elkaar, met bewerken bovenaan.

## [0.4.0] - 2026-10-19

### Toegevoegd
- **Zijbalk inklappen**: met de knop *Inklappen* onderin wordt de zijbalk een smalle strook met het logo, de knoppen en per categorie het icoon of de beginletter. Klik nog eens om hem weer uit te klappen. Je keuze wordt per browser onthouden. Op je telefoon verandert er niets.

### Gewijzigd
- De naam van de categorie (zoals *Privé* of *Werk*) staat niet meer groot boven de pagina. Welke categorie actief is, zie je in de zijbalk.
- De knop **+ Sectie** rechtsboven is een rustige knop zonder rand geworden, die pas duidelijker wordt als je eroverheen beweegt.
- De knop *Zoeken* onderin de zijbalk is weg. Zoeken werkt nog steeds: begin gewoon te typen of druk op `/`. Op je telefoon blijft het vergrootglas bovenaan staan, omdat je daar niet zomaar kunt beginnen met typen.
- De **accentkleur** geldt nu overal: ook voor het logo in de zijbalk, het icoon in het browsertabblad en het icoon op je beginscherm of als geïnstalleerde app. Bij een lichte accentkleur wordt de schakel in het logo donker, net als de tekst op knoppen.

## [0.3.1] - 2026-10-19

### Gewijzigd
- Categorieën in de zijbalk staan er standaard zonder icoon of bolletje. Wil je ze toch, zet dan **Iconen bij categorieën** aan onder *Instellingen → Weergave*. Daarna kun je per categorie een icoon of emoji kiezen via het potlood.

## [0.3.0] - 2026-10-19

### Toegevoegd
- **Zijbalk breder of smaller maken**: sleep de rechterrand van de zijbalk (een blauwe lijn verschijnt als je eroverheen beweegt). De breedte loopt van 170 tot 440 pixels en wordt per browser onthouden. Dubbelklik op de rand voor de standaardbreedte. Met het toetsenbord: Tab naar de rand en gebruik de pijltjes links en rechts.

## [0.2.7] - 2026-10-19

### Gewijzigd
- De **+** voor een nieuwe categorie staat nu naast het kopje *Categorieën*, net als de + naast een sectienaam: altijd licht zichtbaar, blauw als je eroverheen beweegt. Op je telefoon staat hij achter de tabs.

## [0.2.6] - 2026-10-19

### Gewijzigd
- De knop *+ Categorie* is vervangen door een subtiele **+** onder de categorieën. Die verschijnt pas als je met de muis over de categorieën beweegt. Op een touchscreen blijft hij zichtbaar.

## [0.2.5] - 2026-10-19

### Gewijzigd
- Het potlood naast de naam van de categorie verschijnt alleen als je met de muis over de kop beweegt. Op een touchscreen blijft het zichtbaar.

## [0.2.4] - 2026-10-19

### Gewijzigd
- De zoekbalk bovenaan is weg. Zoeken werkt nog steeds: begin gewoon te typen of druk op `/`, dan verschijnt de balk. Met `Esc` of door ernaast te klikken verdwijnt hij weer. In de zijbalk staat een knop *Zoeken*, ook handig op je telefoon.
- De klok staat nu rechts naast de naam van de categorie.

## [0.2.3] - 2026-10-19

### Gewijzigd
- De grote knop *+ Snelkoppeling* naast de zoekbalk is weg. Toevoegen gaat nu met een subtiele **+** naast elke sectienaam, die direct in die sectie toevoegt. Plakken, slepen en de bladwijzer-knop werken zoals voorheen.
- Het vinkje **Controleren of hij online is** staat direct zichtbaar in het toevoegvenster, niet meer onder *Meer opties*. Het staat standaard uit, ook voor adressen in je thuisnetwerk.

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

[0.8.0]: https://github.com/RichrdJ/linker/compare/v0.7.5...v0.8.0
[0.7.5]: https://github.com/RichrdJ/linker/compare/v0.7.4...v0.7.5
[0.7.4]: https://github.com/RichrdJ/linker/compare/v0.7.3...v0.7.4
[0.7.3]: https://github.com/RichrdJ/linker/compare/v0.7.2...v0.7.3
[0.7.2]: https://github.com/RichrdJ/linker/compare/v0.7.1...v0.7.2
[0.7.1]: https://github.com/RichrdJ/linker/compare/v0.7.0...v0.7.1
[0.7.0]: https://github.com/RichrdJ/linker/compare/v0.6.0...v0.7.0
[0.6.0]: https://github.com/RichrdJ/linker/compare/v0.5.1...v0.6.0
[0.5.1]: https://github.com/RichrdJ/linker/compare/v0.5.0...v0.5.1
[0.5.0]: https://github.com/RichrdJ/linker/compare/v0.4.1...v0.5.0
[0.4.1]: https://github.com/RichrdJ/linker/compare/v0.4.0...v0.4.1
[0.4.0]: https://github.com/RichrdJ/linker/compare/v0.3.1...v0.4.0
[0.3.1]: https://github.com/RichrdJ/linker/compare/v0.3.0...v0.3.1
[0.3.0]: https://github.com/RichrdJ/linker/compare/v0.2.7...v0.3.0
[0.2.7]: https://github.com/RichrdJ/linker/compare/v0.2.6...v0.2.7
[0.2.6]: https://github.com/RichrdJ/linker/compare/v0.2.5...v0.2.6
[0.2.5]: https://github.com/RichrdJ/linker/compare/v0.2.4...v0.2.5
[0.2.4]: https://github.com/RichrdJ/linker/compare/v0.2.3...v0.2.4
[0.2.3]: https://github.com/RichrdJ/linker/compare/v0.2.2...v0.2.3
[0.2.2]: https://github.com/RichrdJ/linker/compare/v0.2.1...v0.2.2
[0.2.1]: https://github.com/RichrdJ/linker/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/RichrdJ/linker/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/RichrdJ/linker/releases/tag/v0.1.0

# Linker

Een lichte, zelf-gehoste startpagina en linkbeheerder voor je homelab. Je links staan in **collecties** (Homelab, Thuis, Werk…), elk met eigen **secties** vol kaarten. Iconen verschijnen vanzelf, een bolletje laat zien of een dienst bereikbaar is, en de zoekbalk doorzoekt alles tegelijk.

Alles draait in één container met SQLite. De pagina laadt geen scripts, fonts of trackers van buitenaf, dus hij werkt ook zonder internet. Alle instellingen doe je in de app zelf; in Portainer hoef je niets in te vullen.

![Startpagina](docs/images/startpagina-dark.png)

## Functies

- **Collecties → secties → links.** Collecties staan in de zijbalk; wisselen met een klik of `Alt`+`1` tot `9`. Linker onthoudt waar je was.
- **Direct bewerken op de pagina.** Beweeg over een kaart of sectie voor de knoppen (bewerken, adres kopiëren, A-Z sorteren). Sleep kaarten, secties en collecties om de volgorde te wijzigen. Laat een kaart of sectie op een collectie in de zijbalk vallen om hem te verplaatsen.
- **Zoeken met het toetsenbord**: begin gewoon met typen of druk op `/`.
  - Doorzoekt alle collecties tegelijk (naam, omschrijving en adres).
  - `Enter` opent de beste treffer, `↑` `↓` kiest een andere, `Esc` wist.
  - `Shift`+`Enter` zoekt op het web: DuckDuckGo, Google, Startpage, Bing, Brave, Kagi, Ecosia of een eigen zoekmachine.
  - Typ je een adres zoals `nas.lan:5000`, dan opent `Enter` dat direct.
- **Iconen** zonder gedoe. Het veld *Icoon* kan zijn:
  - leeg: de favicon van de site zelf. Linker haalt die op vanaf de server, dus het werkt ook voor diensten in je thuisnetwerk;
  - een appnaam zoals `sonarr`, `plex` of `home-assistant`: uit [dashboard-icons](https://github.com/homarr-labs/dashboard-icons), anders [selfh.st/icons](https://github.com/selfhst/icons). Met `di:` of `sh:` ervoor kies je de bron zelf;
  - een zelf geüpload bestand (PNG, SVG, ICO, JPG of WebP);
  - een afbeeldingsadres (`https://…`) of een emoji.

  Iconen worden in `/config` bewaard en daarna lokaal geserveerd. Lukt het niet, dan krijg je een gekleurde tegel met de eerste letter.
- **Bereikbaarheid**: Linker controleert periodiek elke link en toont een groen of rood bolletje; een collectie met een onbereikbare dienst krijgt een rood bolletje in de zijbalk. 401/403 telt als bereikbaar (de dienst draait, je bent alleen niet ingelogd). Zelfondertekende certificaten zijn geen probleem. Per link kun je een apart controle-adres opgeven, bijvoorbeeld `http://sonarr:8989` als de link zelf via je domein loopt.
- **Uiterlijk**: licht, donker, OLED of automatisch, een eigen accentkleur, normale of compacte kaarten, en een eigen achtergrondafbeelding.
- **Importeren** van een ctrlTAB-back-up, een Linkwarden-export of de bladwijzers uit je browser (HTML-export uit Chrome, Firefox, Edge of Safari; elke map wordt een sectie). Geïmporteerde links worden niet op bereikbaarheid gecontroleerd; zet dat per link aan als je wilt.
- **Back-up** downloaden en terugzetten als JSON.
- **Bewerken beveiligen** met een optioneel wachtwoord. De startpagina blijft voor iedereen bruikbaar; alleen wijzigen vraagt om het wachtwoord.
- **Installeerbaar als app** (PWA) op telefoon en desktop.

![Zoeken](docs/images/zoeken-dark.png)

## Installeren in Portainer

### Optie A: Web editor met kant-en-klare image (aanbevolen)

GitHub Actions bouwt bij elke push naar `main` een image: `ghcr.io/richrdj/linker:latest` (amd64 + arm64).

1. Portainer → **Stacks** → **Add stack** → **Web editor**
2. Plak de inhoud van [`portainer-stack.yml`](portainer-stack.yml).
3. **Deploy the stack** → open `http://<server>:5656`

> Is de repository privé? Maak dan het package op GitHub openbaar (Packages → linker → Package settings → Change visibility), of voeg `ghcr.io` toe als registry in Portainer met een GitHub-token met de scope `read:packages`.

### Optie B: Rechtstreeks vanuit Git (Portainer bouwt zelf)

1. Portainer → **Stacks** → **Add stack** → **Repository**
2. Repository URL: `https://github.com/RichrdJ/linker`, Compose path: `docker-compose.yml`
3. Bij een privé-repo: zet *Authentication* aan en gebruik een GitHub-token.
4. Deploy. Met *GitOps updates* haalt Portainer nieuwe versies automatisch op.

### Optie C: docker compose

```bash
git clone https://github.com/RichrdJ/linker.git && cd linker
docker compose up -d --build
```

### Als startpagina van je browser

Stel `http://<server>:5656` in als startpagina en als pagina voor nieuwe tabbladen (in Chrome en Firefox kan dat laatste met een extensie zoals *New Tab Redirect*). Wil je Linker buiten je thuisnetwerk gebruiken, zet er dan een reverse proxy met HTTPS voor, bijvoorbeeld Nginx Proxy Manager, Traefik of Caddy, en stel een wachtwoord in.

De database staat in het volume `linker-config` (`/config/linker.db`, met geüploade iconen en achtergrond in `/config/uploads`). Neem dat volume mee in je back-ups, of download af en toe een back-up via *Instellingen*.

## Omgevingsvariabelen

| Variabele | Standaard | Uitleg |
|---|---|---|
| `TZ` | – | Tijdzone |
| `PUID` / `PGID` | (root) | Gebruiker/groep die eigenaar wordt van `/config` |
| `PORT` | `5656` | Poort binnen de container |
| `LOG_LEVEL` | `INFO` | |

## Lokaal ontwikkelen

```bash
pip install -r requirements.txt
DATA_DIR=./config uvicorn app.main:app --reload --port 5656
```

Open daarna http://localhost:5656.

## Versies

Alle wijzigingen per versie staan in [CHANGELOG.md](CHANGELOG.md) en onder [Releases](https://github.com/RichrdJ/linker/releases). Het versienummer van je installatie staat onderaan *Instellingen*.

- `:latest` volgt `main`, `:0.1.0` is een vaste versie.
- Wil je zelf bepalen wanneer je updatet? Zet dan een vast versienummer in `portainer-stack.yml`, bijvoorbeeld `:0.1.0`.

**Nieuwe versie uitbrengen:** werk `CHANGELOG.md` en `app/VERSION` bij, commit, en push met een tag:

```bash
git tag -a v0.2.0 -m "v0.2.0" && git push && git push --tags
```

GitHub Actions bouwt dan de image `:0.2.0` en maakt de release aan met de tekst uit de changelog.

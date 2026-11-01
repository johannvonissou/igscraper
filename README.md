# igscraper

`igscraper` est un client Python **asynchrone** et une **CLI** pour interagir avec Instagram : connexion, recherche de comptes, lecture de profils, abonnements, lecture des conversations et envoi de messages privés.

Le navigateur est piloté avec **[Patchright](https://github.com/Kaliiiiiiiiii-Vinyzu/patchright)**, un fork furtif de Playwright. Les sessions sont persistantes et les médias sont bloqués par défaut pour accélérer les traitements.

> ⚠️ Projet non officiel, sans affiliation avec Instagram. Utilisez-le dans le respect des conditions d'utilisation d'Instagram et des lois applicables.

---

## Sommaire

- [Fonctionnalités](#fonctionnalités)
- [Prérequis](#prérequis)
- [Installation](#installation)
- [Démarrage rapide](#démarrage-rapide)
- [Référence CLI](#référence-cli)
  - [Options communes](#options-communes)
  - [`chrome` : gérer Chrome](#chrome--gérer-chrome)
  - [`login` : se connecter](#login--se-connecter)
  - [`logout` / `disconnect` : se déconnecter](#logout--disconnect--se-déconnecter)
  - [`search` : rechercher des comptes](#search--rechercher-des-comptes)
  - [`account` : consulter un profil](#account--consulter-un-profil)
  - [`follow` : s'abonner](#follow--sabonner)
  - [`messages` : lire une conversation](#messages--lire-une-conversation)
  - [`send` : envoyer un message](#send--envoyer-un-message)
  - [`console` : console interactive](#console--console-interactive)
- [Sorties JSON](#sorties-json)
- [API Python](#api-python)
- [Comportement et robustesse](#comportement-et-robustesse)
- [Structure du projet](#structure-du-projet)
- [Constantes](#constantes)
- [Gestion des erreurs](#gestion-des-erreurs)
- [Développement](#développement)
- [Limitations et responsabilité](#limitations-et-responsabilité)
- [Crédits](#crédits)

---

## Fonctionnalités

| Domaine | Ce que fait `igscraper` |
| --- | --- |
| Connexion | Connexion par identifiants, par cookie `sessionid`, ou réutilisation d'un profil persistant. |
| Challenges | Détection des CAPTCHA, 2FA, checkpoints et résolution manuelle avec `--headed`. |
| Recherche | Union des résultats « Pour vous » et « Non personnalisé » : nom, handle, abonnés et URL. |
| Profils | Nom, bio, lien, adresse, statut privé, statistiques, dernier suivi et dernières publications. |
| Abonnements | Abonnement à un compte, avec confirmation de l'état (`Suivi(e)` ou demande en attente). |
| Messages | Lecture de l'historique d'une conversation, pagination automatique et affichage des N derniers messages. |
| Envoi | Envoi d'un message privé, confirmation de l'envoi et relecture optionnelle de l'historique. |
| Chrome | Téléchargement, installation et nettoyage de Chrome et de ses profils. |
| Furtivité | Patchright, user-agent cohérent, locale/timezone, profil persistant, blocage des médias. |
| Sorties | Rendu terminal coloré ou JSON brut pour l'automatisation. |
| Console | Console interactive `igscraper console` : une requête par commande, avec chrono. |
| Intégration | API Python asynchrone, classes de service réutilisables et helpers de session. |

---

## Prérequis

- **Python ≥ 3.11**
- **[uv](https://github.com/astral-sh/uv)** (recommandé)
- **Linux** pour l'installation automatique de Chrome (`chrome install`)
- Un binaire Chrome/Chromium installé dans `vendor/chrome/chrome` (ou lancez `igscraper chrome install` / `make build`)

---

## Installation

```bash
cd igscraper

uv sync
uv run igscraper chrome install
```

`uv run igscraper` exécute la CLI sans installation globale. Après `uv sync`, vous pouvez aussi activer l'environnement et appeler directement `igscraper`.

### Raccourci avec `make`

```bash
make build   # uv sync + installation de Chrome dans vendor/chrome
make check   # lint Ruff + vérification de la syntaxe Python
```

---

## Démarrage rapide

### 1. Installer Chrome

```bash
uv run igscraper chrome install
```

### 2. Se connecter et récupérer un `sessionid`

```bash
uv run igscraper login --username "mon_compte" --password "mon_mot_de_passe"
```

Pour un CAPTCHA ou une validation 2FA, affichez le navigateur :

```bash
uv run igscraper login --username "mon_compte" --password "mon_mot_de_passe" --headed
```

Le `sessionid` affiché peut ensuite être réutilisé avec `--sessionid`.

### 3. Explorer un profil

```bash
uv run igscraper account "instagram"
```

### 4. Lire et envoyer des messages

```bash
uv run igscraper messages "instagram" --sessionid "VOTRE_SESSIONID" --last 10
uv run igscraper send "instagram" "Bonjour !" --sessionid "VOTRE_SESSIONID"
```

---

## Référence CLI

La CLI est disponible via :

```bash
igscraper <COMMANDE> [OPTIONS]
# ou
python -m igscraper <COMMANDE> [OPTIONS]
```

### Options communes

Ces options sont acceptées par les commandes qui ouvrent un navigateur :

| Option | Description |
| --- | --- |
| `--headed` | Affiche la fenêtre du navigateur. Nécessaire pour résoudre un challenge manuellement. |
| `--load-media` | Télécharge images et vidéos. Les médias sont bloqués par défaut. |
| `--json` | Écrit uniquement le JSON final sur `stdout` et désactive les journaux. |
| `--sessionid COOKIE` | Réutilise un cookie `sessionid` existant. |
| `--username USER` | Compte Instagram utilisé pour la connexion. |
| `--password PASS` | Mot de passe Instagram. |
| `--log-level LEVEL` | Verbosité : `DEBUG`, `INFO`, `WARNING` ou `ERROR`. Défaut : `INFO`. |

Option globale :

| Option | Description |
| --- | --- |
| `--version` | Affiche la version d'`igscraper`. |

> Les journaux sont écrits sur `stderr`. En mode `--json`, seul le résultat JSON est écrit sur `stdout`, ce qui permet de rediriger la sortie sans pollution.

### `chrome` : gérer Chrome

#### `chrome install`

Télécharge le paquet `.deb` officiel de Google Chrome, l'extrait dans `vendor/chrome` et vérifie que le binaire démarre.

```bash
igscraper chrome install
```

Options :

| Option | Description |
| --- | --- |
| `--force` | Réinstalle même si Chrome est déjà présent. |
| `--url URL` | Utilise un paquet `.deb` personnalisé. L'URL doit être en **HTTPS**. |
| `--json` | Affiche le résultat en JSON. |

Exemple :

```bash
igscraper chrome install --force --url "https://exemple.com/google-chrome.deb"
```

#### `chrome clean`

Supprime Chrome, le profil persistant et les profils supplémentaires indiqués.

```bash
igscraper chrome clean
```

Options :

| Option | Description |
| --- | --- |
| `--dry-run` | Affiche les éléments et leur taille sans rien supprimer. |
| `-y`, `--yes` | Ne demande pas de confirmation. |
| `--keep-profile` | Conserve le profil persistant par défaut (la session est gardée). |
| `--keep-chrome` | Conserve l'installation de Chrome. |
| `--profile DIR` | Ajoute un profil à supprimer. Répétable. |
| `--json` | Affiche le résultat en JSON. |

Exemples :

```bash
igscraper chrome clean --dry-run
igscraper chrome clean --keep-profile -y
```

> Pour un usage non interactif (script, CI), ajoutez `-y`. Sans `-y`, une confirmation est demandée si l'entrée standard est un terminal.

### `login` : se connecter

Se connecte avec des identifiants, un `sessionid`, ou tente de réutiliser le profil persistant.

```bash
igscraper login --username "mon_compte" --password "mon_mot_de_passe"
igscraper login --sessionid "VOTRE_SESSIONID"
igscraper login --username "mon_compte" --password "mon_mot_de_passe" --headed
```

La commande renvoie le `sessionid` et la méthode utilisée (`password`, `cookie`, `sessionid` ou `auto`).

### `logout` / `disconnect` : se déconnecter

Efface les cookies de session du navigateur courant.

```bash
igscraper logout
igscraper disconnect
```

`logout` et `disconnect` sont deux alias de la même action.

### `search` : rechercher des comptes

```bash
igscraper search "openai"
igscraper search "openai" --json
```

La recherche récupère d'abord les résultats de l'onglet **« Pour vous »** (onglet par défaut), puis sélectionne l'onglet **« Non personnalisé »** et renvoie l'**union** des deux listes : les comptes « Pour vous » en premier, sans doublon, les champs manquants (comme le nombre d'abonnés) étant complétés par l'autre onglet. Seuls les comptes affichés dans la liste de résultats sont retenus (l'historique « Récent » et l'avatar du compte connecté sont ignorés).

Le résultat contient le handle, le nom affiché, le nombre d'abonnés, l'URL du profil et l'URL de la photo de profil.

### `account` : consulter un profil

```bash
igscraper account "instagram"
igscraper account "instagram" --json
```

Les informations extraites comprennent :

- le nom d'utilisateur et le nom affiché ;
- le statut privé et l'état d'abonnement ;
- le nombre de publications, d'abonnés et d'abonnements ;
- la bio, le lien externe et l'adresse ;
- les dernières publications visibles.

### `follow` : s'abonner

```bash
igscraper follow "un_compte" --sessionid "VOTRE_SESSIONID"
```

La commande vérifie l'état après le clic. Pour un compte privé, elle indique qu'une demande d'abonnement est en attente.

### `messages` : lire une conversation

```bash
igscraper messages "instagram" --sessionid "VOTRE_SESSIONID"
igscraper messages "instagram" --sessionid "VOTRE_SESSIONID" --last 10
```

`--last N` limite uniquement l'affichage aux N derniers messages (`--last 0` affiche tout). La récupération de l'historique reste paginée automatiquement.

### `send` : envoyer un message

```bash
igscraper send "instagram" "Bonjour !" --sessionid "VOTRE_SESSIONID"
igscraper send "instagram" "Bonjour !" --sessionid "VOTRE_SESSIONID" --history
igscraper send "instagram" "Bonjour !" --sessionid "VOTRE_SESSIONID" --history --last 20
```

| Option | Description |
| --- | --- |
| `--history` | Relit l'historique après l'envoi. |
| `--last N` | Avec `--history`, n'affiche que les N derniers messages (défaut : 10, `0` = tous). |

L'envoi est confirmé en vérifiant qu'une nouvelle occurrence du message apparaît dans la conversation. Les retours à la ligne (`\n`) sont conservés dans un seul message.

### `console` : console interactive

```bash
igscraper console
igscraper console --headed
igscraper console --sessionid "VOTRE_SESSIONID"
```

Le navigateur et la session sont ouverts une seule fois au démarrage (réutilisation du profil persistant par défaut), puis chaque commande exécute une requête et affiche sa durée. La console accepte les options communes ; le niveau de journalisation par défaut est `WARNING`.

```text
login                                   réutiliser la session du profil persistant
login <utilisateur> <mot_de_passe>      se connecter avec des identifiants
login --sessionid <cookie>              se connecter avec un cookie sessionid
logout                                  effacer les cookies de session
search <texte>                          rechercher des comptes
account <compte>                        lire un profil
follow <compte>                         s'abonner à un compte
messages <compte> [--last N]            lire une conversation (défaut : 10, 0 = tout)
send <compte> <texte> [--history] [--last N]
                                        envoyer un message privé
status                                  état du navigateur et de la session
headless [on|off]                       relancer le navigateur en mode headless ou visible
json [on|off]                           afficher les réponses brutes en JSON
help                                    afficher l'aide
quit / exit                             quitter
```

Chaque commande accepte `--json` pour une réponse brute ponctuelle. Alias : `profile` (`account`), `msgs` (`messages`), `dm` (`send`), `disconnect` (`logout`).

```text
ig> account instagram
→ account…
👤 @instagram  Instagram
...
⏱  1.42 s
```

---

## Sorties JSON

Chaque commande accepte `--json`. Les journaux sont alors coupés et seuls les résultats sont écrits sur `stdout`.

### `login`

```json
{
  "sessionId": "123456789:abcdef...",
  "method": "password"
}
```

### `search`

```json
[
  {
    "profilePictureUrl": "https://...",
    "username": "instagram",
    "name": "Instagram",
    "followersCount": 686000000,
    "url": "https://www.instagram.com/instagram/"
  }
]
```

### `account`

```json
{
  "username": "instagram",
  "name": "Instagram",
  "appearsPrivate": false,
  "isFollowed": false,
  "postsCount": 1234,
  "followersCount": 500000000,
  "followingCount": 200,
  "bio": "Description du compte",
  "address": null,
  "url": "https://example.com",
  "latestPosts": [
    {
      "description": "Texte alternatif de l'image",
      "imageUrl": "https://...",
      "url": "https://www.instagram.com/instagram/p/ABC123/"
    }
  ]
}
```

### `messages`

```json
{
  "username": "instagram",
  "messages": [
    {
      "index": 1,
      "timestamp": 1700000000,
      "sender": "instagram",
      "isSelf": false,
      "content": "Bonjour !"
    }
  ]
}
```

Les médias sont remplacés par des marqueurs lisibles : `<photo>`, `<vidéo>`, `<vocal>`, `<sticker>`, `<story>`, `<reel>` ou `<média>`.

### `send`

```json
{
  "username": "instagram",
  "sent": true,
  "messages": []
}
```

Avec `--history`, `messages` contient l'historique relu après l'envoi.

### `follow`

```json
{
  "username": "un_compte",
  "followed": true
}
```

### `chrome install`

```json
{
  "installed": true,
  "path": "/chemin/vers/vendor/chrome/chrome",
  "version": "Google Chrome 131.0.6778.85",
  "skipped": false
}
```

### `chrome clean`

```json
{
  "removed": ["/chemin/vers/vendor", "/chemin/vers/.chrome-profile"],
  "bytes": 123456789,
  "dryRun": false
}
```

### Erreur en mode JSON

```json
{
  "error": "message d'erreur"
}
```

Le code de sortie est alors `1`.

---

## API Python

### Ouverture d'un client

```python
import asyncio

from igscraper import BrowserOptions, Instagram


async def main():
    options = BrowserOptions(
        headless=True,
        block_media=True,
    )

    async with Instagram(options) as client:
        result = await client.login(sessionid="VOTRE_SESSIONID")

        if not result.success:
            print(f"Connexion impossible : {result.reason}")
            return

        print(await client.account("instagram"))


if __name__ == "__main__":
    asyncio.run(main())
```

`Instagram` peut aussi être démarré et fermé manuellement :

```python
client = Instagram()
await client.start()
try:
    ...
finally:
    await client.close()
```

### `BrowserOptions`

| Option | Défaut | Description |
| --- | --- | --- |
| `headless` | `True` | Lance le navigateur sans fenêtre. |
| `block_media` | `True` | Bloque images et vidéos pour accélérer les pages. |
| `locale` | `"fr-FR"` | Locale du navigateur. |
| `timezone_id` | `"Europe/Paris"` | Fuseau horaire. |
| `user_agent` | `None` | User-agent personnalisé. Sinon, un UA cohérent est calculé en headless. |
| `user_data_dir` | `None` | Répertoire du profil persistant. Défaut : `.chrome-profile`. |
| `slow_mo` | `None` | Ralentit les actions Playwright (millisecondes). |
| `extra_args` | `None` | Arguments Chrome supplémentaires. |

Toute option inconnue lève immédiatement `TypeError`.

### Méthodes principales

| Méthode | Description |
| --- | --- |
| `await client.start()` | Démarre le navigateur et prépare les services. |
| `await client.close()` | Ferme la messagerie et le navigateur. |
| `await client.login(...)` | Connexion par identifiants, `sessionid` ou profil persistant. |
| `await client.logout()` | Efface les cookies de session. |
| `await client.ensure_login()` | Vérifie la session et renvoie le `sessionid`, sinon lève `LoginRequiredError`. |
| `await client.search(query)` | Recherche des comptes. |
| `await client.account(username)` | Récupère un profil. |
| `await client.follow(username)` | S'abonne à un compte. |
| `await client.messages(username)` | Lit une conversation. |
| `await client.send_message(username, message, history=False)` | Envoie un message, avec historique optionnel. |

Alias disponibles :

```python
client.disconnect      # logout
client.get_profile     # account
client.get_messages    # messages
client.send            # send_message
```

Propriétés :

| Propriété | Description |
| --- | --- |
| `client.logged_in` | `True` si un `sessionid` est connu. |
| `client.sessionid` | `sessionid` courant, ou `None`. |
| `client.page` | Page Playwright active. Lève `BrowserError` si le client n'est pas démarré. |
| `client.context` | Contexte Playwright actif. Lève `BrowserError` si le client n'est pas démarré. |

### Connexion

```python
# Par identifiants
result = await client.login(username="mon_compte", password="mon_mot_de_passe")

# Par cookie
result = await client.login(sessionid="VOTRE_SESSIONID")

# Réutilisation exclusive du profil persistant
result = await client.login(reuse_only=True)
```

`login()` renvoie un `LoginResult` :

| Attribut | Description |
| --- | --- |
| `success` | Succès de la connexion. |
| `method` | Méthode utilisée (`password`, `cookie`, `sessionid`). |
| `sessionid` | Cookie de session obtenu. |
| `reason` | Raison de l'échec. |
| `challenge` | Challenge détecté, le cas échéant. |

`LoginResult` est évaluable directement :

```python
if await client.login(sessionid=sessionid):
    ...
```

### Session autonome (sans client persistant)

Utile pour obtenir un `sessionid` une seule fois :

```python
from igscraper import SessionOptions, establish_session_result

result = await establish_session_result(
    "mon_compte",
    "mon_mot_de_passe",
    SessionOptions(headless=False, verify=True),
)

if result and result.sessionid:
    print(result.sessionid)
```

| Helper | Résultat |
| --- | --- |
| `establish_session_result(...)` | `LoginResult` ou `None`. |
| `establish_session(...)` | `sessionid` ou `None`. |
| `get_sessionid(...)` | Alias de `establish_session`. |

`SessionOptions` accepte `headless`, `manual_timeout`, `profile_dir` et `verify`.

### Services de bas niveau

Les classes `Login`, `Search`, `Account` et `Message` sont exportées et peuvent être utilisées directement avec une page Playwright :

```python
from igscraper import Account, Login, Message, Search, first_page, stealth_browser

async with stealth_browser() as context:
    page = await first_page(context)
    login = Login(page)
    search = Search(page)
    account = Account(page)
    message = Message(page)
    ...
```

---

## Comportement et robustesse

### Furtivité

- Patchright réduit les signaux d'automatisation détectables.
- Un user-agent Chrome cohérent est généré automatiquement en mode headless.
- La locale, le fuseau horaire et la taille de fenêtre sont contrôlés.
- Le profil persistant conserve les cookies entre les exécutions.
- Les médias peuvent être bloqués ou remplacés par une image minimale.

### Connexion et challenges

- Détection des CAPTCHA, checkpoints, 2FA et activités suspectes.
- En mode `--headed`, la résolution manuelle est proposée pendant la durée `manual_timeout`.
- En mode headless, un challenge non résoluble fait échouer la connexion avec une raison explicite.

### Navigation et attentes

- Les attentes utilisent des scrutins avec backoff exponentiel plutôt que des délais fixes.
- La saisie de texte imite une frappe humaine (délais aléatoires et pauses).
- La pagination des messages est bornée pour éviter les boucles infinies.
- Les erreurs Playwright et système sont interceptées puis transformées en erreurs métier.

### Médias

Par défaut, les ressources `image` et `media` sont bloquées. `--load-media` (CLI) ou `block_media=False` (Python) les autorise, au prix d'un chargement plus lent.

---

## Structure du projet

```text
igscraper/
├── __init__.py        # API publique et version
├── __main__.py        # CLI (argparse)
├── account.py         # profils et abonnements
├── browser.py         # lancement furtif, options, blocage médias
├── chrome.py          # installation et nettoyage de Chrome
├── client.py          # façade Instagram
├── console.py         # console interactive
├── constants.py       # toutes les constantes du projet
├── errors.py          # exceptions et helpers
├── login.py           # connexion, cookies, challenges
├── message.py         # lecture et envoi de messages
├── navigation.py      # navigation, attentes, saisie clavier
├── render.py          # rendu terminal
├── scripts.py         # chargement des scripts JavaScript
├── search.py          # recherche de comptes
├── session.py         # obtention autonome d'une session
└── js/                # scripts injectés dans la page
    ├── account_overview.js
    ├── button_texts.js
    ├── profile_ready.js
    ├── profile_state.js
    ├── search_results.js
    ├── sent_state.js
    ├── text_length.js
    └── text_longer.js
```

---

## Constantes

**Toutes les valeurs de configuration sont centralisées dans `igscraper/constants.py`** :

- URLs, chemins et version ;
- options par défaut du navigateur et des sessions ;
- sélecteurs CSS et textes d'interface Instagram ;
- délais, timeouts et paramètres de polling ;
- styles et dimensions du rendu terminal ;
- niveaux de journalisation et formateur de logs ;
- constantes d'installation et d'extraction de Chrome.

Les autres modules n'en déclarent aucune : ils importent celles dont ils ont besoin depuis `constants.py`.

---

## Gestion des erreurs

Toutes les exceptions héritent de `IGScraperError` et sont disponibles dans `igscraper.errors` :

| Exception | Rôle |
| --- | --- |
| `IGScraperError` | Erreur de base. |
| `BrowserError` | Navigateur absent, lancement impossible ou client non démarré. |
| `LoginError` | Échec de connexion. |
| `ChallengeRequiredError` | Vérification de sécurité requise (CAPTCHA, 2FA). |
| `LoginRequiredError` | Une session valide est nécessaire avant l'action. |
| `ScrapeError` | Données Instagram inaccessibles ou action métier échouée. |
| `AccountNotFoundError` | Compte inexistant, supprimé ou ayant bloqué l'utilisateur connecté (sous-classe de `ScrapeError`, attribut `username`). |
| `AccountRestrictedError` | Profil restreint par Instagram, par exemple page « Profil restreint : vous devez avoir au moins 25 ans pour voir ce profil » (sous-classe de `ScrapeError`, attribut `username`). |

Comportement :

- Les méthodes de la façade `Instagram` lèvent une exception métier (`ScrapeError`, `LoginRequiredError`, `BrowserError`).
- Instagram répond HTTP 200 avec la page « Cette page n'est malheureusement pas disponible » pour un compte inexistant, supprimé ou bloqué : `account`, `follow`, `messages` et `send` détectent cette page immédiatement et lèvent `AccountNotFoundError` (sans attendre de délai), ce qui permet de l'attraper séparément :

  ```python
  try:
      profile = await client.account("un_compte")
  except AccountNotFoundError as exc:
      print(f"@{exc.username} n'existe pas")
  ```

- Un profil à restriction d'âge (page « Profil restreint », sans en-tête de profil) est détecté de la même façon et lève `AccountRestrictedError`.
- Les commandes `account`, `follow`, `messages` et `send` acceptent un nom d'utilisateur (`@nom`, `nom`) ou l'URL complète du profil (`https://www.instagram.com/nom/`).
- `login()` renvoie un `LoginResult` avec `success=False` et une `reason` en cas d'échec attendu.
- Les classes de service utilisent un garde-fou qui intercepte les erreurs Playwright/OS, journalise le détail et renvoie `None` ou `False`.
- Les messages d'erreur sont tronqués par `summarize()` pour rester lisibles.

---

## Développement

```bash
# Installer les dépendances
uv sync

# Installer Chrome
uv run igscraper chrome install

# Lint et syntaxe
make check

# Équivalents manuels
uvx ruff check igscraper
uv run python -m compileall -q igscraper
```

Configuration Ruff : ligne de 120 caractères, cible Python 3.11, nombreuses règles activées (`pyproject.toml`).

`make clean` supprime `.venv`, `vendor`, `.chrome-profile`, `uv.lock`, `dist` et les caches Python. À utiliser avec précaution : la session persistante est perdue.

---

## Limitations et responsabilité

- Instagram peut modifier son interface à tout moment : les sélecteurs CSS sont par nature fragiles.
- Les challenges de sécurité peuvent nécessiter une intervention manuelle.
- Des connexions automatisées répétées peuvent entraîner des limitations ou blocages de compte.
- L'outil ne contourne pas les permissions : il lit uniquement ce qu'un compte connecté peut voir.
- Aucune garantie de disponibilité, d'exactitude des données ou d'absence de détection.

Vous êtes responsable de l'usage de cet outil et du respect des conditions d'utilisation d'Instagram.

---

## Crédits

- **[Patchright](https://github.com/Kaliiiiiiiiii-Vinyzu/patchright)** — fork furtif de Playwright utilisé pour piloter le navigateur.
- **[Playwright for Python](https://playwright.dev/python/)** — API de navigation et d'automatisation.
- **[uv](https://github.com/astral-sh/uv)** — gestion de l'environnement et des dépendances.

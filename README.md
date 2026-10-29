# igscraper

`igscraper` est un client Python asynchrone et une interface en ligne de commande (CLI) pour interagir avec Instagram. Il est basé sur [patchright](https://github.com/kaliiiiiiiiii/patchright) pour automatiser un navigateur Chromium.

---

## Sommaire

1. [Installation](#installation)
2. [Interface en Ligne de Commande (CLI)](#interface-en-ligne-de-commande-cli)
3. [Interface Module Python](#interface-module-python)
4. [Gestion des erreurs](#gestion-des-erreurs)

---

## Installation

Le projet utilise [uv](https://github.com/astral-sh/uv).

### Prérequis
- Python >= 3.11
- `uv`

### Installation
Pour installer le projet et télécharger le navigateur Chromium :
```bash
make build
```

---

## Interface en Ligne de Commande (CLI)

Le CLI s'utilise avec la commande `igscraper` ou `python -m igscraper`.

### Options communes

- `--headed` : Affiche la fenêtre du navigateur (utile pour les challenges ou la double authentification).
- `--load-media` : Télécharge les images et vidéos (bloquées par défaut).
- `--json` : Affiche uniquement le résultat au format JSON sur la sortie standard.
- `--sessionid <COOKIE>` : Réutilise un cookie de session existant.
- `--username <USER>` : Nom d'utilisateur Instagram.
- `--password <PASS>` : Mot de passe Instagram.
- `--log-level <LEVEL>` : Niveau de log (`DEBUG`, `INFO`, `WARNING`, `ERROR`).
- `--version` : Affiche la version.

### Commandes

#### Connexion (`login`)
Permet de se connecter et d'obtenir le cookie de session.
```bash
igscraper login --username "utilisateur" --password "mot_de_passe"
```
Avec affichage du navigateur :
```bash
igscraper login --username "utilisateur" --password "mot_de_passe" --headed
```

#### Déconnexion (`logout` / `disconnect`)
Ferme et supprime la session active.
```bash
igscraper logout --sessionid "VOTRE_SESSION_ID"
```

#### Recherche (`search`)
Recherche des comptes ou des hashtags.
```bash
igscraper search "terme" --json
```

#### Profil (`account`)
Affiche les informations d'un profil.
```bash
igscraper account "utilisateur" --json
```

#### Abonnement (`follow`)
S'abonne à un compte.
```bash
igscraper follow "utilisateur" --sessionid "VOTRE_SESSION_ID"
```

#### Messages (`messages`)
Lit les messages d'une conversation.
```bash
igscraper messages "utilisateur" --sessionid "VOTRE_SESSION_ID" --last 10
```

#### Envoi de message (`send`)
Envoie un message à un utilisateur.
```bash
igscraper send "utilisateur" "Bonjour" --sessionid "VOTRE_SESSION_ID" --history
```

---

## Interface Module Python

Le module peut être intégré dans des scripts Python asynchrones.

### Exemple

```python
import asyncio
from igscraper import Instagram, BrowserOptions

async def main():
    options = BrowserOptions(
        headless=True,
        block_media=True
    )

    async with Instagram(options) as client:
        result = await client.login(sessionid="VOTRE_COOKIE_SESSIONID")

        if not result.success:
            print(f"Erreur: {result.reason}")
            return

        # Recherche
        results = await client.search("terme")
        print(results)

        # Profil
        profile = await client.account("utilisateur")
        print(profile)

        # Messages
        msgs = await client.messages("utilisateur")
        print(msgs)

        # Envoi
        await client.send_message("utilisateur", "Bonjour")

if __name__ == "__main__":
    asyncio.run(main())
```

### Méthodes principales

- `client.login(...)` : Connexion (par identifiants ou cookie sessionid).
- `client.logout()` / `client.disconnect()` : Déconnexion.
- `client.ensure_login()` : Vérifie si l'utilisateur est connecté.
- `client.search(query)` : Recherche.
- `client.account(username)` / `client.get_profile(username)` : Récupère un profil.
- `client.follow(username)` : S'abonne à un compte.
- `client.messages(username)` / `client.get_messages(username)` : Lit les messages.
- `client.send_message(username, message, history=False)` : Envoie un message.

---

## Gestion des erreurs

Les exceptions se trouvent dans `igscraper.errors` :

- `IGScraperError` : Erreur de base.
- `LoginError` : Erreur de connexion.
- `LoginRequiredError` : Connexion requise.
- `ChallengeRequiredError` : Vérification de sécurité requise (CAPTCHA / 2FA).
- `ScrapeError` : Erreur lors de la récupération des données.
- `BrowserError` : Erreur liée au navigateur.

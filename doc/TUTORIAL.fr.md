# Tutoriel : fichiers `.http` avec REST Client pour Zed

Ce tutoriel explique la syntaxe des fichiers `.http` (ou `.rest`) et comment les
exécuter depuis Zed avec le convertisseur `http2curl.py` fourni dans cette
extension.

> Le format `.http` est issu de l'extension VS Code REST Client. Il permet de
> décrire des requêtes HTTP dans un simple fichier texte, avec coloration
> syntaxique, variables, environnements et bodies JSON / XML / GraphQL.

---

## Table des matières

1. [Installation et prérequis](#1-installation-et-prérequis)
2. [Première requête](#2-première-requête)
3. [Anatomie d'une requête](#3-anatomie-dune-requête)
4. [Plusieurs requêtes dans un fichier](#4-plusieurs-requêtes-dans-un-fichier)
5. [Le corps de requête (body)](#5-le-corps-de-requête-body)
6. [Variables](#6-variables)
7. [Environnements](#7-environnements)
8. [GraphQL](#8-graphql)
9. [cURL intégré](#9-curl-intégré)
10. [Exécuter une requête depuis Zed](#10-exécuter-une-requête-depuis-zed)
11. [Astuces et raccourcis](#11-astuces-et-raccourcis)
12. [Table de référence rapide](#12-table-de-référence-rapide)

---

## 1. Installation et prérequis

### L'extension Zed

Dans Zed : `zed: install dev extension` → sélectionner le dossier `rest-zed-extension/`.
Ouvrez ensuite un fichier `.http` : la coloration syntaxique, les snippets et
l'outline s'activent.

### Le convertisseur curl

Pour **envoyer** des requêtes (Zed ne peut pas le faire nativement) :

```sh
chmod +x ./scripts/http2curl.py
ln -s "$(pwd)/rest-zed-extension/scripts/http2curl.py" ~/.local/bin/http2curl
```

Vérifiez :

```sh
echo "GET https://httpbin.org/get" | http2curl --run
```

### Les tâches Zed

Ouvrez `zed: open tasks` (`~/.config/zed/tasks.json`) et ajoutez :

```json
[
  {
    "label": "REST: envoyer la requête sous le curseur",
    "command": "http2curl --line $ZED_ROW $ZED_FILE --run",
    "use_new_terminal": false,
    "allow_concurrent_runs": true,
    "reveal": "always"
  },
  {
    "label": "REST: afficher la commande curl",
    "command": "http2curl --line $ZED_ROW $ZED_FILE",
    "use_new_terminal": false,
    "allow_concurrent_runs": true,
    "reveal": "always"
  }
]
```

`$ZED_ROW` est la ligne du curseur : `http2curl` trouve automatiquement la
requête qui contient cette ligne (entre deux séparateurs `###`). **Aucune
sélection nécessaire** — placez juste le curseur dans la requête, comme dans
VS Code.

Raccourci clavier optionnel dans `~/.config/zed/keymap.json` :

```json
[
  {
    "context": "Workspace",
    "bindings": {
      "alt-r": ["task::Spawn", { "task_name": "REST: envoyer la requête sous le curseur" }]
    }
  }
]
```

---

## 2. Première requête

Créez un fichier `test.http` :

```http
GET https://httpbin.org/get
Accept: application/json
```

Placez le curseur sur l'une de ces deux lignes → `task: spawn` → **REST: envoyer
la requête sous le curseur**. La réponse s'affiche dans le terminal.

Encore plus court : si vous omettez la méthode, `GET` est implicite.

```http
https://httpbin.org/get
```

---

## 3. Anatomie d'une requête

Une requête `.http` suit la structure du RFC 2616 :

```
MÉTHODE URL [HTTP/1.1]      ← ligne de requête
Header-Name: valeur          ← en-têtes (une par ligne)
                              ← ligne vide OBLIGATOIRE
corps de requête             ← body (optionnel)
```

Exemple complet :

```http
POST https://httpbin.org/post HTTP/1.1
Content-Type: application/json
Authorization: Bearer mon-token

{
  "nom": "alice",
  "age": 30
}
```

### La ligne de requête

- **Méthodes supportées** : `GET`, `POST`, `PUT`, `DELETE`, `PATCH`, `HEAD`,
  `OPTIONS`, `CONNECT`, `TRACE`, `LIST`, `GRAPHQL`, `WEBSOCKET`.
- Le suffixe `HTTP/1.1` est optionnel (ignoré par `http2curl`).
- Si la méthode est omise → `GET` par défaut.

### Query strings multi-lignes

Pour les URLs avec beaucoup de paramètres :

```http
GET https://api.example.com/users
    ?page=2
    &pageSize=10
    &sort=name
```

Les lignes commençant par `?` ou `&` sont concaténées avec la ligne précédente.

### En-têtes

Format `Nom: Valeur`, une par ligne, jusqu'à la ligne vide :

```http
User-Agent: rest-client
Accept-Language: fr-FR,fr;q=0.9,en;q=0.6
Content-Type: application/json
```

---

## 4. Plusieurs requêtes dans un fichier

Séparez les requêtes avec `###` (trois dièses ou plus) :

```http
### Récupérer un commentaire
GET https://example.com/comments/1

### Lister les sujets
GET https://example.com/topics/1

### Créer un commentaire
POST https://example.com/comments
Content-Type: application/json

{
  "name": "sample",
  "time": "Wed, 21 Oct 2015 18:27:50 GMT"
}
```

Vous pouvez ajouter un titre après `###` :

```http
### Connexion utilisateur
POST https://api.example.com/login
Content-Type: application/json

{"user": "alice", "password": "secret"}
```

Le titre apparaît dans l'**outline** de Zed et aide à naviguer dans un fichier
contenant beaucoup de requêtes.

### Nommer une requête (`# @name`)

```http
# @name login
POST https://api.example.com/login
Content-Type: application/json

{"user": "alice"}
```

Le nom `login` apparaît dans l'outline et peut être référencé par d'autres
requêtes (pour enchaîner : utiliser la réponse de `login` dans la suivante —
*note : le chaînage de réponses nécessite l'extension VS Code originale, non
supporté par `http2curl.py`*).

---

## 5. Le corps de requête (body)

Tout ce qui suit la **ligne vide** après les en-têtes est le corps.

### JSON

```http
POST https://api.example.com/users
Content-Type: application/json

{
  "name": "alice",
  "email": "alice@example.com",
  "roles": ["admin", "user"]
}
```

La coloration syntaxique JSON s'applique automatiquement dans Zed.

### XML

```http
POST https://api.example.com/xml
Content-Type: application/xml

<request>
  <name>sample</name>
  <time>Wed, 21 Oct 2015 18:27:50 GMT</time>
</request>
```

### Body depuis un fichier

Préfixe `<` suivi du chemin (absolu ou relatif au fichier `.http`) :

```http
POST https://api.example.com/upload
Content-Type: application/xml

< ./data/payload.xml
```

Avec substitution de variables (encodage UTF-8 par défaut) :

```http
<@ ./template.xml
```

Avec un encodage spécifique :

```http
<@latin1 ./legacy.xml
```

### Form data (`multipart/form-data`)

```http
POST https://api.example.com/upload
Content-Type: multipart/form-data; boundary=----WebAppBoundary

------WebAppBoundary
Content-Disposition: form-data; name="titre"

Mon fichier
------WebAppBoundary
Content-Disposition: form-data; name="fichier"; filename="1.png"
Content-Type: image/png

< ./1.png
------WebAppBoundary--
```

Snippet Zed : tapez `mfr` pour générer ce squelette automatiquement.

### URL-encoded

```http
POST https://api.example.com/login
Content-Type: application/x-www-form-urlencoded

name=foo
&password=bar
&remember=true
```

Chaque paire `clé=valeur` commence sur une nouvelle ligne par `&` (sauf la
première).

---

## 6. Variables

### Variables de fichier (`@variable`)

Définies en haut du fichier, substituées partout (`{{nom}}`) :

```http
@host = https://api.example.com
@token = abc123def456

### Liste des utilisateurs
GET {{host}}/users
Authorization: Bearer {{token}}

### Détail d'un utilisateur
GET {{host}}/users/42
Authorization: Bearer {{token}}
```

Les variables peuvent référencer d'autres variables :

```http
@host = https://api.example.com
@baseUrl = {{host}}/api/v1

GET {{baseUrl}}/users
```

> **Important avec `http2curl`** : si vous ne sélectionnez que la requête (sans
> les lignes `@variable`), passez `--vars-from "$ZED_FILE"` pour que les
> variables soient quand même résolues depuis le fichier complet. C'est déjà le
> cas dans les tâches Zed fournies plus haut.

### Variables de requête (`# @name`)

Le résultat d'une requête nommée peut être réutilisé dans les suivantes
*(supporté par l'extension VS Code originale ; non supporté par
`http2curl.py`)*. Syntaxe pour référence :

```http
# @name login
POST https://api.example.com/login
Content-Type: application/json

{"user": "alice", "password": "secret"}

###

GET https://api.example.com/profile
Authorization: Bearer {{login.response.body.token}}
```

### Variables système

| Variable | Description |
|----------|-------------|
| `{{$guid}}` | UUID v4 aléatoire |
| `{{$randomInt min max}}` | Entier aléatoire entre `min` et `max` |
| `{{$timestamp}}` | Timestamp Unix actuel |
| `{{$timestamp 1 day}}` | Timestamp +1 jour |
| `{{$datetime rfc1123}}` | Date au format RFC 1123 |
| `{{$datetime iso8601}}` | Date au format ISO 8601 |
| `{{$localDatetime rfc1123}}` | Date locale au format RFC 1123 |
| `{{$processEnv %HOME}}` | Variable d'environnement du système |
| `{{$dotenv MA_VARIABLE}}` | Variable depuis un fichier `.env` |

> *Note : les variables système dynamiques sont supportées par l'extension VS
> Code originale. `http2curl.py` ne les substitute pas — remplacez-les par des
> valeurs concrètes ou des `@variable`.*

### Commentaires

```http
# Ceci est un commentaire
// Celui-ci aussi
### Celui-ci est un séparateur de requête (avec titre optionnel)
```

---

## 7. Environnements

Les environnements permettent de basculer entre plusieurs configurations (dev,
staging, prod) sans modifier le fichier `.http`.

### Fichier d'environnement (`settings.json`)

Format identique à `rest-client.environmentVariables` de VS Code :

```json
{
  "$shared": {
    "version": "v1"
  },
  "dev": {
    "host": "http://localhost:3000",
    "token": "dev-token"
  },
  "prod": {
    "host": "https://api.prod.example.com",
    "token": "prod-token"
  }
}
```

- `$shared` est **toujours fusionné** quel que soit l'environnement choisi.
- L'environnement nommé (`dev`, `prod`) est fusionné par-dessus `$shared`.

### Utilisation dans le fichier `.http`

```http
GET {{host}}/api/{{version}}/users
Authorization: Bearer {{token}}
```

### Exécution avec un environnement

```sh
http2curl --env-file settings.json --env prod --vars-from test.http --run < <(sed -n '/^GET/,$p' test.http)
```

Ou via une tâche Zed dédiée :

```json
{
  "label": "REST: envoyer (prod)",
  "command": "echo \"$ZED_SELECTED_TEXT\" | http2curl --vars-from \"$ZED_FILE\" --env-file ./settings.json --env prod --run"
}
```

---

## 8. GraphQL

Ajoutez l'en-tête `X-Request-Type: GraphQL`. Le body contient la query, puis
(optionnellement) les variables séparées par une **ligne vide** :

```http
POST https://api.github.com/graphql
Content-Type: application/json
Authorization: Bearer ghp_xxx
X-Request-Type: GraphQL

query ($name: String!, $owner: String!) {
  repository(name: $name, owner: $owner) {
    name
    fullName: nameWithOwner
    description
    stargazers(first: 5) {
      totalCount
      nodes {
        login
      }
    }
  }
}

{
  "name": "vscode-restclient",
  "owner": "Huachao"
}
```

Snippet Zed : tapez `graphql` pour générer le squelette.

---

## 9. cURL intégré

Vous pouvez écrire directement une commande `curl` dans un fichier `.http` :

```http
curl -X POST https://api.example.com/users \
  -H "Content-Type: application/json" \
  -d '{"name":"alice"}'
```

La coloration syntaxique shell s'applique sur ce bloc.

---

## 10. Exécuter une requête depuis Zed

### Méthode 1 : tâche Zed (recommandée)

1. Placez le curseur dans la requête (sur la ligne `METHOD url`, un en-tête ou le body).
2. `task: spawn` (`ctrl-shift-p` → "task: spawn").
3. Choisissez **REST: envoyer la requête sous le curseur**.
4. La réponse s'affiche dans le terminal.

Avec le raccourci `ctrl-alt-r` (si configuré) : sélection + touche = envoi direct.

### Méthode 2 : terminal manuel (par numéro de ligne)

```sh
# envoyer la requête à la ligne 14 du fichier
http2curl --line 14 test.http --run
```

Ou via stdin (une requête complète sur l'entrée standard) :

```sh
echo "GET https://httpbin.org/get" | http2curl --run
```

### Méthode 3 : afficher la commande curl sans l'exécuter

Utile pour vérifier ou copier la commande :

```sh
http2curl --vars-from test.http < <(sed -n '/^POST/,$p' test.http)
```

Sortie :

```
$ curl -s -i -X POST https://api.example.com/users -H 'Content-Type: application/json' --data-raw '{
  "name": "alice"
}'
```

---

## 11. Astuces et raccourcis

### Snippets disponibles

Tapez le préfixe puis `Tab` dans un fichier `.http` :

| Préfixe | Génère |
|---------|--------|
| `get` | `GET ${1:url} HTTP/1.1` |
| `post` | `POST` avec en-tête + body |
| `put` | `PUT` avec en-tête + body |
| `delete` | `DELETE` |
| `graphql` | Requête GraphQL complète |
| `soap` | Enveloppe SOAP |
| `mfr` | `multipart/form-data` |
| `fv` | Variable de fichier `@nom = valeur` |
| `rv` | Variable de requête `# @name nom` |
| `note` | Commentaire `# @note` |

### Outline

L'outline de Zed affiche :
- Les séparateurs `###` avec leur titre
- Les lignes de requête (`METHOD url`)
- Les déclarations `@variable`

Utilisez `ctrl-shift-o` pour naviguer rapidement entre les requêtes d'un gros
fichier.

### Authentification

`http2curl` supporte les trois formats de Basic Auth de l'extension VS Code originale.
Les credentials sont **automatiquement encodés en base64** — vous n'avez pas besoin
de le faire vous-même :

```http
# Format 1 : user et password séparés par un espace (auto-encode)
GET https://httpbin.org/basic-auth/user/passwd
Authorization: Basic user passwd

# Format 2 : user:password en clair (auto-encode)
GET https://httpbin.org/basic-auth/user/passwd
Authorization: Basic user:passwd

# Format 3 : déjà encodé en base64 (inchangé)
GET https://httpbin.org/basic-auth/user/passwd
Authorization: Basic dXNlcjpwYXNzd2Q=
```

Les trois produisent la même commande :
```
curl -H 'Authorization: Basic dXNlcjpwYXNzd2Q='
```

**Avec des variables** (substituées puis encodées) :

```http
@user = alice
@pass = s3cret

GET https://api.example.com/me
Authorization: Basic {{user}} {{pass}}
```

**Digest Auth** fonctionne pareil :

```http
GET https://httpbin.org/digest-auth/auth/user/passwd
Authorization: Digest user passwd
```

**Bearer token / API key** — pas d'encodage, valeur utilisée telle quelle :

```http
GET https://api.example.com/data
Authorization: Bearer eyJhbGciOi...

GET https://api.example.com/data
X-Api-Key: ma-cle-secret
```

> AWS Signature v4, AWS Cognito et Azure AD ne sont pas supportés par
> `http2curl` — utilisez les flags `curl` correspondants ou des en-têtes
> pré-calculés.

### Partage d'écran (redaction)

L'extension configure une **redaction automatique** des en-têtes sensibles
(`Authorization`, `Cookie`, `Set-Cookie`, `X-Api-Key`, `Api-Key`,
`X-Auth-Token`) et des valeurs de variables `@variable` lors du partage d'écran
collaboratif dans Zed. Les valeurs sont masquées pour vos collaborateurs.

---

## 12. Table de référence rapide

| Élément | Syntaxe | Exemple |
|---------|---------|---------|
| Requête GET | `GET url` | `GET https://api.example.com/users` |
| Requête POST | `POST url` + headers + body | voir §3 |
| En-tête | `Nom: Valeur` | `Content-Type: application/json` |
| Body | après ligne vide | `{ "key": "value" }` |
| Body depuis fichier | `< chemin` | `< ./data.json` |
| Séparateur | `###` | `### Créer un utilisateur` |
| Nom de requête | `# @name nom` | `# @name login` |
| Variable fichier | `@nom = valeur` | `@host = https://api.example.com` |
| Référence variable | `{{nom}}` | `{{host}}/users` |
| Commentaire | `#` ou `//` | `# ceci est un commentaire` |
| Query multi-ligne | lignes `?`/`&` | voir §3 |
| GraphQL | `X-Request-Type: GraphQL` | voir §8 |
| cURL intégré | ligne `curl ...` | voir §9 |
| Multipart | `boundary=...` | snippet `mfr` |

### Ce qui fonctionne dans Zed vs VS Code

| Fonctionnalité | Zed (cette extension) | VS Code (original) |
|----------------|:---------------------:|:------------------:|
| Coloration syntaxique | ✅ | ✅ |
| Snippets | ✅ | ✅ |
| Outline / navigation | ✅ | ✅ |
| Injections JSON/XML/GraphQL | ✅ | ✅ |
| Envoi de requêtes | ⚠ via `http2curl` + tâches | ✅ natif |
| Panneau de réponse | ❌ (terminal) | ✅ webview |
| Variables `@variable` / `{{}}` | ✅ (`http2curl`) | ✅ |
| Variables système `{{$timestamp}}` | ❌ | ✅ |
| Environnements | ✅ (`--env-file`) | ✅ |
| Cookies persistants | ❌ | ✅ |
| Historique de requêtes | ❌ | ✅ |
| Auth AWS / Azure AD / Digest | ❌ | ✅ |
| Génération de snippets de code | ❌ | ✅ |
| Import Swagger | ❌ | ✅ |
| CodeLens "Send Request" | ❌ | ✅ |
| Redaction collaboration | ✅ | ❌ |

---

## Pour aller plus loin

- [Documentation originale VS Code](https://github.com/Huachao/vscode-restclient#usage)
- [Grammar tree-sitter-http](https://github.com/rest-nvim/tree-sitter-http)
- [Documentation extensions Zed](https://zed.dev/docs/extensions)

Bon test d'API ! 🚀

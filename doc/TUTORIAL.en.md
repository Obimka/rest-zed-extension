# Tutorial: `.http` files with REST Client for Zed

This tutorial explains the syntax of `.http` (or `.rest`) files and how to
execute them from Zed using the `http2curl.py` converter bundled with this
extension.

> The `.http` format comes from the VS Code REST Client extension. It lets you
> describe HTTP requests in a simple text file, with syntax highlighting,
> variables, environments, and JSON / XML / GraphQL bodies.

---

## Table of Contents

1. [Installation and prerequisites](#1-installation-and-prerequisites)
2. [First request](#2-first-request)
3. [Anatomy of a request](#3-anatomy-of-a-request)
4. [Multiple requests in one file](#4-multiple-requests-in-one-file)
5. [Request body](#5-request-body)
6. [Variables](#6-variables)
7. [Environments](#7-environments)
8. [GraphQL](#8-graphql)
9. [Inline cURL](#9-inline-curl)
10. [Running a request from Zed](#10-running-a-request-from-zed)
11. [Tips and shortcuts](#11-tips-and-shortcuts)
12. [Quick reference table](#12-quick-reference-table)

---

## 1. Installation and prerequisites

### The Zed extension

In Zed: `zed: install dev extension` → select the `zed-extension/` folder.
Then open a `.http` file: syntax highlighting, snippets, and
the outline are activated.

### The curl converter

To **send** requests (Zed cannot do this natively):

```sh
chmod +x zed-extension/scripts/http2curl.py
ln -s "$(pwd)/zed-extension/scripts/http2curl.py" ~/.local/bin/http2curl
```

Verify:

```sh
echo "GET https://httpbin.org/get" | http2curl --run
```

### Zed tasks

Open `zed: open tasks` (`~/.config/zed/tasks.json`) and add:

```json
[
  {
    "label": "REST: send request under cursor",
    "command": "http2curl --line $ZED_ROW $ZED_FILE --run",
    "use_new_terminal": false,
    "allow_concurrent_runs": true,
    "reveal": "always"
  },
  {
    "label": "REST: show curl command",
    "command": "http2curl --line $ZED_ROW $ZED_FILE",
    "use_new_terminal": false,
    "allow_concurrent_runs": true,
    "reveal": "always"
  }
]
```

`$ZED_ROW` is the cursor line: `http2curl` automatically finds the
request that contains this line (between two `###` separators). **No
selection needed** — just place the cursor inside the request, like in
VS Code.

Optional keyboard shortcut in `~/.config/zed/keymap.json`:

```json
[
  {
    "context": "Workspace",
    "bindings": {
      "alt-r": ["task::Spawn", { "task_name": "REST: send request under cursor" }]
    }
  }
]
```

---

## 2. First request

Create a `test.http` file:

```http
GET https://httpbin.org/get
Accept: application/json
```

Place the cursor on either line → `task: spawn` → **REST: send request
under cursor**. The response appears in the terminal.

Even shorter: if you omit the method, `GET` is implied.

```http
https://httpbin.org/get
```

---

## 3. Anatomy of a request

A `.http` request follows the RFC 2616 structure:

```
METHOD URL [HTTP/1.1]      ← request line
Header-Name: value          ← headers (one per line)
                              ← BLANK LINE (required)
request body                ← body (optional)
```

Complete example:

```http
POST https://httpbin.org/post HTTP/1.1
Content-Type: application/json
Authorization: Bearer my-token

{
  "name": "alice",
  "age": 30
}
```

### The request line

- **Supported methods**: `GET`, `POST`, `PUT`, `DELETE`, `PATCH`, `HEAD`,
  `OPTIONS`, `CONNECT`, `TRACE`, `LIST`, `GRAPHQL`, `WEBSOCKET`.
- The `HTTP/1.1` suffix is optional (ignored by `http2curl`).
- If the method is omitted → `GET` by default.

### Multi-line query strings

For URLs with many parameters:

```http
GET https://api.example.com/users
    ?page=2
    &pageSize=10
    &sort=name
```

Lines starting with `?` or `&` are concatenated with the previous line.

### Headers

Format `Name: Value`, one per line, up to the blank line:

```http
User-Agent: rest-client
Accept-Language: en-US,en;q=0.9,fr;q=0.6
Content-Type: application/json
```

---

## 4. Multiple requests in one file

Separate requests with `###` (three hashes or more):

```http
### Fetch a comment
GET https://example.com/comments/1

### List topics
GET https://example.com/topics/1

### Create a comment
POST https://example.com/comments
Content-Type: application/json

{
  "name": "sample",
  "time": "Wed, 21 Oct 2015 18:27:50 GMT"
}
```

You can add a title after `###`:

```http
### User login
POST https://api.example.com/login
Content-Type: application/json

{"user": "alice", "password": "secret"}
```

The title appears in Zed's **outline** and helps navigate a file
with many requests.

### Naming a request (`# @name`)

```http
# @name login
POST https://api.example.com/login
Content-Type: application/json

{"user": "alice"}
```

The name `login` appears in the outline and can be referenced by other
requests (for chaining: use the response from `login` in the next request —
*note: response chaining requires the original VS Code extension, not
supported by `http2curl.py`*).

---

## 5. Request body

Everything following the **blank line** after headers is the body.

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

JSON syntax highlighting applies automatically in Zed.

### XML

```http
POST https://api.example.com/xml
Content-Type: application/xml

<request>
  <name>sample</name>
  <time>Wed, 21 Oct 2015 18:27:50 GMT</time>
</request>
```

### Body from file

Prefix `<` followed by the path (absolute or relative to the `.http` file):

```http
POST https://api.example.com/upload
Content-Type: application/xml

< ./data/payload.xml
```

With variable substitution (UTF-8 encoding by default):

```http
<@ ./template.xml
```

With a specific encoding:

```http
<@latin1 ./legacy.xml
```

### Form data (`multipart/form-data`)

```http
POST https://api.example.com/upload
Content-Type: multipart/form-data; boundary=----WebAppBoundary

------WebAppBoundary
Content-Disposition: form-data; name="title"

My file
------WebAppBoundary
Content-Disposition: form-data; name="file"; filename="1.png"
Content-Type: image/png

< ./1.png
------WebAppBoundary--
```

Zed snippet: type `mfr` to generate this skeleton automatically.

### URL-encoded

```http
POST https://api.example.com/login
Content-Type: application/x-www-form-urlencoded

name=foo
&password=bar
&remember=true
```

Each `key=value` pair starts on a new line with `&` (except the first).

---

## 6. Variables

### File variables (`@variable`)

Defined at the top of the file, substituted everywhere (`{{name}}`):

```http
@host = https://api.example.com
@token = abc123def456

### List users
GET {{host}}/users
Authorization: Bearer {{token}}

### User details
GET {{host}}/users/42
Authorization: Bearer {{token}}
```

Variables can reference other variables:

```http
@host = https://api.example.com
@baseUrl = {{host}}/api/v1

GET {{baseUrl}}/users
```

> **Important with `http2curl`**: if you only select the request (without
> the `@variable` lines), pass `--vars-from "$ZED_FILE"` so that
> variables are resolved from the full file anyway. This is already
> the case in the Zed tasks provided above.

### Request variables (`# @name`)

The result of a named request can be reused in subsequent requests
*(supported by the original VS Code extension; not supported by
`http2curl.py`)*. Syntax for reference:

```http
# @name login
POST https://api.example.com/login
Content-Type: application/json

{"user": "alice", "password": "secret"}

###

GET https://api.example.com/profile
Authorization: Bearer {{login.response.body.token}}
```

### System variables

| Variable | Description |
|----------|-------------|
| `{{$guid}}` | Random UUID v4 |
| `{{$randomInt min max}}` | Random integer between `min` and `max` |
| `{{$timestamp}}` | Current Unix timestamp |
| `{{$timestamp 1 day}}` | Timestamp +1 day |
| `{{$datetime rfc1123}}` | RFC 1123 formatted date |
| `{{$datetime iso8601}}` | ISO 8601 formatted date |
| `{{$localDatetime rfc1123}}` | Local date in RFC 1123 format |
| `{{$processEnv %HOME}}` | System environment variable |
| `{{$dotenv MY_VARIABLE}}` | Variable from a `.env` file |

> *Note: dynamic system variables are supported by the original VS Code
> extension. `http2curl.py` does not substitute them — replace them with
> concrete values or `@variable`.*

### Comments

```http
# This is a comment
// This one too
### This is a request separator (with optional title)
```

---

## 7. Environments

Environments let you switch between multiple configurations (dev,
staging, prod) without modifying the `.http` file.

### Environment file (`settings.json`)

Same format as `rest-client.environmentVariables` from VS Code:

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

- `$shared` is **always merged** regardless of the chosen environment.
- The named environment (`dev`, `prod`) is merged on top of `$shared`.

### Usage in the `.http` file

```http
GET {{host}}/api/{{version}}/users
Authorization: Bearer {{token}}
```

### Running with an environment

```sh
http2curl --env-file settings.json --env prod --vars-from test.http --run < <(sed -n '/^GET/,$p' test.http)
```

Or via a dedicated Zed task:

```json
{
  "label": "REST: send (prod)",
  "command": "echo \"$ZED_SELECTED_TEXT\" | http2curl --vars-from \"$ZED_FILE\" --env-file ./settings.json --env prod --run"
}
```

---

## 8. GraphQL

Add the `X-Request-Type: GraphQL` header. The body contains the query, then
(optionally) the variables separated by a **blank line**:

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

Zed snippet: type `graphql` to generate the skeleton.

---

## 9. Inline cURL

You can write a `curl` command directly in a `.http` file:

```http
curl -X POST https://api.example.com/users \
  -H "Content-Type: application/json" \
  -d '{"name":"alice"}'
```

Shell syntax highlighting applies to this block.

---

## 10. Running a request from Zed

### Method 1: Zed task (recommended)

1. Place the cursor in the request (on the `METHOD url` line, a header, or the body).
2. `task: spawn` (`ctrl-shift-p` → "task: spawn").
3. Choose **REST: send request under cursor**.
4. The response appears in the terminal.

With the `ctrl-alt-r` shortcut (if configured): cursor + key = direct send.

### Method 2: manual terminal (by line number)

```sh
# send the request at line 14 of the file
http2curl --line 14 test.http --run
```

Or via stdin (a complete request on standard input):

```sh
echo "GET https://httpbin.org/get" | http2curl --run
```

### Method 3: display the curl command without running it

Useful to verify or copy the command:

```sh
http2curl --vars-from test.http < <(sed -n '/^POST/,$p' test.http)
```

Output:

```
$ curl -s -i -X POST https://api.example.com/users -H 'Content-Type: application/json' --data-raw '{
  "name": "alice"
}'
```

---

## 11. Tips and shortcuts

### Available snippets

Type the prefix then `Tab` in a `.http` file:

| Prefix | Generates |
|--------|-----------|
| `get` | `GET ${1:url} HTTP/1.1` |
| `post` | `POST` with header + body |
| `put` | `PUT` with header + body |
| `delete` | `DELETE` |
| `graphql` | Complete GraphQL request |
| `soap` | SOAP envelope |
| `mfr` | `multipart/form-data` |
| `fv` | File variable `@name = value` |
| `rv` | Request variable `# @name name` |
| `note` | Comment `# @note` |

### Outline

Zed's outline displays:
- `###` separators with their title
- Request lines (`METHOD url`)
- `@variable` declarations

Use `ctrl-shift-o` to quickly navigate between requests in a large
file.

### Authentication

`http2curl` supports the three Basic Auth formats of the original VS Code extension.
Credentials are **automatically base64-encoded** — you don't need
to do it yourself:

```http
# Format 1: user and password separated by a space (auto-encode)
GET https://httpbin.org/basic-auth/user/passwd
Authorization: Basic user passwd

# Format 2: user:password in plain text (auto-encode)
GET https://httpbin.org/basic-auth/user/passwd
Authorization: Basic user:passwd

# Format 3: already base64-encoded (passed through)
GET https://httpbin.org/basic-auth/user/passwd
Authorization: Basic dXNlcjpwYXNzd2Q=
```

All three produce the same command:
```
curl -H 'Authorization: Basic dXNlcjpwYXNzd2Q='
```

**With variables** (substituted then encoded):

```http
@user = alice
@pass = s3cret

GET https://api.example.com/me
Authorization: Basic {{user}} {{pass}}
```

**Digest Auth** works the same way:

```http
GET https://httpbin.org/digest-auth/auth/user/passwd
Authorization: Digest user passwd
```

**Bearer token / API key** — no encoding, value used as-is:

```http
GET https://api.example.com/data
Authorization: Bearer eyJhbGciOi...

GET https://api.example.com/data
X-Api-Key: my-secret-key
```

> AWS Signature v4, AWS Cognito and Azure AD are not supported by
> `http2curl` — use the corresponding `curl` flags or pre-computed
> headers.

### Screen share (redaction)

The extension configures **automatic redaction** of sensitive headers
(`Authorization`, `Cookie`, `Set-Cookie`, `X-Api-Key`, `Api-Key`,
`X-Auth-Token`) and `@variable` values during collaborative screen
sharing in Zed. Values are masked for your collaborators.

---

## 12. Quick reference table

| Element | Syntax | Example |
|---------|--------|---------|
| GET request | `GET url` | `GET https://api.example.com/users` |
| POST request | `POST url` + headers + body | see §3 |
| Header | `Name: Value` | `Content-Type: application/json` |
| Body | after blank line | `{ "key": "value" }` |
| Body from file | `< path` | `< ./data.json` |
| Separator | `###` | `### Create a user` |
| Request name | `# @name name` | `# @name login` |
| File variable | `@name = value` | `@host = https://api.example.com` |
| Variable reference | `{{name}}` | `{{host}}/users` |
| Comment | `#` or `//` | `# this is a comment` |
| Multi-line query | `?`/`&` lines | see §3 |
| GraphQL | `X-Request-Type: GraphQL` | see §8 |
| Inline cURL | `curl ...` line | see §9 |
| Multipart | `boundary=...` | snippet `mfr` |

### What works in Zed vs VS Code

| Feature | Zed (this extension) | VS Code (original) |
|---------|:--------------------:|:------------------:|
| Syntax highlighting | ✅ | ✅ |
| Snippets | ✅ | ✅ |
| Outline / navigation | ✅ | ✅ |
| JSON/XML/GraphQL injections | ✅ | ✅ |
| Request sending | ⚠ via `http2curl` + tasks | ✅ native |
| Response panel | ❌ (terminal) | ✅ webview |
| Variables `@variable` / `{{}}` | ✅ (`http2curl`) | ✅ |
| System variables `{{$timestamp}}` | ❌ | ✅ |
| Environments | ✅ (`--env-file`) | ✅ |
| Persistent cookies | ❌ | ✅ |
| Request history | ❌ | ✅ |
| Auth AWS / Azure AD / Digest | ❌ | ✅ |
| Code snippet generation | ❌ | ✅ |
| Swagger import | ❌ | ✅ |
| CodeLens "Send Request" | ❌ | ✅ |
| Collaboration redaction | ✅ | ❌ |

---

## Going further

- [Original VS Code documentation](https://github.com/Huachao/vscode-restclient#usage)
- [tree-sitter-http grammar](https://github.com/rest-nvim/tree-sitter-http)
- [Zed extensions documentation](https://zed.dev/docs/extensions)

Happy API testing!

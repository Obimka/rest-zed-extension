# REST Client for Zed
Extension for [Zed](https://zed.dev) editor, providing language support for HTTP request files (`.http` / `.rest`).

## 

- **Syntax highlighting** for `.http` and `.rest` files via the
  [`rest-nvim/tree-sitter-http`](https://github.com/rest-nvim/tree-sitter-http) grammar.
- **Code injections**: JSON / XML / GraphQL bodies and `< {% ... %} >` JavaScript pre-request &
  response-handler scripts are highlighted with their own language.
- **Outline**: request lines (`###` separators, `# @name` request variables, `@variable`
  declarations) appear in the outline panel.
- **Snippets**: `get`, `post`, `put`, `delete`, `graphql`, `soap`, `mfr` (multipart), `fv` (file
  variable), `rv` (request variable), `note`.
- **Bracket matching & auto-indentation** for request bodies.
- **Screen-share redaction**: `Authorization`, `Cookie`, `Api-Key`, and similar header values, plus
  variable declarations, are redacted while collaborating.

## Sending requests with `curl`

Since the extension itself can't execute requests, pair it with `curl` via **Zed Tasks** and the
bundled `scripts/http2curl.py` converter. The converter parses `.http` syntax (variables, headers,
JSON/XML bodies, `###` separators) and emits/runs a `curl` command.

### Setup


In Zed: `zed: install dev extension` → select the `rest-zed-extension/` folder.
Then open a `.http` file: syntax highlighting, snippets, and
the outline are activated.


1. Install the converter somewhere on your `PATH` (or note its absolute path):
   ```sh
   chmod +x zed-extension/scripts/http2curl.py
   # e.g. symlink it:
   ln -s "$(pwd)/zed-extension/scripts/http2curl.py" ~/.local/bin/http2curl
   ```

2. Add tasks to your **global** Zed tasks file (`~/.config/zed/tasks.json` or open it via
   `zed: open tasks`):
   ```json
   [
     {
       "label": "REST: send request at cursor",
       "command": "http2curl --line $ZED_ROW $ZED_FILE --run",
       "use_new_terminal": false,
       "allow_concurrent_runs": true,
       "reveal": "always"
     },
     {
       "label": "REST: show curl for request at cursor",
       "command": "http2curl --line $ZED_ROW $ZED_FILE",
       "use_new_terminal": false,
       "allow_concurrent_runs": true,
       "reveal": "always"
     }
   ]
   ```
   Place your cursor anywhere inside a request block and run the task — no selection needed.
   `$ZED_ROW` tells `http2curl` which request to send based on cursor position, and variables
   (`@variable`, `{{name}}`, request chaining) are always resolved from the full file.

3. (Optional) Bind a keybinding in `~/.config/zed/keymap.json`:
   ```json
   [
     {
       "context": "Workspace",
       "bindings": {
         "ctrl-alt-r": ["task::Spawn", { "task_name": "REST: send request at cursor" }]
       }
     }
   ]
   ```

### Usage

Place your cursor inside a request block in your `.http` file (no selection needed),
then run `task: spawn` → **REST: send request at cursor**. The response prints in the
terminal. Named requests (`# @name login`) cache their response so subsequent requests
can reference it via `{{login.response.body.access_token}}`.

### Environment files

To use VS Code-style `rest-client.environmentVariables` JSON files, pass `--env-file` and `--env`:
```json
{
  "label": "REST: send (prod)",
  "command": "http2curl --line $ZED_ROW $ZED_FILE --env-file ./settings.json --env prod --run"
}
```
The env file format is `{"$shared": {...}, "prod": {...}}`; `$shared` is always merged, then the
named environment on top.

### Supported syntax

| Syntax | Supported |
|--------|-----------|
| `GET/POST/... url` | yes |
| `Header: value` | yes |
| `@variable = value` + `{{variable}}` | yes |
| JSON / XML / raw body | yes |
| `< ./body.json` (body from file) | yes |
| `###` request separators | yes |
| `# @name` / comments | parsed (name ignored) |
| `{% %}` pre-request scripts | **no** (skipped) |
| OAuth / Azure AD / AWS Sigv4 auth | **no** (use `curl`'s own auth flags or add headers manually) |

## Install (dev extension)

1. `cd zed-extension`
2. In Zed, run `zed: install dev extension` and select this directory.
3. Open any `.http` file.

## Publish

Follow the [Zed extension publishing guide](https://zed.dev/docs/extensions/developing-extensions):
add this directory as a submodule under `extensions/rest-client` in
`zed-industries/extensions` and open a PR.

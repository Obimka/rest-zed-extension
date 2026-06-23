#!/usr/bin/env python3
"""Convert a VS Code REST Client .http request block into a curl command and run it.

Reads the selected text from stdin (or a file arg), parses one request, prints the
curl command, and executes it if --run is passed.

Syntax handled:
    ### separator (ignored)
    # @name request_name       (names the request; response is cached for chaining)
    # @note / # comment        (ignored)
    @variable = value          (substituted into {{variable}})
    @variable = {{req.response.body.field}}  (file variable from cached response)
    METHOD url [HTTP/1.1]
    Header-Name: value
    < ./file                   (body from file)
    {% ... %}                  (ignored - pre-request scripts not supported)

    <body line>

Request chaining:
    # @name login
    POST /auth ...

    ###

    GET /profile
    Authorization: Bearer {{login.response.body.access_token}}

Responses are cached in ~/.cache/http2curl/responses.json so they persist
across separate invocations (e.g. when selecting requests one at a time in Zed).
"""
import json, os, re, shlex, subprocess, sys
from base64 import b64encode

# --- ANSI colors (disabled if stdout is not a TTY) ---

_USE_COLOR = sys.stdout.isatty()

class C:
    RESET   = "\033[0m"   if _USE_COLOR else ""
    BOLD    = "\033[1m"   if _USE_COLOR else ""
    DIM     = "\033[2m"   if _USE_COLOR else ""
    GREEN   = "\033[32m"  if _USE_COLOR else ""
    RED     = "\033[31m"  if _USE_COLOR else ""
    YELLOW  = "\033[33m"  if _USE_COLOR else ""
    CYAN    = "\033[36m"  if _USE_COLOR else ""
    MAGENTA = "\033[35m"  if _USE_COLOR else ""
    BLUE    = "\033[34m"  if _USE_COLOR else ""

def colorize_response(raw):
    """Add ANSI colors to a raw HTTP response: status line, headers, and body (JSON/XML)."""
    # Split headers / body (try \r\n\r\n first, then \n\n)
    sep = "\r\n\r\n"
    if sep not in raw:
        sep = "\n\n"
    if sep not in raw:
        return raw
    header_block, body = raw.split(sep, 1)
    header_lines = header_block.splitlines()
    out = []
    for i, line in enumerate(header_lines):
        if i == 0 and line.startswith("HTTP/"):
            m = re.match(r"(HTTP/\S+)\s+(\d+)(.*)", line)
            if m:
                status = int(m.group(2))
                color = C.GREEN if status < 300 else C.YELLOW if status < 400 else C.RED if status < 500 else C.RED
                out.append(f"{C.BOLD}{m.group(1)} {color}{m.group(2)}{C.RESET}{C.BOLD}{m.group(3)}{C.RESET}")
                continue
        if ":" in line:
            k, _, v = line.partition(":")
            out.append(f"{C.CYAN}{k}{C.RESET}:{C.DIM}{v}{C.RESET}")
        else:
            out.append(line)
    out.append("")
    colored_body = colorize_body(body.strip())
    return "\n".join(out) + "\n" + colored_body

def colorize_body(body):
    if not body:
        return body
    content_type = ""
    # Try to detect from last header block — but body is already split out,
    # so we sniff the content: JSON starts with { or [, XML with <
    stripped = body.lstrip()
    if stripped.startswith("{") or stripped.startswith("["):
        return colorize_json(body)
    if stripped.startswith("<"):
        return colorize_xml(body)
    return body

_JSON_TOKEN = re.compile(
    r'(?P<key>"(?:[^"\\]|\\.)*"(?:\s*:))'
    r'|(?P<string>"(?:[^"\\]|\\.)*")'
    r'|(?P<number>-?\d+\.?\d*(?:[eE][+-]?\d+)?)'
    r'|(?P<bool>true|false|null)'
    r'|(?P<punct>[{}\[\]:,])'
    r'|(?P<ws>\s+)'
)

def _json_highlight(text):
    out = []
    for m in _JSON_TOKEN.finditer(text):
        g = m.groupdict()
        if g["key"]:
            s = g["key"]
            trailing = ""
            stripped = s.rstrip()
            if stripped.endswith(":"):
                trailing = s[len(stripped):]
                s = stripped[:-1]
            out.append(f'{C.MAGENTA}{s}{C.RESET}{C.DIM}:{C.RESET}{trailing}')
        elif g["string"]:
            out.append(f'{C.GREEN}{g["string"]}{C.RESET}')
        elif g["number"]:
            out.append(f'{C.YELLOW}{g["number"]}{C.RESET}')
        elif g["bool"]:
            out.append(f'{C.CYAN}{g["bool"]}{C.RESET}')
        elif g["punct"]:
            out.append(f'{C.DIM}{g["punct"]}{C.RESET}')
        else:
            out.append(m.group(0))
    return "".join(out)

def colorize_json(text):
    try:
        data = json.loads(text)
        text = json.dumps(data, indent=2, ensure_ascii=False)
    except (json.JSONDecodeError, ValueError):
        return text
    return _json_highlight(text)

_XML_TAG    = re.compile(r'(<[/]?)([\w:.-]+)')
_XML_TAG_END= re.compile(r'(/?>)')
_XML_ATTR   = re.compile(r'([\w:.-]+)=("[^"]*")')

def colorize_xml(text):
    text = _XML_TAG.sub(lambda m: f'{C.BLUE}{m.group(1)}{C.MAGENTA}{m.group(2)}{C.RESET}', text)
    text = _XML_TAG_END.sub(lambda m: f'{C.BLUE}{m.group(1)}{C.RESET}', text)
    text = _XML_ATTR.sub(lambda m: f'{C.CYAN}{m.group(1)}{C.RESET}={C.GREEN}{m.group(2)}{C.RESET}', text)
    return text

VARS = {}
ENV_NAME = None
CACHE_DIR = os.path.expanduser("~/.cache/http2curl")
CACHE_FILE = os.path.join(CACHE_DIR, "responses.json")
RESPONSES = {}

# --- response cache ---

def load_cache():
    global RESPONSES
    try:
        with open(CACHE_FILE) as f:
            RESPONSES = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        RESPONSES = {}

def save_cache():
    os.makedirs(CACHE_DIR, exist_ok=True)
    with open(CACHE_FILE, "w") as f:
        json.dump(RESPONSES, f, indent=2)

def cache_response(name, raw_response):
    """Parse a raw HTTP response and cache it under the request name."""
    parts = raw_response.split("\r\n\r\n", 1)
    if len(parts) < 2:
        # No headers/body split — maybe \n\n or just body
        parts = raw_response.split("\n\n", 1)
    header_block = parts[0] if len(parts) > 1 else ""
    body = parts[1] if len(parts) > 1 else raw_response
    headers = {}
    status = 0
    for line in header_block.splitlines():
        if line.startswith("HTTP/"):
            m = re.match(r"HTTP/\S+\s+(\d+)", line)
            if m:
                status = int(m.group(1))
        elif ":" in line:
            k, _, v = line.partition(":")
            headers[k.strip().lower()] = v.strip()
    body_json = None
    try:
        body_json = json.loads(body)
    except (json.JSONDecodeError, ValueError):
        pass
    RESPONSES[name] = {
        "status": status,
        "headers": headers,
        "body": body,
        "body_json": body_json,
    }
    save_cache()

# --- variable substitution ---

REQ_VAR_RE = re.compile(r"\{\{\s*(\w+)\.response\.(body|header)\.([^}]+)\s*\}\}")

def resolve_req_var(match):
    """Resolve {{name.response.body.field.sub}} or {{name.response.header.Name}}."""
    req_name, part, path = match.group(1), match.group(2), match.group(3)
    if req_name not in RESPONSES:
        return match.group(0)
    resp = RESPONSES[req_name]
    if part == "header":
        return resp["headers"].get(path.strip().lower(), match.group(0))
    # body: navigate dot-path through body_json if available
    if resp["body_json"] is not None:
        val = resp["body_json"]
        for key in path.split("."):
            if isinstance(val, dict) and key in val:
                val = val[key]
            elif isinstance(val, list) and key.isdigit() and int(key) < len(val):
                val = val[int(key)]
            else:
                return match.group(0)
        return str(val)
    return match.group(0)

def subst(s):
    if s is None:
        return s
    # First resolve request variables {{name.response.body.field}}
    s = REQ_VAR_RE.sub(resolve_req_var, s)
    # Then resolve file/environment variables {{variable}}
    for k, v in VARS.items():
        s = s.replace("{{" + k + "}}", v).replace("{{ " + k + " }}", v)
    return s

# --- auth ---

def encode_basic_auth(val):
    """Auto-encode Basic/Digest Auth credentials (VS Code style).

    "Basic user passwd"      -> "Basic dXNlcjpwYXNzd2Q="  (space-separated)
    "Basic user:passwd"      -> "Basic dXNlcjpwYXNzd2Q="  (colon-separated, raw)
    "Basic dXNlcjpwYXNzd2Q=" -> kept as-is               (already base64)
    """
    val = subst(val)
    m = re.match(r'^(Basic|Digest)\s+(.+)$', val)
    if not m:
        return val
    scheme, creds = m.group(1), m.group(2).strip()
    if ":" not in creds and " " not in creds and re.match(r'^[A-Za-z0-9+/]+=*$', creds):
        return f"{scheme} {creds}"
    if " " in creds:
        parts = creds.split(None, 1)
        creds = f"{parts[0]}:{parts[1]}" if len(parts) > 1 else parts[0]
    encoded = b64encode(creds.encode()).decode()
    return f"{scheme} {encoded}"

# --- request extraction by cursor line ---

def extract_request_at_line(full_text, target_line):
    """Return the text of the request block containing the given 1-based line number.

    Blocks are delimited by `###` separators. The block containing target_line
    (including any leading `# @name` and `@variable` lines above it, up to the
    previous `###` or start of file) is returned.
    """
    lines = full_text.splitlines()
    if target_line < 1 or target_line > len(lines):
        return None
    idx = target_line - 1  # 0-based
    # Find block boundaries: previous separator (exclusive) and next separator (exclusive)
    start = 0
    for j in range(idx, -1, -1):
        if lines[j].lstrip().startswith("###"):
            start = j + 1
            break
    else:
        start = 0
    end = len(lines)
    for j in range(idx + 1, len(lines)):
        if lines[j].lstrip().startswith("###"):
            end = j
            break
    block = "\n".join(lines[start:end]).strip()
    # Prepend any @variable definitions from earlier in the file so they resolve
    prefix_lines = []
    for j in range(0, start):
        l = lines[j].strip()
        if re.match(r"^@[\w-]+\s*=", l):
            prefix_lines.append(l)
    if prefix_lines:
        block = "\n".join(prefix_lines) + "\n" + block
    return block

# --- parsing ---

def parse(text):
    lines = text.splitlines()
    i = 0
    req_name = None
    method = url = None
    headers = []
    body_lines = []
    in_body = False
    while i < len(lines):
        raw = lines[i]
        line = raw.strip()
        i += 1
        if not line:
            if in_body:
                body_lines.append("")
            elif method is not None:
                in_body = True
            continue
        if line.startswith("###"):
            if method:
                break
            continue
        if line.startswith("#") or line.startswith("//"):
            m = re.match(r'^#\s*@name\s+(\w+)', line)
            if m:
                req_name = m.group(1)
            continue
        m = re.match(r"^@([\w-]+)\s*=\s*(.+)$", line)
        if m:
            continue
        if line.startswith("< ") and (method is not None):
            path = line[2:].strip()
            with open(os.path.expanduser(path)) as f:
                body_lines.append(f.read())
            in_body = True
            continue
        if method is None and re.match(r"^[A-Z]+\s+", line):
            parts = line.split()
            method = parts[0]
            url = parts[1]
            continue
        if method is not None and ":" in line and not in_body:
            name, _, val = line.partition(":")
            headers.append((name.strip(), val.strip()))
            continue
        if method is not None:
            in_body = True
            body_lines.append(raw)
    return req_name, method, url, headers, "\n".join(body_lines).strip()

def to_curl(method, url, headers, body):
    cmd = ["curl", "-s", "-i", "-k", "-X", method, subst(url)]
    for name, val in headers:
        if name.lower() == "authorization":
            val = encode_basic_auth(val)
        else:
            val = subst(val)
        cmd += ["-H", f"{name}: {val}"]
    if body:
        cmd += ["--data-raw", subst(body)]
    return cmd

def collect_vars(text):
    for line in text.splitlines():
        m = re.match(r"^@([\w-]+)\s*=\s*(.+)$", line.strip())
        if m:
            raw = m.group(2).strip()
            VARS[m.group(1)] = raw

def resolve_file_vars_from_responses():
    """Resolve file variables that reference request variables, e.g.
    @authToken = {{login.response.body.access_token}}"""
    changed = True
    while changed:
        changed = False
        for k, v in list(VARS.items()):
            new_v = subst(v)
            if new_v != v:
                VARS[k] = new_v
                changed = True

def load_env_file(path):
    with open(path) as f:
        data = json.load(f)
    env = {}
    env.update(data.get("$shared", {}))
    if ENV_NAME and ENV_NAME in data:
        env.update(data[ENV_NAME])
    for k, v in env.items():
        VARS[k] = str(v)

# --- main ---

def main():
    global ENV_NAME
    if "--help" in sys.argv or "-h" in sys.argv:
        print(__doc__)
        print("Usage: http2curl [--run] [--line N FILE] [--vars-from FILE] [--env-file FILE] [--env NAME] [REQUEST_FILE]")
        print("  --line N FILE  send the request containing line N of FILE (cursor-based, no selection needed)")
        print("  Reads the request from stdin if no REQUEST_FILE is given.")
        return
    run = "--run" in sys.argv
    env_file = None
    file_for_vars = None
    target_line = None
    args = []
    i = 1
    while i < len(sys.argv):
        a = sys.argv[i]
        if a == "--run":
            run = True
        elif a == "--env-file" and i + 1 < len(sys.argv):
            env_file = sys.argv[i + 1]; i += 1
        elif a == "--env" and i + 1 < len(sys.argv):
            ENV_NAME = sys.argv[i + 1]; i += 1
        elif a == "--vars-from" and i + 1 < len(sys.argv):
            file_for_vars = sys.argv[i + 1]; i += 1
        elif a == "--line" and i + 1 < len(sys.argv):
            target_line = int(sys.argv[i + 1]); i += 1
        else:
            args.append(a)
        i += 1
    load_cache()
    # Determine the request text: --line extracts from the file, otherwise stdin/file
    if target_line is not None:
        if not args:
            print("--line requires a file argument", file=sys.stderr)
            sys.exit(1)
        file_path = args[0]
        full_text = open(file_path).read()
        text = extract_request_at_line(full_text, target_line)
        if not text:
            print(f"No request found at line {target_line}", file=sys.stderr)
            sys.exit(1)
        # variables always come from the full file
        collect_vars(full_text)
    elif args:
        text = open(args[0]).read()
        if file_for_vars:
            collect_vars(open(file_for_vars).read())
        else:
            collect_vars(text)
    else:
        text = sys.stdin.read()
        if file_for_vars:
            collect_vars(open(file_for_vars).read())
        else:
            collect_vars(text)
    if env_file:
        load_env_file(env_file)
    # Resolve file variables that reference request responses (e.g. @authToken = {{login.response.body.token}})
    resolve_file_vars_from_responses()
    req_name, method, url, headers, body = parse(text)
    if not method:
        print("No request found in input", file=sys.stderr)
        sys.exit(1)
    cmd = to_curl(method, url, headers, body)
    print("$ " + " ".join(shlex.quote(c) for c in cmd))
    if run:
        result = subprocess.run(cmd, capture_output=True, text=True)
        raw = result.stdout
        print(colorize_response(raw))
        if req_name:
            cache_response(req_name, raw)
            print(f"\n[response cached as '{req_name}']", file=sys.stderr)

if __name__ == "__main__":
    main()

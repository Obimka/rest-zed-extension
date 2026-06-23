; Redact sensitive header values when screen-sharing
(header
  name: (_) @_name
  (#any-of? @_name "Authorization" "Proxy-Authorization" "Cookie" "Set-Cookie" "X-Api-Key" "Api-Key" "X-Auth-Token")
  value: (_) @redact) @redact

; Redact variable values (may contain tokens/secrets)
(variable_declaration
  value: (_) @redact) @redact

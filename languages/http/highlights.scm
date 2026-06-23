; Methods
(method) @keyword

; Headers
(header
  name: (_) @property)

(header
  value: (_) @string)

(header
  ":" @punctuation.delimiter)

; HTTP version
(http_version) @constant.builtin

; URL
(request
  url: (_) @string.special.url)

; Variables
(variable_declaration
  name: (identifier) @variable)

(variable_declaration
  "=" @operator)

(variable) @variable

; Request name / variable comments
(comment
  "@" @keyword
  name: (_) @label)

(comment
  "=" @operator)

; Response
(status_code) @number
(status_text) @string

; Request separator (### title)
(request_separator
  value: (_) @title)

; External body file path
(external_body
  path: (_) @string.special.path)

(external_body
  "<" @operator)

(external_body
  name: (_) @constant)

; Punctuation
[
  "{{"
  "}}"
] @punctuation.bracket

[
  "{%"
  "%}"
] @punctuation.bracket

; Comments
[
  (comment)
  (request_separator)
] @comment

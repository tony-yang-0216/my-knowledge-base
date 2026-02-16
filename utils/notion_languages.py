# Notion API 支援的 code block 語言
NOTION_LANGUAGES = {
    "abap", "abc", "agda", "arduino", "ascii art", "assembly", "bash", "basic",
    "bnf", "c", "c#", "c++", "clojure", "coffeescript", "coq", "css", "dart",
    "dhall", "diff", "docker", "ebnf", "elixir", "elm", "erlang", "f#", "flow",
    "fortran", "gherkin", "glsl", "go", "graphql", "groovy", "haskell", "hcl",
    "html", "idris", "java", "javascript", "json", "julia", "kotlin", "latex",
    "less", "lisp", "livescript", "llvm ir", "lua", "makefile", "markdown",
    "markup", "matlab", "mathematica", "mermaid", "nix", "notion formula",
    "objective-c", "ocaml", "pascal", "perl", "php", "plain text", "powershell",
    "prolog", "protobuf", "purescript", "python", "r", "racket", "reason",
    "ruby", "rust", "sass", "scala", "scheme", "scss", "shell", "smalltalk",
    "solidity", "sql", "swift", "toml", "typescript", "vb.net", "verilog",
    "vhdl", "visual basic", "webassembly", "xml", "yaml", "java/c/c++/c#",
}

# 常見 markdown 語言別名 → Notion 語言
LANG_ALIASES = {
    "text": "plain text", "txt": "plain text", "plaintext": "plain text",
    "sh": "bash", "zsh": "bash",
    "js": "javascript", "jsx": "javascript",
    "ts": "typescript", "tsx": "typescript",
    "py": "python", "python3": "python",
    "rb": "ruby",
    "rs": "rust",
    "yml": "yaml",
    "dockerfile": "docker",
    "objc": "objective-c", "obj-c": "objective-c",
    "cs": "c#", "csharp": "c#",
    "cpp": "c++",
    "fs": "f#", "fsharp": "f#",
    "hs": "haskell",
    "kt": "kotlin",
    "md": "markdown",
    "tex": "latex",
    "ps1": "powershell",
    "asm": "assembly",
    "gql": "graphql",
    "proto": "protobuf",
    "sol": "solidity",
    "wasm": "webassembly",
    "vb": "visual basic",
    "jsonc": "json",
}


def normalize_notion_language(lang: str) -> str:
    """將 markdown info string 轉換為 Notion 支援的語言名稱"""
    lang = lang.strip().lower()
    if lang in NOTION_LANGUAGES:
        return lang
    if lang in LANG_ALIASES:
        return LANG_ALIASES[lang]
    return "plain text"

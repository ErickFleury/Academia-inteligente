"""Keep retrieval mechanics out of client replies without weakening validation."""

import re


def exposes_retrieval(message):
    return bool(
        re.search(
            r"\b(trechos?|referências?|referencias?|citaç(?:ão|ões)|citac(?:ao|oes)|"
            r"fontes?|vetori[sz]\w*|RAG|grounding|citation_ids)\b|"
            r"\b(segundo|conforme|de acordo com)\s+(o|a|os|as)\s+(guia|manual|livro|literatura)",
            message,
            re.I,
        )
    )


def client_message(message):
    if not exposes_retrieval(message):
        return message
    # Never strip an attribution and publish the remaining prescription as if
    # it had been validated. This is a conservative fallback for prompt failures.
    return (
        "Não consigo confirmar essa orientação com segurança. "
        "Peça ao instrutor para revisar esse ajuste antes de prosseguir."
    )

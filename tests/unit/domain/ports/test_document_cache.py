import ast
import inspect
from abc import ABC
from pathlib import Path
from typing import Any

import pytest

from app.domain.ports.cache import DocumentCache

CONTRACT_METHODS = ("get", "set", "acquire_lock", "release_lock")
CONTRACT_SIGNATURES = [
    ("get", (("checksum", str),), str | None),
    ("set", (("checksum", str), ("value", str), ("ttl", int)), None),
    ("acquire_lock", (("checksum", str), ("ttl", int)), bool),
    ("release_lock", (("checksum", str),), None),
]
ALLOWED_STDLIB_IMPORTS = {"abc", "typing"}
ALLOWED_DOMAIN_IMPORTS: set[str] = set()
FORBIDDEN_IMPLEMENTATION_TOKENS = (
    "redis",
    "motor",
    "pymongo",
    "fastapi",
    "uvicorn",
    "starlette",
    "pickle",
    "serialize",
    "client",
    "driver",
)


def _contract_method(method_name: str) -> Any:
    return getattr(DocumentCache, method_name)


def _port_source() -> str:
    module = inspect.getmodule(DocumentCache)
    assert module is not None
    assert module.__file__ is not None
    return Path(module.__file__).read_text(encoding="utf-8")


def test_document_cache_inherits_from_abc() -> None:
    assert issubclass(DocumentCache, ABC)


def test_document_cache_is_abstract() -> None:
    assert DocumentCache.__abstractmethods__


def test_document_cache_cannot_be_instantiated() -> None:
    with pytest.raises(TypeError):
        DocumentCache()


@pytest.mark.parametrize("method_name", CONTRACT_METHODS)
def test_contract_methods_are_abstract(method_name: str) -> None:
    assert _contract_method(method_name).__isabstractmethod__ is True


@pytest.mark.parametrize("method_name", CONTRACT_METHODS)
def test_contract_methods_are_async(method_name: str) -> None:
    assert inspect.iscoroutinefunction(_contract_method(method_name))


def test_abstract_methods_are_exactly_the_requested_contract() -> None:
    assert set(DocumentCache.__abstractmethods__) == set(CONTRACT_METHODS)


def test_contract_exposes_exactly_the_requested_operations() -> None:
    public_methods = {
        method_name
        for method_name, _ in inspect.getmembers(DocumentCache, inspect.isfunction)
        if not method_name.startswith("_")
    }
    assert public_methods == set(CONTRACT_METHODS)


@pytest.mark.parametrize(
    ("method_name", "parameters_spec", "return_type"),
    CONTRACT_SIGNATURES,
)
def test_contract_signatures_match_specification(
    method_name: str, parameters_spec: Any, return_type: Any
) -> None:
    signature = inspect.signature(_contract_method(method_name))
    parameters = list(signature.parameters.values())

    expected_names = ["self", *(name for name, _ in parameters_spec)]
    expected_annotations = [annotation for _, annotation in parameters_spec]

    assert [parameter.name for parameter in parameters] == expected_names
    assert [parameter.annotation for parameter in parameters[1:]] == expected_annotations
    assert all(parameter.default is inspect.Parameter.empty for parameter in parameters)
    assert signature.return_annotation == return_type


def test_port_module_declares_no_infrastructure_dependencies() -> None:
    tree = ast.parse(_port_source())

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name.split(".")[0] in ALLOWED_STDLIB_IMPORTS
        elif isinstance(node, ast.ImportFrom):
            assert node.module is not None
            if node.module.startswith("app."):
                assert node.module in ALLOWED_DOMAIN_IMPORTS
            else:
                assert node.module.split(".")[0] in ALLOWED_STDLIB_IMPORTS


def test_contract_source_expresses_no_implementation_details() -> None:
    source = _port_source().lower()

    for token in FORBIDDEN_IMPLEMENTATION_TOKENS:
        assert token not in source


def test_port_lives_in_the_domain_layer() -> None:
    assert DocumentCache.__module__ == "app.domain.ports.cache"

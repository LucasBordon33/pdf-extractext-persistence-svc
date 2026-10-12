import ast
import inspect
from abc import ABC
from pathlib import Path
from typing import Any

import pytest

from app.domain.models import PDFDocument
from app.domain.ports.repository import DocumentRepository

CONTRACT_METHODS = ("save", "find_by_checksum", "find_by_id", "delete")
ALLOWED_STDLIB_IMPORTS = {"abc", "typing"}
ALLOWED_DOMAIN_IMPORTS = {"app.domain.models"}


def _contract_method(method_name: str) -> Any:
    return getattr(DocumentRepository, method_name)


def test_document_repository_inherits_from_abc() -> None:
    assert issubclass(DocumentRepository, ABC)


def test_document_repository_is_abstract() -> None:
    assert DocumentRepository.__abstractmethods__


def test_document_repository_cannot_be_instantiated() -> None:
    with pytest.raises(TypeError):
        DocumentRepository()


@pytest.mark.parametrize("method_name", CONTRACT_METHODS)
def test_contract_methods_are_abstract(method_name: str) -> None:
    assert _contract_method(method_name).__isabstractmethod__ is True


@pytest.mark.parametrize("method_name", CONTRACT_METHODS)
def test_contract_methods_are_async(method_name: str) -> None:
    assert inspect.iscoroutinefunction(_contract_method(method_name))


def test_abstract_methods_are_exactly_the_requested_contract() -> None:
    assert set(DocumentRepository.__abstractmethods__) == set(CONTRACT_METHODS)


def test_contract_exposes_exactly_the_requested_operations() -> None:
    public_methods = {
        method_name
        for method_name, _ in inspect.getmembers(DocumentRepository, inspect.isfunction)
        if not method_name.startswith("_")
    }
    assert public_methods == set(CONTRACT_METHODS)


@pytest.mark.parametrize(
    ("method_name", "parameter_name", "parameter_type", "return_type"),
    [
        ("save", "doc", PDFDocument, str),
        ("find_by_checksum", "checksum", str, PDFDocument | None),
        ("find_by_id", "doc_id", str, PDFDocument | None),
        ("delete", "doc_id", str, bool),
    ],
)
def test_contract_signatures_match_specification(
    method_name: str, parameter_name: str, parameter_type: Any, return_type: Any
) -> None:
    signature = inspect.signature(_contract_method(method_name))
    parameters = list(signature.parameters.values())

    assert len(parameters) == 2
    assert parameters[0].name == "self"
    assert parameters[1].name == parameter_name
    assert parameters[1].annotation == parameter_type
    assert parameters[1].default is inspect.Parameter.empty
    assert signature.return_annotation == return_type


def test_port_module_declares_no_infrastructure_dependencies() -> None:
    module = inspect.getmodule(DocumentRepository)
    assert module is not None
    assert module.__file__ is not None

    tree = ast.parse(Path(module.__file__).read_text(encoding="utf-8"))

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


def test_port_lives_in_the_domain_layer() -> None:
    assert DocumentRepository.__module__ == "app.domain.ports.repository"

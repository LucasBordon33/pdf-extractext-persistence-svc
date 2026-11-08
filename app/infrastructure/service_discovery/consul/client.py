import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from ..models import ServiceInstance
from ..settings import ServiceDiscoverySettings


class ConsulError(RuntimeError):
    """Fallo de comunicación con el agente de Consul."""


class ConsulAgentClient:
    def __init__(self, settings: ServiceDiscoverySettings) -> None:
        parsed = urllib.parse.urlparse(settings.consul_base_url)

        if parsed.scheme not in {"http", "https"}:
            raise ValueError(
                "Consul base URL must use HTTP or HTTPS"
            )

        self._base_url = settings.consul_base_url.rstrip("/")
        self._timeout = settings.consul_timeout

    def register(self, payload: dict[str, Any]) -> None:
        self._request("PUT", "/v1/agent/service/register", payload)

    def deregister(self, service_id: str) -> None:
        path = (
            f"/v1/agent/service/deregister/"
            f"{urllib.parse.quote(service_id, safe='')}"
        )
        self._request("PUT", path)

    def healthy_instances(self, service_name: str) -> tuple[ServiceInstance, ...]:
        path = (
            f"/v1/health/service/"
            f"{urllib.parse.quote(service_name, safe='')}?passing=true"
        )

        entries = self._request("GET", path) or []

        return tuple(
            ServiceInstance(
                id=entry["Service"]["ID"],
                name=entry["Service"]["Service"],
                host=entry["Service"].get("Address")
                or entry["Node"]["Address"],
                port=int(entry["Service"]["Port"]),
            )
            for entry in entries
        )

    def _request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
    ) -> Any:
        body = None
        headers: dict[str, str] = {}

        if payload is not None:
            body = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"

        request = urllib.request.Request(
            f"{self._base_url}{path}",
            data=body,
            headers=headers,
            method=method,
        )

        try:
            # nosemgrep: python.lang.security.audit.dynamic-urllib-use-detected
            with urllib.request.urlopen(
                request,
                timeout=self._timeout,
            ) as response:
                raw = response.read()

        except urllib.error.HTTPError as exc:
            raise ConsulError(
                f"Consul respondió {exc.code} para {method} {path}"
            ) from exc

        except OSError as exc:
            raise ConsulError(
                f"Consul inalcanzable en {self._base_url}: {exc}"
            ) from exc

        if not raw:
            return None

        try:
            return json.loads(raw)

        except json.JSONDecodeError as exc:
            raise ConsulError(
                f"Respuesta inválida de Consul para {method} {path}"
            ) from exc
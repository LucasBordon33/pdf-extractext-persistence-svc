# Estrategia de pruebas de rendimiento (K6 + Vegeta)

Suite de pruebas de carga, estrés y spike para `pdf-extractext-persistence-svc`.

## 1. Análisis del servicio

Endpoints bajo prueba (prefijo `/api/v1`):

| Endpoint | Uso | Camino interno |
|---|---|---|
| `POST /store` | Escritura idempotente | Redis lock (SET NX EX) → Mongo find → insert → cache set → unlock (5 RTT de red) |
| `GET /documents/checksum/{checksum}` | Consulta principal (read-through) | Redis get → (miss) Mongo find → repoblar cache |
| `GET /documents/{doc_id}` | Consulta por id | Mongo find |
| `GET /documents` | Listado | Mongo find completo (sin paginar) |
| `DELETE /documents/{doc_id}` | Baja | Mongo find + delete |
| `GET /health` | Probes | Mongo ping (opcional) |

Cuellos de botella identificados:

1. **Camino de escritura**: 5 RTT secuenciales (Redis×3 + Mongo×2) por cada store — la latencia p95 la domina la cadena de idempotencia, no el insert.
2. **Contención por checksum**: stores concurrentes del mismo checksum se serializan por el lock o reciben 409 — un flujo que repite el mismo checksum mide exactamente ese techo.
3. **Listado sin paginar** (`GET /documents`): crece con la colección; excluido de los escenarios de alta tasa por diseño (riesgo de autodosificación) — se prueba solo como sonda.
4. **Texto de tamaño variable**: el contenido extraído puede alcanzar MBs; cada escenario parametriza `textBytes` para explorar el costo de inserción/lectura.
5. **Wiring actual no crea el índice único** (`main.py` usa el constructor en vez de `MongoDocumentRepository.create`): la idempotencia descansa solo en el lock. Los escenarios de conflicto vigilan esta debilidad: si el lock expira bajo carga, aparecen 201 donde deberían verse 409.

## 2. Supuestos explícitos (ajustar con SLOs reales cuando existan)

| Supuesto | Valor usado | Riesgo si es incorrecto |
|---|---|---|
| SLO de lectura (cache hit) | p95 < 100 ms | Umbrales demasiado laxos/estrictos; ajustar en `config/env.js` |
| SLO de escritura | p95 < 150 ms | Ídem |
| Sin autenticación | La plataforma (Traefik/mesh) la resuelve fuera del servicio | Si se agrega auth, inyectar header en `lib/documents.js` |
| Entorno de pruebas aislado | staging/compose, jamás producción | Contaminación de datos y DOS accidental |
| Datos sintéticos | checksums únicos `k6-<runId>-<vu>-<iter>` | No reproduce distribución real de colisiones |

## 3. Matriz de escenarios K6 (`perf/k6/scenarios/`)

| Archivo | Objetivo | Executor | Tasa | Duración | Por qué |
|---|---|---|---|---|---|
| `read_steady.js` | Rendimiento nominal del camino de lectura (cache hit) | constant-arrival-rate | 30 rps | 5 m | 30 rps modela tráfico sostenido típico del orquestador; arrival-rate desacopla tasa de latencia; 5 m alcanza estado estable (cache caliente, conexiones reutilizadas) |
| `store_sustained.js` | Carga sostenida del ciclo completo de escritura (store → fetch → delete, autolimpieza) | constant-arrival-rate | 10 ciclos/s (30 req/s) | 10 m | 10 min expone deriva de latencia/consumo bajo inserts continuos; el ciclo deja la BD estable |
| `stress_ramp.js` | Límite operativo: hallar el codo (80% lectura / 20% escritura) | ramping-arrival-rate | 50 → 200 → 400 → 50 rps | 8 m | Rampa por etapas para localizar el punto de quiebre; etapa final mide recuperación |
| `spike.js` | Burst súbito 15× sobre baseline de lectura | ramping-arrival-rate | 20 → 300 → 20 rps | 4.5 m | 30 s de pico simula un lote de PDFs procesado en paralelo; 2 m posteriores verifican drenaje de colas y normalización de p99 |

Criterio de asignación de VUs: `preAllocatedVUs` ≈ 2× tasa esperada (latencia sub-segundo), `maxVUs` ≈ 3× para absorber picos de latencia sin que el propio k6 se vuelva el cuello.

## 4. División de trabajo K6 vs Vegeta

- **K6**: flujos dinámicos (checksums únicos por iteración, read-your-write, autolimpieza), umbrales integrados (exit code ≠ 0 si fallan) y tags de baja cardinalidad (`name: store`, `fetch_checksum`, …) para métricas por operación.
- **Vegeta**: perfilado de tasa fija y cuerpo estático. Su limitación (sin templating) se convierte en ventaja para dos escenarios: `store_conflict` (body fijo → martilleo idempotente del mismo checksum: espera ≥95% de 409 con p99 acotado) y `health`/`fetch_hit` (soak a tasa constante).

Escenarios Vegeta (`perf/vegeta/targets/`): `health.json` (probe barato a 200 rps), `fetch_hit.json` (siembra el documento vía curl antes de atacar y lo borra al final), `store_conflict.json` (conflicto idempotente).

## 5. Umbrales y criterios de aceptación

| Escenario | Éxito | Fallo |
|---|---|---|
| read_steady | p95 < 100 ms, errores < 1% | Cualquier threshold excedido (k6 exit ≠ 0) |
| store_sustained | p95 store < 150 ms, p95 fetch < 100 ms, p95 delete < 150 ms, errores < 1%, checks > 99% | Ídem |
| stress_ramp | p95 < 300 ms (lectura) / < 400 ms (store), errores < 5%, checks > 90% | Colapso antes de 400 rps = límite operativo documentado |
| spike | p95 < 500 ms global, errores < 5% durante el pico | p99 sin normalizar en la ventana de recuperación |
| vegeta standard (health/fetch) | success ≥ 99%, p99 < 250 ms | `report.sh` exit 1 |
| vegeta conflict | 409 ≥ 95% y p99 < 250 ms | Ídem |

## 6. Comandos

```bash
# Local contra docker-compose (red pdf-extractext, host persistence.localhost)
docker compose up -d
export BASE_URL="https://persistence.localhost"   # o http://127.0.0.1:8003 según exposición

# K6
k6 run perf/k6/scenarios/read_steady.js
K6_TEXT_BYTES=8192 k6 run perf/k6/scenarios/store_sustained.js
k6 run perf/k6/scenarios/stress_ramp.js
k6 run perf/k6/scenarios/spike.js

# Vegeta (requiere vegeta y jq)
bash perf/vegeta/attack.sh health       RATE=200 DURATION=120s
bash perf/vegeta/attack.sh fetch_hit    RATE=100 DURATION=60s
bash perf/vegeta/attack.sh store_conflict RATE=50 DURATION=300s
bash perf/vegeta/report.sh perf/vegeta/results/health_200rps_120s.bin
bash perf/vegeta/report.sh perf/vegeta/results/store_conflict_50rps_300s.bin conflict
```

`perf/vegeta/results/` es salida local: no commitear (agregar a `.gitignore`).

## 7. Métricas clave a monitorear (lado servicio, durante las corridas)

- **API**: `http_req_duration` (p95/p99) y `http_req_failed` por tag; `store_duplicate_responses` (contador custom: 409 inesperados en checksums únicos = indicador de bug de idempotencia).
- **Proceso**: CPU y memoria del contenedor (compose limita a 256m — vigilar OOM bajo stress), event-loop lag de uvicorn.
- **MongoDB**: connections, opcounters (insert/query/delete), tickets de ejecución, latencia del servidor.
- **Redis**: ops/s, keys con TTL, rejected connections, latencia de comandos.
- **Contención**: reloj del lock (`lock:<checksum>` keys vivas) y ratio 409 en el escenario conflict.

## 8. Riesgos y mitigaciones

| Riesgo | Mitigación |
|---|---|
| Correr contra producción | Gate humano + BASE_URL explícito; documentar entornos permitidos |
| Crecimiento de la BD en store_sustained | Ciclo con DELETE por iteración (autolimpieza) + teardown |
| List endpoint autodosifica | Excluido de altas tasas; solo sonda manual |
| Índice único ausente en el wiring (hallazgo del security review) | `store_conflict` actúa como detector: 201 inesperados tras el primer request = bypass de idempotencia |
| Cardinalidad de métricas k6 | Tags `name` fijos por operación, nunca el checksum dinámico |
| Umbrales inventados | Sección 2: supuestos explícitos, ajustar con SLOs reales |
| k6/vegeta no instalados en CI | Documentar instalación en el job; no ejecutar per-PR (ver 9) |

## 9. Integración CI/CD (recomendación, no activada por YAGNI)

- **No ejecutar en cada PR**: ruido y coste sin valor (el gate de seguridad sigue en `security.yml`).
- **Nightly en staging** con `workflow_dispatch` + schedule: levantar compose con perfil de staging, correr `read_steady` + `store_sustained` (cortos: 2-3 min), publicar resumen y fallar el job si los thresholds fallan.
- Criterio para activarlo: existencia del entorno de staging estable y SLOs acordados. Hasta entonces, ejecución manual documentada (sección 6).

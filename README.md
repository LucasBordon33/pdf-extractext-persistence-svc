# pdf-persistence-service

Microservicio **stateful** en **Python (FastAPI)** responsable de la capa de persistencia: almacena y recupera los JSON con metadatos de PDFs (nombre, checksum, contenido, tamaño, etc.). Usa **MongoDB** como fuente de verdad y **Redis** como caché + idempotencia de escrituras.

Ver `ISSUES.md` para el backlog de desarrollo.
export const BASE_URL = __ENV.BASE_URL || "https://localhost:443";
// Traefik expone el servicio por HTTPS (websecure, puerto 443) con certificado
// posiblemente autofirmado. Forzar omitir verificación TLS con:
//   K6_INSECURE_SKIP_TLS_VERIFY=true k6 run <scenario>.js
export const API_V1 = `${BASE_URL}/api/v1`;

export function serviceThresholds({ durationP95, failedRate, tags = {}, checksRate }) {
    const thresholds = {
        http_req_duration: [`p(95)<${durationP95}`],
        http_req_failed: [`rate<${failedRate}`],
    };
    for (const [tag, limits] of Object.entries(tags)) {
        thresholds[`http_req_duration{name:${tag}}`] = [`p(95)<${limits.p95}`];
        thresholds[`http_req_failed{name:${tag}}`] = [`rate<${limits.rate}`];
    }
    if (checksRate !== undefined) {
        thresholds.checks = [`rate>${checksRate}`];
    }
    return thresholds;
}

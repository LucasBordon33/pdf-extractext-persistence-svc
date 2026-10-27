export const BASE_URL = __ENV.BASE_URL || "http://127.0.0.1:8003";
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

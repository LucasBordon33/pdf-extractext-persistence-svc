import { serviceThresholds } from "../config/env.js";
import { makeDocument, storeDocument, fetchByChecksum, deleteById } from "../lib/documents.js";

export const options = {
    scenarios: {
        baseline_with_spike: {
            executor: "ramping-arrival-rate",
            startRate: 20,
            timeUnit: "1s",
            stages: [
                { target: 20, duration: "2m" },
                { target: 300, duration: "30s" },
                { target: 20, duration: "2m" },
            ],
            preAllocatedVUs: 40,
            maxVUs: 150,
        },
    },
    thresholds: serviceThresholds({
        durationP95: 500,
        failedRate: 0.05,
        tags: { fetch_checksum: { p95: 500, rate: 0.05 } },
        checksRate: 0.9,
    }),
};

export function setup() {
    const payload = makeDocument({ textBytes: 512 });
    const stored = storeDocument(payload);
    if (stored.status !== 201) {
        throw new Error(`setup: no se pudo sembrar el documento (status ${stored.status})`);
    }
    return { checksum: payload.checksum, id: stored.json("id") };
}

export default function (data) {
    fetchByChecksum(data.checksum);
}

export function teardown(data) {
    deleteById(data.id);
}

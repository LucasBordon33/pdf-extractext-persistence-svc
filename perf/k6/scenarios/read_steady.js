import { check } from "k6";
import { serviceThresholds } from "../config/env.js";
import { makeDocument, storeDocument, fetchByChecksum, deleteById } from "../lib/documents.js";

export const options = {
    scenarios: {
        steady_reads: {
            executor: "constant-arrival-rate",
            rate: 30,
            timeUnit: "1s",
            duration: "5m",
            preAllocatedVUs: 20,
            maxVUs: 50,
        },
    },
    thresholds: serviceThresholds({
        durationP95: 100,
        failedRate: 0.01,
        tags: { fetch_checksum: { p95: 100, rate: 0.01 } },
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
    const response = fetchByChecksum(data.checksum);
    check(response, {
        "documento sembrado coincide": (r) => r.json("checksum") === data.checksum,
    });
}

export function teardown(data) {
    deleteById(data.id);
}

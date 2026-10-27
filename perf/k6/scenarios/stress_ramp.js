import { serviceThresholds } from "../config/env.js";
import { makeDocument, storeDocument, fetchByChecksum, deleteById } from "../lib/documents.js";

export const options = {
    scenarios: {
        ramp_to_break: {
            executor: "ramping-arrival-rate",
            startRate: 50,
            timeUnit: "1s",
            stages: [
                { target: 50, duration: "2m" },
                { target: 200, duration: "2m" },
                { target: 400, duration: "3m" },
                { target: 50, duration: "1m" },
            ],
            preAllocatedVUs: 60,
            maxVUs: 150,
        },
    },
    thresholds: serviceThresholds({
        durationP95: 300,
        failedRate: 0.05,
        tags: {
            fetch_checksum: { p95: 300, rate: 0.05 },
            store: { p95: 400, rate: 0.05 },
        },
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
    if (Math.random() < 0.8) {
        fetchByChecksum(data.checksum);
        return;
    }
    const payload = makeDocument({ textBytes: 2048 });
    const stored = storeDocument(payload);
    if (stored.status === 201) {
        deleteById(stored.json("id"));
    }
}

export function teardown(data) {
    deleteById(data.id);
}

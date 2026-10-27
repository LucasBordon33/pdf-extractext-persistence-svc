import { serviceThresholds } from "../config/env.js";
import { makeDocument, storeDocument, fetchByChecksum, deleteById } from "../lib/documents.js";

const TEXT_BYTES = Number(__ENV.K6_TEXT_BYTES || 512);

export const options = {
    scenarios: {
        sustained_writes: {
            executor: "constant-arrival-rate",
            rate: 10,
            timeUnit: "1s",
            duration: "10m",
            preAllocatedVUs: 15,
            maxVUs: 40,
        },
    },
    thresholds: serviceThresholds({
        durationP95: 150,
        failedRate: 0.01,
        tags: {
            store: { p95: 150, rate: 0.01 },
            fetch_checksum: { p95: 100, rate: 0.01 },
            delete: { p95: 150, rate: 0.01 },
        },
        checksRate: 0.99,
    }),
};

export default function () {
    const payload = makeDocument({ textBytes: TEXT_BYTES });
    const stored = storeDocument(payload);
    if (stored.status !== 201) {
        return;
    }
    const id = stored.json("id");
    fetchByChecksum(payload.checksum);
    deleteById(id);
}

package org.framemedialab.media;

import java.time.Instant;
import java.util.UUID;

/** A fresh launch cannot inherit measurement fields from a previous private export. */
final class LaunchRecord {
    final String id = UUID.randomUUID().toString();
    private final String timestamp = Instant.now().toString();
    String initialJson() {
        // Both interpolated values are generated identifiers with JSON-safe characters.
        return "{\"schema_version\":1,\"synthetic\":false,\"complete\":false,\"state\":\"IDLE\","
            + "\"launch_id\":\"" + id + "\",\"timestamp\":\"" + timestamp + "\"}";
    }
}

package org.framemedialab.media;

import java.net.URI;
import java.net.URISyntaxException;
import java.util.Locale;

/** Validates the supported source kinds without retaining or reporting identifying URI parts. */
final class SourcePolicy {
    private SourcePolicy() { }
    static String kind(String source) {
        if (source != null && source.startsWith("/")) return "file";
        if (source == null || source.isEmpty()) throw new IllegalArgumentException("Source required");
        try {
            URI uri = new URI(source);
            String scheme = uri.getScheme();
            if (scheme == null) throw new IllegalArgumentException("Absolute path or supported URI required");
            scheme = scheme.toLowerCase(Locale.ROOT);
            if (scheme.equals("http") || scheme.equals("https")) {
                if (uri.getHost() == null) throw new IllegalArgumentException("Network source requires a host");
                return scheme;
            }
            if (scheme.equals("content") && uri.getAuthority() != null) return scheme;
            if (scheme.equals("file") && uri.getPath() != null && uri.getPath().startsWith("/")) return scheme;
            throw new IllegalArgumentException("Unsupported source kind");
        } catch (URISyntaxException e) { throw new IllegalArgumentException("Malformed source URI"); }
    }
}

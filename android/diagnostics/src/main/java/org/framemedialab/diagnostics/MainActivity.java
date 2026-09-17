package org.framemedialab.diagnostics;

import android.app.Activity;
import android.content.Intent;
import android.media.MediaCodecInfo;
import android.media.MediaCodecList;
import android.media.MediaDrm;
import android.media.NotProvisionedException;
import android.media.ResourceBusyException;
import android.media.UnsupportedSchemeException;
import android.os.Build;
import android.os.Bundle;
import android.util.AtomicFile;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import org.json.JSONArray;
import org.json.JSONObject;
import java.io.File;
import java.io.FileOutputStream;
import java.io.OutputStream;
import java.nio.charset.StandardCharsets;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Locale;
import java.util.TimeZone;
import java.util.UUID;

/** Public API inventory. No network permission, credentials, provisioning or license flow. */
public final class MainActivity extends Activity {
    private TextView output;
    private Button probe;
    private volatile String exported = "{}";
    private static final String[] SAFE_PROPERTIES = {"vendor", "version", "description", "algorithms", "securityLevel"};

    static void put(JSONObject object, String key, Object value) {
        try { object.put(key, value == null ? JSONObject.NULL : value); }
        catch (org.json.JSONException e) { throw new IllegalStateException(e); }
    }
    static String timestamp() {
        SimpleDateFormat date = new SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss.SSS'Z'", Locale.US);
        date.setTimeZone(TimeZone.getTimeZone("UTC"));
        return date.format(new Date());
    }
    static String error(Exception e) {
        // Exception messages can contain vendor data. Export only the exception class.
        return e.getClass().getSimpleName();
    }
    @Override public void onCreate(Bundle saved) {
        super.onCreate(saved);
        LinearLayout column = new LinearLayout(this); column.setOrientation(LinearLayout.VERTICAL); column.setPadding(24,24,24,24);
        probe = new Button(this); probe.setText("Run DRM + codec probe"); column.addView(probe);
        Button save = new Button(this); save.setText("Export JSON…"); column.addView(save);
        output = new TextView(this); output.setTextIsSelectable(true);
        ScrollView scroll = new ScrollView(this); scroll.addView(output); column.addView(scroll);
        setContentView(column);
        probe.setOnClickListener(v -> runProbe());
        save.setOnClickListener(v -> {
            Intent intent = new Intent(Intent.ACTION_CREATE_DOCUMENT).setType("application/json").addCategory(Intent.CATEGORY_OPENABLE)
                .putExtra(Intent.EXTRA_TITLE, "diagnostics.json");
            try { startActivityForResult(intent, 1); }
            catch (Exception e) { output.setText("File picker unavailable; use ADB run-as export.\n" + exported); }
        });
        runProbe();
    }
    @Override protected void onActivityResult(int request, int result, Intent data) {
        super.onActivityResult(request, result, data);
        if (request == 1 && result == RESULT_OK && data != null && data.getData() != null) {
            try (OutputStream stream = getContentResolver().openOutputStream(data.getData())) {
                if (stream == null) throw new java.io.IOException();
                stream.write(exported.getBytes(StandardCharsets.UTF_8));
            } catch (Exception e) { output.setText("Export failed: " + error(e) + "\n" + exported); }
        }
    }
    private void persist(JSONObject result) throws Exception {
        AtomicFile file = new AtomicFile(new File(getFilesDir(), "diagnostics.json"));
        FileOutputStream stream = null;
        try {
            stream = file.startWrite(); stream.write(result.toString(2).getBytes(StandardCharsets.UTF_8)); file.finishWrite(stream);
        } catch (Exception e) { if (stream != null) file.failWrite(stream); throw e; }
    }
    private void runProbe() {
        probe.setEnabled(false); output.setText("Probing…");
        new Thread(() -> {
            JSONObject result = new JSONObject();
            put(result, "schema_version", 1); put(result, "synthetic", false); put(result, "complete", false);
            put(result, "run_id", UUID.randomUUID().toString()); put(result, "timestamp", timestamp());
            try {
                persist(result); // Replace previous completed evidence immediately.
                JSONObject device = new JSONObject();
                put(device, "model", Build.MODEL); put(device, "manufacturer", Build.MANUFACTURER);
                put(device, "android_release", Build.VERSION.RELEASE); put(device, "sdk", Build.VERSION.SDK_INT);
                put(device, "security_patch", Build.VERSION.SECURITY_PATCH); put(device, "fingerprint", Build.FINGERPRINT);
                put(device, "abis", new JSONArray(java.util.Arrays.asList(Build.SUPPORTED_ABIS))); put(result, "device", device);
                put(result, "widevine", drm(UUID.fromString("edef8ba9-79d6-4ace-a3c8-27dcd51d21ed")));
                put(result, "clearkey", drm(UUID.fromString("e2719d58-a985-b3c9-781a-b030af78d30e")));
                put(result, "codecs", codecs());
                put(result, "complete", true); put(result, "finished_at", timestamp()); persist(result);
                exported = result.toString(2);
            } catch (Exception e) {
                put(result, "error", error(e)); exported = result.toString();
                try { persist(result); } catch (Exception ignored) { exported = "Export write failed. " + exported; }
            }
            runOnUiThread(() -> { if (!isDestroyed()) { output.setText(exported); probe.setEnabled(true); } });
        }, "media-diagnostics").start();
    }
    static JSONObject drm(UUID uuid) {
        JSONObject result = new JSONObject(); JSONObject properties = new JSONObject(); JSONObject session = new JSONObject();
        put(result, "supported", null); put(result, "construction", "NOT_TESTED"); put(result, "properties", properties);
        put(session, "status", "NOT_TESTED"); put(session, "security_level", null); put(session, "security_level_name", "UNKNOWN");
        put(result, "session", session);
        MediaDrm drm = null; byte[] sessionId = null;
        try {
            put(result, "supported", MediaDrm.isCryptoSchemeSupported(uuid));
            // Construct separately: support query is only a capability advertisement.
            drm = new MediaDrm(uuid); put(result, "construction", "SUCCESS");
            for (String name : SAFE_PROPERTIES) {
                try { put(properties, name, drm.getPropertyString(name)); }
                catch (Exception e) { put(properties, name, null); put(properties, name + "_error", error(e)); }
            }
            if (Build.VERSION.SDK_INT >= 28) {
                try { put(result, "connected_hdcp_level", drm.getConnectedHdcpLevel()); put(result, "max_hdcp_level", drm.getMaxHdcpLevel()); }
                catch (Exception e) { put(result, "hdcp_error", error(e)); }
            } else { put(result, "hdcp_status", "API_UNAVAILABLE"); }
            try {
                sessionId = drm.openSession(); put(session, "status", "OPENED");
                if (Build.VERSION.SDK_INT >= 28) {
                    try {
                        int level = drm.getSecurityLevel(sessionId);
                        put(session, "security_level", level); put(session, "security_level_name", securityName(level));
                    } catch (Exception e) { put(session, "security_level_error", error(e)); }
                } else { put(session, "security_level_name", "API_UNAVAILABLE"); }
            } catch (NotProvisionedException e) { put(session, "status", "PROVISIONING_REQUIRED"); }
            catch (ResourceBusyException e) { put(session, "status", "RESOURCE_BUSY"); }
            catch (Exception e) { put(session, "status", "ERROR"); put(session, "error", error(e)); }
        } catch (UnsupportedSchemeException e) { put(result, "construction", "UNSUPPORTED_SCHEME"); }
        catch (Exception e) { put(result, "construction", "ERROR"); put(result, "error", error(e)); }
        finally {
            if (drm != null) {
                if (sessionId != null) {
                    try { drm.closeSession(sessionId); put(session, "closed", true); }
                    catch (Exception e) { put(session, "close_error", error(e)); }
                }
                try { drm.release(); } catch (Exception ignored) { }
            }
        }
        return result;
    }
    static String securityName(int level) {
        switch (level) {
            case MediaDrm.SECURITY_LEVEL_SW_SECURE_CRYPTO: return "SW_SECURE_CRYPTO";
            case MediaDrm.SECURITY_LEVEL_SW_SECURE_DECODE: return "SW_SECURE_DECODE";
            case MediaDrm.SECURITY_LEVEL_HW_SECURE_CRYPTO: return "HW_SECURE_CRYPTO";
            case MediaDrm.SECURITY_LEVEL_HW_SECURE_DECODE: return "HW_SECURE_DECODE";
            case MediaDrm.SECURITY_LEVEL_HW_SECURE_ALL: return "HW_SECURE_ALL";
            default: return "UNKNOWN";
        }
    }
    static JSONArray codecs() {
        JSONArray list = new JSONArray();
        for (MediaCodecInfo info : new MediaCodecList(MediaCodecList.ALL_CODECS).getCodecInfos()) {
            if (info.isEncoder()) continue;
            for (String mime : info.getSupportedTypes()) {
                if (!mime.startsWith("video/")) continue;
                JSONObject codec = new JSONObject(); list.put(codec);
                put(codec, "name", info.getName()); put(codec, "mime", mime);
                put(codec, "evidence", "ADVERTISED"); put(codec, "configured", false); put(codec, "actually_used", false);
                put(codec, "hardware_accelerated", Build.VERSION.SDK_INT >= 29 ? info.isHardwareAccelerated() : null);
                put(codec, "software_only", Build.VERSION.SDK_INT >= 29 ? info.isSoftwareOnly() : null);
                put(codec, "vendor", Build.VERSION.SDK_INT >= 29 ? info.isVendor() : null);
                put(codec, "alias", Build.VERSION.SDK_INT >= 29 ? info.isAlias() : null);
                put(codec, "canonical_name", Build.VERSION.SDK_INT >= 29 ? info.getCanonicalName() : null);
                try {
                    MediaCodecInfo.CodecCapabilities caps = info.getCapabilitiesForType(mime);
                    put(codec, "adaptive_playback", caps.isFeatureSupported(MediaCodecInfo.CodecCapabilities.FEATURE_AdaptivePlayback));
                    put(codec, "secure_playback", caps.isFeatureSupported(MediaCodecInfo.CodecCapabilities.FEATURE_SecurePlayback));
                    put(codec, "secure_playback_required", caps.isFeatureRequired(MediaCodecInfo.CodecCapabilities.FEATURE_SecurePlayback));
                    put(codec, "tunneled_playback", caps.isFeatureSupported(MediaCodecInfo.CodecCapabilities.FEATURE_TunneledPlayback));
                    put(codec, "low_latency", Build.VERSION.SDK_INT >= 30 ? caps.isFeatureSupported(MediaCodecInfo.CodecCapabilities.FEATURE_LowLatency) : null);
                    JSONArray profiles = new JSONArray();
                    for (MediaCodecInfo.CodecProfileLevel p : caps.profileLevels) {
                        JSONObject entry = new JSONObject(); put(entry, "profile", p.profile); put(entry, "level", p.level); profiles.put(entry);
                    }
                    put(codec, "profiles_levels", profiles);
                    MediaCodecInfo.VideoCapabilities video = caps.getVideoCapabilities();
                    if (video != null) {
                        put(codec, "width_range", video.getSupportedWidths().toString()); put(codec, "height_range", video.getSupportedHeights().toString());
                        put(codec, "frame_rate_range", video.getSupportedFrameRates().toString());
                        put(codec, "bitrate_range", video.getBitrateRange().toString());
                        put(codec, "width_alignment", video.getWidthAlignment()); put(codec, "height_alignment", video.getHeightAlignment());
                        JSONArray formats = new JSONArray();
                        for (int[] size : new int[][] {{1920,1080}, {3840,2160}}) {
                            JSONObject format = new JSONObject(); put(format, "width", size[0]); put(format, "height", size[1]);
                            boolean supported = video.isSizeSupported(size[0], size[1]); put(format, "size_supported", supported);
                            put(format, "supports_30fps", video.areSizeAndRateSupported(size[0], size[1], 30));
                            put(format, "supports_60fps", video.areSizeAndRateSupported(size[0], size[1], 60));
                            if (supported) put(format, "frame_rate_range", video.getSupportedFrameRatesFor(size[0], size[1]).toString());
                            formats.put(format);
                        }
                        put(codec, "advertised_formats", formats);
                    }
                } catch (Exception e) { put(codec, "error", error(e)); }
            }
        }
        return list;
    }
}

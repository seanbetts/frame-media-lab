package org.framemedialab.media;

import android.app.Activity;
import android.content.Intent;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.os.SystemClock;
import org.json.JSONObject;
import android.util.AtomicFile;
import android.view.SurfaceHolder;
import android.view.SurfaceView;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import java.io.File;
import java.io.FileOutputStream;
import java.nio.charset.StandardCharsets;

/** Clear MediaExtractor/MediaCodec playback. No DRM, XR or external dependencies. */
public final class MainActivity extends Activity implements SurfaceHolder.Callback {
    private final Handler handler = new Handler(Looper.getMainLooper());
    private static String currentLaunchId;
    private final LaunchRecord launch = new LaunchRecord();
    private String activitySnapshot = launch.initialJson();
    private Button play;
    private long cancelDeadline;
    private boolean waitingForRelease, forceStopRequired, resumed;
    private SurfaceView surface;
    private TextView status;
    private EditText source;
    private String pendingSource;
    private ClearPlayer player;
    private boolean surfaceReady;
    private final Runnable update = new Runnable() {
        @Override public void run() { export(); handler.postDelayed(this, 1000); }
    };
    @Override public void onCreate(Bundle saved) {
        super.onCreate(saved);
        currentLaunchId = launch.id;
        writeSnapshot(activitySnapshot); // Invalidate install -r / prior-run evidence before UI or input.
        LinearLayout column = new LinearLayout(this); column.setOrientation(LinearLayout.VERTICAL); column.setPadding(16,16,16,16);
        TextView title = new TextView(this); title.setText("FRAME MEDIA LAB — CLEAR VIDEO"); title.setTextSize(22); column.addView(title);
        source = new EditText(this); source.setSingleLine(true); source.setHint("Local path, content://, http:// or https://"); column.addView(source);
        LinearLayout buttons = new LinearLayout(this); column.addView(buttons);
        play = new Button(this); play.setText("Play"); buttons.addView(play); play.setOnClickListener(v -> start(source.getText().toString()));
        Button pick = new Button(this); pick.setText("Choose file"); buttons.addView(pick); pick.setOnClickListener(v -> {
            try { startActivityForResult(new Intent(Intent.ACTION_OPEN_DOCUMENT).setType("video/*").addCategory(Intent.CATEGORY_OPENABLE), 1); }
            catch (Exception e) { status.setText("File picker unavailable. Supply --es source or a readable app-private path."); }
        });
        Button stop = new Button(this); stop.setText("Stop"); buttons.addView(stop); stop.setOnClickListener(v -> { pendingSource = null; cancelActive(); export(); });
        surface = new SurfaceView(this); surface.getHolder().addCallback(this);
        column.addView(surface, new LinearLayout.LayoutParams(-1, 0, 1));
        status = new TextView(this); status.setTextIsSelectable(true);
        ScrollView scroll = new ScrollView(this); scroll.addView(status); column.addView(scroll, new LinearLayout.LayoutParams(-1, 240));
        setContentView(column);
        pendingSource = getIntent().getStringExtra("source");
        if (pendingSource != null) source.setText(pendingSource);
        status.setText("Choose a generated clear fixture. Surface visibility and audible sound need headset observation.");
    }
    @Override protected void onActivityResult(int request, int result, Intent data) {
        super.onActivityResult(request,result,data);
        if (request == 1 && result == RESULT_OK && data != null && data.getData() != null) {
            source.setText(data.getData().toString()); start(data.getData().toString());
        }
    }
    private void start(String value) {
        if (forceStopRequired || value == null || value.trim().isEmpty()) return;
        pendingSource = value.trim();
        tryPending();
    }
    private void tryPending() {
        if (!launch.id.equals(currentLaunchId)) return;
        if (forceStopRequired || waitingForRelease || pendingSource == null || !surfaceReady || !resumed) return;
        if (ClearPlayer.active() != null) { cancelActive(); return; }
        String value = pendingSource; pendingSource = null;
        ClearPlayer next = new ClearPlayer(getApplicationContext(), surface.getHolder().getSurface(), value, launch.id,
            completed -> handler.post(() -> { if (player == completed) export(); }));
        next.surfaceSize(surface.getWidth(), surface.getHeight());
        if (next.start()) { player = next; export(); }
        else { pendingSource = value; cancelActive(); }
    }
    private void cancelActive() {
        if (!launch.id.equals(currentLaunchId)) return;
        ClearPlayer active = ClearPlayer.active();
        if (active == null || waitingForRelease) return;
        active.stop(); waitingForRelease = true; play.setEnabled(false);
        cancelDeadline = SystemClock.elapsedRealtime() + 5000;
        handler.post(awaitRelease);
    }
    private final Runnable awaitRelease = new Runnable() {
        @Override public void run() {
            if (!launch.id.equals(currentLaunchId)) return;
            if (ClearPlayer.active() == null) {
                waitingForRelease = false; play.setEnabled(true); export(); tryPending();
            } else if (SystemClock.elapsedRealtime() >= cancelDeadline) {
                waitingForRelease = false; forceStopRequired = true; pendingSource = null;
                try {
                    JSONObject stalled = new JSONObject(launch.initialJson());
                    stalled.put("state", "NEEDS_FORCE_STOP");
                    stalled.put("teardown_status", "CANCELLATION_TIMEOUT");
                    stalled.put("error", "Previous decoder resources are still owned; force-stop the media app before retrying");
                    activitySnapshot = stalled.toString();
                } catch (org.json.JSONException e) { throw new IllegalStateException(e); }
                export();
            } else handler.postDelayed(this, 100);
        }
    };
    private void export() {
        writeSnapshot(forceStopRequired || player == null ? activitySnapshot : player.snapshot());
    }
    private void writeSnapshot(String json) {
        if (!launch.id.equals(currentLaunchId)) return; // Old Activity callbacks cannot replace this launch.
        if (status != null) status.setText(json);
        AtomicFile file = new AtomicFile(new File(getFilesDir(), "media.json")); FileOutputStream stream = null;
        try { stream = file.startWrite(); stream.write(json.getBytes(StandardCharsets.UTF_8)); file.finishWrite(stream); }
        catch (Exception e) {
            if (stream != null) file.failWrite(stream);
            file.delete(); // Do not leave the previous completed run readable after invalidation failure.
            if (status != null) status.append("\nJSON export failed: " + e.getClass().getSimpleName());
        }
    }
    @Override public void surfaceCreated(SurfaceHolder holder) { surfaceReady = true; tryPending(); }
    @Override public void surfaceChanged(SurfaceHolder holder,int format,int width,int height) { if (player != null) player.surfaceSize(width,height); }
    @Override public void surfaceDestroyed(SurfaceHolder holder) { surfaceReady = false; cancelActive(); export(); }
    @Override protected void onResume() { super.onResume(); resumed = true; handler.post(update); tryPending(); }
    @Override protected void onPause() { resumed = false; handler.removeCallbacks(update); pendingSource = null; cancelActive(); export(); super.onPause(); }
    @Override protected void onDestroy() { handler.removeCallbacks(update); handler.removeCallbacks(awaitRelease); super.onDestroy(); }
}

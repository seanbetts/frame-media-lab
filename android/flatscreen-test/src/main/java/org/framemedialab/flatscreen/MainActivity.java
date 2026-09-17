package org.framemedialab.flatscreen;

import android.animation.ObjectAnimator;
import android.app.Activity;
import android.graphics.Color;
import android.os.Build;
import android.os.Bundle;
import android.view.MotionEvent;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import java.util.ArrayDeque;
import java.util.Locale;

/** Ordinary Activity; seeing this on an Android screenshot is not headset evidence. */
public final class MainActivity extends Activity {
    private TextView events, pointer, dimensions;
    private final ArrayDeque<String> log = new ArrayDeque<>();
    private ObjectAnimator animation;
    private int count;
    private TextView label(LinearLayout parent, String text, int size) {
        TextView view = new TextView(this); view.setText(text); view.setTextSize(size); view.setTextColor(Color.WHITE); parent.addView(view); return view;
    }
    @Override public void onCreate(Bundle saved) {
        super.onCreate(saved);
        ScrollView scroll = new ScrollView(this);
        LinearLayout column = new LinearLayout(this); column.setOrientation(LinearLayout.VERTICAL); column.setPadding(32,32,32,32);
        column.setBackgroundColor(Color.rgb(13,36,65)); scroll.addView(column); setContentView(scroll);
        label(column, "FRAME MEDIA LAB", 32); label(column, "2D ANDROID TEST", 26);
        label(column, "Activity is running — confirm visibility in the headset", 18);
        label(column, Build.MANUFACTURER + " / " + Build.MODEL + "\nAndroid " + Build.VERSION.RELEASE + " (API " + Build.VERSION.SDK_INT + ")\n" + java.util.Arrays.toString(Build.SUPPORTED_ABIS), 16);
        dimensions = label(column, "Waiting for layout", 18);
        column.addOnLayoutChangeListener((v,l,t,r,b,ol,ot,or,ob) -> dimensions.setText("Window content: " + scroll.getWidth() + " × " + scroll.getHeight() + " px\nDisplay metrics: " + getResources().getDisplayMetrics().widthPixels + " × " + getResources().getDisplayMetrics().heightPixels + " px"));
        Button button = new Button(this); button.setText("Tap / click me: 0"); column.addView(button);
        button.setOnClickListener(v -> { button.setText("Tap / click me: " + ++count); event("Button activated " + count); });
        EditText entry = new EditText(this); entry.setSingleLine(true); entry.setTextColor(Color.WHITE); entry.setHintTextColor(Color.LTGRAY);
        entry.setHint("Test keyboard / text input here"); column.addView(entry);
        TextView moving = label(column, "● Animation", 28);
        animation = ObjectAnimator.ofFloat(moving, "alpha", 1f, 0.25f, 1f); animation.setDuration(1800); animation.setRepeatCount(ObjectAnimator.INFINITE);
        pointer = label(column, "Touch / pointer: waiting", 16); events = label(column, "Lifecycle", 16);
        for (int i=1;i<=20;i++) label(column, "Scroll test row " + i + " — move the panel, resize, then return here.", 20);
        event("onCreate");
    }
    private void event(String value) {
        if (log.size() >= 20) log.removeFirst(); log.addLast(android.os.SystemClock.elapsedRealtime() + " ms " + value);
        if (events != null) events.setText(android.text.TextUtils.join("\n", log));
    }
    private void pointerEvent(MotionEvent e) {
        if (pointer != null) pointer.setText(String.format(Locale.US, "%s x=%.1f y=%.1f source=0x%x buttons=0x%x", MotionEvent.actionToString(e.getAction()), e.getX(), e.getY(), e.getSource(), e.getButtonState()));
    }
    @Override public boolean dispatchTouchEvent(MotionEvent e) { pointerEvent(e); return super.dispatchTouchEvent(e); }
    @Override public boolean dispatchGenericMotionEvent(MotionEvent e) { pointerEvent(e); return super.dispatchGenericMotionEvent(e); }
    @Override protected void onStart() { super.onStart(); event("onStart"); }
    @Override protected void onResume() { super.onResume(); event("onResume"); if (animation != null) animation.start(); }
    @Override protected void onPause() { event("onPause"); if (animation != null) animation.cancel(); super.onPause(); }
    @Override protected void onStop() { event("onStop"); super.onStop(); }
    @Override protected void onDestroy() { event("onDestroy"); super.onDestroy(); }
}

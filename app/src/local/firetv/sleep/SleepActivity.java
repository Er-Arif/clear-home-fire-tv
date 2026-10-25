package local.firetv.sleep;

import android.app.Activity;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.util.Log;
import android.view.Gravity;
import android.view.View;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.TextView;

public final class SleepActivity extends Activity {
    private final Handler handler = new Handler(Looper.getMainLooper());
    private int attempts;

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        attemptSleep();
    }

    private void attemptSleep() {
        if (SleepService.isConnected()) {
            boolean accepted = SleepService.sleep();
            Log.i("FireTvSleep", "Standby action accepted=" + accepted);
            if (accepted) { finish(); return; }
            showError("Fire OS declined the standby action.");
        } else if (++attempts < 15) {
            handler.postDelayed(new Runnable() {
                @Override public void run() { attemptSleep(); }
            }, 100);
        } else {
            showError("The Sleep shortcut service is disabled. Enable it in Accessibility or restore it using the setup guide.");
        }
    }

    private void showError(String message) {
        LinearLayout layout = new LinearLayout(this);
        layout.setOrientation(LinearLayout.VERTICAL);
        layout.setGravity(Gravity.CENTER);
        layout.setPadding(60, 40, 60, 40);
        TextView text = new TextView(this);
        text.setText(message);
        text.setTextSize(22);
        layout.addView(text);
        Button close = new Button(this);
        close.setText("Close");
        close.setOnClickListener(new View.OnClickListener() {
            @Override public void onClick(View view) { finish(); }
        });
        layout.addView(close);
        setContentView(layout);
        close.requestFocus();
    }

    @Override public void onDestroy() {
        handler.removeCallbacksAndMessages(null);
        super.onDestroy();
    }
}

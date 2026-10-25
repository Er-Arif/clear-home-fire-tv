package local.firetv.sleep;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.DialogInterface;
import android.content.ActivityNotFoundException;
import android.content.Intent;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.view.Gravity;
import android.view.KeyEvent;
import android.view.View;
import android.widget.Button;
import android.widget.GridLayout;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.List;
import java.util.Locale;

/** Native, remote-operated launcher. No web content, feeds, analytics, or polling. */
public final class HomeActivity extends Activity {
    private static final int INK = Color.rgb(242, 245, 250);
    private static final int MUTED = Color.rgb(150, 164, 184);
    private final Handler handler = new Handler(Looper.getMainLooper());
    private boolean allApps;
    private View previousFocus;
    private TextView clock;
    private final Runnable tick = new Runnable() {
        @Override public void run() {
            if (clock != null) clock.setText(new SimpleDateFormat("h:mm a", Locale.getDefault()).format(new Date()));
            handler.postDelayed(this, 60000);
        }
    };

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        allApps = state != null && state.getBoolean("allApps");
        render();
    }
    @Override protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        allApps = false; render();
    }
    @Override protected void onResume() {
        super.onResume();
        handler.removeCallbacks(tick); tick.run();
        if (previousFocus != null) previousFocus.requestFocus();
    }
    @Override protected void onPause() {
        previousFocus = getCurrentFocus(); handler.removeCallbacks(tick); super.onPause();
    }
    @Override protected void onSaveInstanceState(Bundle state) {
        state.putBoolean("allApps", allApps); super.onSaveInstanceState(state);
    }
    @Override protected void onDestroy() { handler.removeCallbacksAndMessages(null); super.onDestroy(); }
    @Override public void onBackPressed() {
        if (allApps) { allApps = false; render(); }
        else { View first = findViewById(200); if (first != null) first.requestFocus(); }
    }
    @Override public boolean onKeyDown(int code, KeyEvent event) {
        if (code == KeyEvent.KEYCODE_MENU && event.getRepeatCount() == 0) {
            allApps = !allApps; render(); return true;
        }
        return super.onKeyDown(code, event);
    }

    private int dp(float value) { return Math.round(value * getResources().getDisplayMetrics().density); }
    private GradientDrawable background(int fill, int stroke) {
        GradientDrawable shape = new GradientDrawable(); shape.setColor(fill); shape.setCornerRadius(dp(13));
        shape.setStroke(dp(2), stroke); return shape;
    }
    private TextView text(String label, int size, int color) {
        TextView view = new TextView(this); view.setText(label); view.setTextSize(size); view.setTextColor(color);
        view.setFontFeatureSettings("kern"); return view;
    }
    private Button action(String name, int id, final Runnable run) {
        final Button button = new Button(this); button.setId(id); button.setText(name); button.setAllCaps(false);
        button.setTextSize(14); button.setTextColor(INK); button.setMinHeight(0); button.setMinimumHeight(0);
        button.setFocusableInTouchMode(true);
        button.setPadding(dp(15), 0, dp(15), 0); button.setBackground(background(0xFF1B2433, Color.TRANSPARENT));
        button.setOnFocusChangeListener(new View.OnFocusChangeListener() {
            @Override public void onFocusChange(View view, boolean focus) {
                button.setBackground(background(focus ? 0xFF34425A : 0xFF1B2433, focus ? 0xFFA9C9FF : Color.TRANSPARENT));
            }
        });
        button.setOnClickListener(new View.OnClickListener() { @Override public void onClick(View view) { run.run(); } });
        return button;
    }

    private void render() {
        previousFocus = null;
        getWindow().getDecorView().setSystemUiVisibility(View.SYSTEM_UI_FLAG_FULLSCREEN
            | View.SYSTEM_UI_FLAG_HIDE_NAVIGATION | View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY);
        LinearLayout root = new LinearLayout(this); root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(dp(44), dp(24), dp(44), dp(20));
        root.setBackground(new GradientDrawable(GradientDrawable.Orientation.TL_BR,
            new int[]{0xFF101B2E, 0xFF080D15, 0xFF10131C}));

        LinearLayout bar = new LinearLayout(this); bar.setGravity(Gravity.CENTER_VERTICAL);
        TextView brand = text("HOME", 16, INK); brand.setLetterSpacing(0.18f); brand.setTypeface(null, Typeface.BOLD);
        bar.addView(brand, new LinearLayout.LayoutParams(0, dp(40), 1)); brand.setGravity(Gravity.CENTER_VERTICAL);
        Button library = action(allApps ? "Watch" : "All Apps", 100, new Runnable() {
            @Override public void run() { allApps = !allApps; render(); }
        });
        Button settings = action("Settings", 101, new Runnable() {
            @Override public void run() { openSettings(); }
        });
        Button sleep = action("Sleep", 102, new Runnable() {
            @Override public void run() { startActivity(new Intent(HomeActivity.this, SleepActivity.class)); }
        });
        for (Button button : new Button[]{library, settings, sleep}) {
            LinearLayout.LayoutParams p = new LinearLayout.LayoutParams(dp(97), dp(40)); p.setMargins(dp(8),0,0,0); bar.addView(button,p);
        }
        clock = text("", 14, MUTED); clock.setGravity(Gravity.RIGHT | Gravity.CENTER_VERTICAL);
        bar.addView(clock, new LinearLayout.LayoutParams(dp(100),dp(40)));
        root.addView(bar);

        LinearLayout headings = new LinearLayout(this); headings.setOrientation(LinearLayout.VERTICAL);
        TextView title = text(allApps ? "Your library" : "What will you watch?", 32, INK);
        title.setTypeface(null, Typeface.BOLD); headings.addView(title);
        headings.addView(text(allApps ? "All installed apps, in one place." : "Your apps. A little more space.", 14, MUTED));
        LinearLayout.LayoutParams hp = new LinearLayout.LayoutParams(-1,-2); hp.setMargins(0,dp(27),0,dp(18)); root.addView(headings,hp);

        ScrollView scroll = new ScrollView(this); scroll.setClipChildren(false); scroll.setClipToPadding(false);
        scroll.setFillViewport(false); scroll.setVerticalScrollBarEnabled(false); scroll.setPadding(dp(4),dp(5),dp(4),dp(5));
        GridLayout grid = new GridLayout(this); grid.setColumnCount(5); grid.setClipChildren(false); grid.setClipToPadding(false);
        List<AppCatalog.App> apps = allApps ? AppCatalog.all(this) : AppCatalog.watch(this);
        int screenWidth = getResources().getDisplayMetrics().widthPixels;
        int cardWidth = (screenWidth - dp(88+8+4*16))/5;
        for (int i=0; i<apps.size(); i++) {
            final AppCatalog.App app = apps.get(i);
            LinearLayout tile = tile(app); tile.setId(200+i);
            if(i < 5) tile.setNextFocusUpId(i < 2 ? 100 : i < 4 ? 101 : 102);
            GridLayout.LayoutParams p = new GridLayout.LayoutParams(); p.width=cardWidth; p.height=dp(126);
            p.setMargins(0,0,i%5 == 4 ? 0 : dp(16),dp(16)); grid.addView(tile,p);
        }
        if (apps.isEmpty()) grid.addView(text("Open All Apps and hold OK on an app to add it here.",18,MUTED));
        scroll.addView(grid); root.addView(scroll,new LinearLayout.LayoutParams(-1,0,1));
        TextView footer = text(allApps ? "Hold OK on an app  ·  Add/remove favourite       BACK  ·  Home"
            : "MENU  ·  All Apps                                      ↑  Quick controls",11,MUTED);
        footer.setGravity(Gravity.CENTER_VERTICAL); root.addView(footer,new LinearLayout.LayoutParams(-1,dp(24)));
        setContentView(root);
        View first=findViewById(200); if(first != null) first.requestFocus(); else library.requestFocus();
        handler.removeCallbacks(tick); tick.run();
    }

    private LinearLayout tile(final AppCatalog.App app) {
        final LinearLayout tile = new LinearLayout(this); tile.setOrientation(LinearLayout.VERTICAL);
        tile.setFocusableInTouchMode(true); tile.setClickable(true); tile.setPadding(dp(3),dp(3),dp(3),dp(3));
        tile.setContentDescription(app.name); tile.setBackground(background(0xFF172130,Color.TRANSPARENT));
        ImageView image=new ImageView(this); image.setImageDrawable(app.art); image.setAdjustViewBounds(false);
        image.setScaleType(ImageView.ScaleType.FIT_CENTER); image.setBackground(background(0xFF172130,Color.TRANSPARENT));
        int imageHeight=dp(88); if(!app.banner) image.setPadding(dp(25),dp(12),dp(25),dp(12));
        tile.addView(image,new LinearLayout.LayoutParams(-1,imageHeight));
        TextView name=text(app.name,13,INK); name.setGravity(Gravity.CENTER); name.setSingleLine(true);
        name.setEllipsize(android.text.TextUtils.TruncateAt.END); tile.addView(name,new LinearLayout.LayoutParams(-1,0,1));
        tile.setOnFocusChangeListener(new View.OnFocusChangeListener() {
            @Override public void onFocusChange(View view,boolean focus) {
                tile.setBackground(background(focus?0xFF293B56:0xFF172130,focus?0xFFB6D2FF:Color.TRANSPARENT));
                tile.setElevation(focus?dp(8):0); tile.setScaleX(focus?1.035f:1f); tile.setScaleY(focus?1.035f:1f);
            }
        });
        tile.setOnClickListener(new View.OnClickListener() {
            @Override public void onClick(View view) {
                try { startActivity(new Intent(app.intent).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)); }
                catch(ActivityNotFoundException | SecurityException error) {
                    Toast.makeText(HomeActivity.this,"Could not open "+app.name+". It may need reinstalling or updating.",Toast.LENGTH_LONG).show();
                }
            }
        });
        tile.setOnLongClickListener(new View.OnLongClickListener() {
            @Override public boolean onLongClick(View view) {
                int result = AppCatalog.toggleFavorite(HomeActivity.this, app.packageName);
                Toast.makeText(HomeActivity.this, result > 0 ? "Added to favourites" : result < 0 ? "Removed from favourites" : "Maximum 30 favourites reached",
                    Toast.LENGTH_SHORT).show();
                if (!allApps) render();
                return true;
            }
        });
        return tile;
    }

    private void openSettings() {
        final String[] labels = {"Network", "Display & Sound", "Applications", "Remotes & Bluetooth",
            "Preferences", "My Fire TV", "Accessibility"};
        final String[] screens = {"tv.network.NetworkActivity", "tv.display_sounds.DisplayAndSoundsActivity",
            "tv.applications.ApplicationsActivity", "tv.controllers_bluetooth_devices.ControllersAndBluetoothActivity",
            "tv.preferences.PreferencesActivity", "tv.device.DeviceActivity", "tv.accessibility.AccessibilityActivity"};
        new AlertDialog.Builder(this).setTitle("Fire TV settings")
            .setItems(labels, new DialogInterface.OnClickListener() {
                @Override public void onClick(DialogInterface dialog, int which) {
                    try {
                        startActivity(new Intent().setClassName("com.amazon.tv.settings.v2",
                            "com.amazon.tv.settings.v2." + screens[which]));
                    } catch(ActivityNotFoundException | SecurityException error) {
                        Toast.makeText(HomeActivity.this,"Hold Home to open Fire TV quick settings.",Toast.LENGTH_LONG).show();
                    }
                }
            }).setNegativeButton("Close", null).show();
    }
}

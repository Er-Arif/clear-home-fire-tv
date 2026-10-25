package local.firetv.sleep;

import android.accessibilityservice.AccessibilityService;
import android.view.accessibility.AccessibilityEvent;

/** OS-bound service; no event subscriptions or screen-reading capability. */
public final class SleepService extends AccessibilityService {
    private static SleepService connected;

    @Override protected void onServiceConnected() { connected = this; }
    @Override public void onDestroy() {
        if (connected == this) connected = null;
        super.onDestroy();
    }
    @Override public void onAccessibilityEvent(AccessibilityEvent event) { }
    @Override public void onInterrupt() { }

    static boolean isConnected() { return connected != null; }
    static boolean sleep() {
        SleepService service = connected;
        return service != null && service.performGlobalAction(GLOBAL_ACTION_LOCK_SCREEN);
    }
}

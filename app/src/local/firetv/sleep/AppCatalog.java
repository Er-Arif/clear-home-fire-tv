package local.firetv.sleep;

import android.content.Context;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.content.pm.ResolveInfo;
import android.graphics.drawable.Drawable;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Collections;
import java.util.Comparator;

/** Resolves installed app entry points; no remote catalog or recommendation API. */
final class AppCatalog {
    static final class App {
        final String name;
        final String packageName;
        final Intent intent;
        final Drawable art;
        final boolean banner;
        App(String name, String packageName, Intent intent, Drawable art, boolean banner) {
            this.name = name; this.packageName = packageName; this.intent = intent;
            this.art = art; this.banner = banner;
        }
    }

    private static final String[][] WATCH = {
        {"com.netflix.ninja", "Netflix"}, {"com.amazon.firebat", "Prime Video"},
        {"com.amazon.firetv.youtube", "YouTube"}, {"in.startv.hotstar", "JioHotstar"},
        {"com.apple.atve.amazon.appletv", "Apple TV"},
        {"tv.airtel.xstream.tvapp", "Xstream Play"}, {"com.jio.media.jiotvplus", "JioTV+"},
        {"com.zee5.amazon", "ZEE5"}, {"com.mxtech.videoplayer.television", "MX Player"},
        {"com.urbanapps.screenmirroringftv", "Screen Mirroring"}
    };

    private static List<App> defaults(Context context) {
        List<App> result = new ArrayList<>();
        PackageManager pm = context.getPackageManager();
        for (String[] item : WATCH) {
            Intent intent = pm.getLeanbackLaunchIntentForPackage(item[0]);
            if (intent == null) intent = pm.getLaunchIntentForPackage(item[0]);
            if (intent != null) result.add(resolve(pm, item[0], item[1], intent));
        }
        return result;
    }

    private static List<String> defaultPackages(Context context) {
        List<String> result = new ArrayList<>();
        for (App app : defaults(context)) result.add(app.packageName);
        return result;
    }

    static List<App> watch(Context context) {
        List<String> packages = new FavoriteStore(context).read(defaultPackages(context));
        Map<String, App> available = new LinkedHashMap<>();
        for (App app : all(context)) available.put(app.packageName, app);
        for (App app : defaults(context)) available.put(app.packageName, app);
        List<App> result = new ArrayList<>();
        for (String pkg : packages) if (available.containsKey(pkg)) result.add(available.get(pkg));
        return result;
    }

    static int toggleFavorite(Context context, String pkg) {
        FavoriteStore store = new FavoriteStore(context);
        List<String> current = store.read(defaultPackages(context));
        boolean already = current.contains(pkg);
        if (!already && current.size() >= FavoriteOrder.LIMIT) return 0;
        List<String> next = FavoriteOrder.toggle(current, pkg);
        store.write(next);
        return already ? -1 : 1;
    }

    static List<App> all(Context context) {
        PackageManager pm = context.getPackageManager();
        Map<String, App> unique = new LinkedHashMap<>();
        for (String category : new String[]{Intent.CATEGORY_LEANBACK_LAUNCHER, Intent.CATEGORY_LAUNCHER}) {
            Intent query = new Intent(Intent.ACTION_MAIN).addCategory(category);
            for (ResolveInfo info : pm.queryIntentActivities(query, 0)) {
                String pkg = info.activityInfo.packageName;
                if (pkg.equals(context.getPackageName()) || unique.containsKey(pkg)) continue;
                Intent launch = new Intent(Intent.ACTION_MAIN).addCategory(category)
                    .setClassName(pkg, info.activityInfo.name);
                unique.put(pkg, resolve(pm, pkg, info.loadLabel(pm).toString(), launch));
            }
        }
        List<App> result = new ArrayList<>(unique.values());
        Collections.sort(result, new Comparator<App>() {
            @Override public int compare(App a, App b) { return a.name.compareToIgnoreCase(b.name); }
        });
        return result;
    }

    private static App resolve(PackageManager pm, String pkg, String name, Intent intent) {
        Drawable art = null;
        boolean banner = false;
        try { art = pm.getApplicationBanner(pkg); banner = art != null; }
        catch (PackageManager.NameNotFoundException ignored) { }
        try { if (art == null) art = pm.getApplicationIcon(pkg); }
        catch (PackageManager.NameNotFoundException ignored) { }
        return new App(name, pkg, intent, art, banner);
    }
}

package local.firetv.sleep;

import java.util.ArrayList;
import java.util.List;

/** Ordered favourites, independent of Android storage and UI. */
final class FavoriteOrder {
    static final int LIMIT = 30;
    static List<String> normalize(List<String> source) {
        List<String> result = new ArrayList<>();
        for (String pkg : source) {
            if (pkg != null && pkg.matches("[A-Za-z][A-Za-z0-9_]*(\\.[A-Za-z0-9_]+)+")
                    && !result.contains(pkg) && result.size() < LIMIT) result.add(pkg);
        }
        return result;
    }
    static List<String> toggle(List<String> current, String pkg) {
        List<String> next = normalize(current);
        if (next.contains(pkg)) next.remove(pkg);
        else if (next.size() < LIMIT) next.add(pkg);
        return normalize(next);
    }
}

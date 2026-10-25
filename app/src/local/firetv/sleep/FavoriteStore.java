package local.firetv.sleep;

import android.content.Context;
import android.content.SharedPreferences;
import org.json.JSONArray;
import org.json.JSONException;
import java.util.ArrayList;
import java.util.List;

final class FavoriteStore {
    private final SharedPreferences preferences;
    FavoriteStore(Context context) {
        preferences = context.getSharedPreferences("clear_home", Context.MODE_PRIVATE);
    }
    List<String> read(List<String> defaults) {
        if (!preferences.contains("favorites")) return FavoriteOrder.normalize(defaults);
        List<String> result = new ArrayList<>();
        try {
            JSONArray values = new JSONArray(preferences.getString("favorites", "[]"));
            for (int i=0; i<values.length(); i++) result.add(values.optString(i, ""));
        } catch (JSONException malformed) { return FavoriteOrder.normalize(defaults); }
        return FavoriteOrder.normalize(result);
    }
    void write(List<String> values) {
        preferences.edit().putString("favorites", new JSONArray(FavoriteOrder.normalize(values)).toString()).apply();
    }
}

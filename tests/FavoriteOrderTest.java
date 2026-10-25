package local.firetv.sleep;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

public final class FavoriteOrderTest {
    private static void check(boolean condition, String message) {
        if (!condition) throw new AssertionError(message);
    }
    public static void main(String[] args) {
        List<String> values = FavoriteOrder.normalize(Arrays.asList("tv.one", "tv.one", "bad;value", null, "tv.two"));
        check(values.equals(Arrays.asList("tv.one", "tv.two")), "Normalize and preserve order");
        check(FavoriteOrder.toggle(values, "tv.one").equals(Arrays.asList("tv.two")), "Remove existing");
        check(FavoriteOrder.toggle(values, "tv.three").equals(Arrays.asList("tv.one", "tv.two", "tv.three")), "Append new");
        check(values.size() == 2, "Do not mutate input");
        List<String> many = new ArrayList<>();
        for (int i=0; i<40; i++) many.add("tv.app"+i);
        check(FavoriteOrder.normalize(many).size() == 30, "Bound stored favourites");
        check(!FavoriteOrder.toggle(many, "tv.extra").contains("tv.extra"), "Do not exceed limit");
        check(FavoriteOrder.normalize(new ArrayList<String>()).isEmpty(), "Allow deliberately empty favourites");
        System.out.println("FavoriteOrder: 7 checks passed");
    }
}

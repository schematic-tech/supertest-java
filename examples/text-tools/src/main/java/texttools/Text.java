package texttools;

public final class Text {
    private Text() {}

    public static String collapseSpaces(String text) {
        return text.replace("  ", " ");
    }
}

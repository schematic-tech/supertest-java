package texttools;

import static org.junit.Assert.assertEquals;
import static tech.schematic.Assumptions.assume;

import tech.schematic.Supertest;

public final class CollapseSpaces {
    private CollapseSpaces() {}

    @Supertest
    public static void collapsingSpacesAgainChangesNothing(String text) {
        assume(text != null);
        String once = Text.collapseSpaces(text);
        String twice = Text.collapseSpaces(once);

        assertEquals(once, twice);
    }
}

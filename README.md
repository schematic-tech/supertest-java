# Supertest for Java

```xml
<dependencies>
  <dependency>
    <groupId>tech.schematic.supertest</groupId>
    <artifactId>schematic-supertest</artifactId>
    <version>0.1.0</version>
    <scope>test</scope>
  </dependency>
  <dependency>
    <groupId>junit</groupId>
    <artifactId>junit</artifactId>
    <version>4.13.2</version>
    <scope>test</scope>
  </dependency>
</dependencies>
```

From the [text-tools example](examples/text-tools):

```java
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
```

See the [Getting Started Documentation](https://docs.schematic.tech/super).

## Example

Try [text-tools](https://github.com/schematic-tech/supertest-java/tree/main/examples/text-tools), a space-normalization example with a supertest.

## License

This library is available under either MIT or Apache-2.0, at your option.

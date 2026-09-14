# Supertest for Java

```xml
<dependency>
  <groupId>tech.schematic.supertest</groupId>
  <artifactId>schematic-supertest</artifactId>
  <version>0.1.0</version>
  <scope>test</scope>
</dependency>
```

```java
import tech.schematic.Supertest;
import static tech.schematic.Assumptions.assume;

public final class Arithmetic {
    @Supertest
    public static void integerDivisionIsBounded(int value, int divisor) {
        assume(value >= 0 && divisor > 0);
        if (value / divisor > value) {
            throw new AssertionError("Quotient exceeded the dividend");
        }
    }
}
```

See the [Getting Started Documentation](https://docs.schematic.tech/pup).

## License

This library is available under either MIT or Apache-2.0, at your option.

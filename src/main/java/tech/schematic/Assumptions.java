// SPDX-License-Identifier: MIT OR Apache-2.0
package tech.schematic;

/** Assumptions that restrict the input domain of a supertest. */
public final class Assumptions {
    private Assumptions() {
    }

    /**
     * Continues when the condition holds; otherwise exits the JVM successfully.
     *
     * <p>Run each concrete input in its own process. A rejected input ends all work
     * in the JVM, including when this method is called from a helper or worker
     * thread. JVM shutdown hooks run; stack {@code finally} blocks do not unwind.
     * A successful exit on a rejected input is not a proof of the specification.
     *
     * @param condition whether this input belongs to the supertest's domain
     */
    public static void assume(boolean condition) {
        if (!condition) {
            System.exit(0);
        }
    }
}

// SPDX-License-Identifier: MIT OR Apache-2.0
package tech.schematic;

import static tech.schematic.Assumptions.assume;
import static org.junit.Assert.*;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.InputStream;
import java.lang.annotation.ElementType;
import java.lang.annotation.Retention;
import java.lang.annotation.RetentionPolicy;
import java.lang.annotation.Target;
import java.util.concurrent.TimeUnit;
import org.junit.Test;

public class AuthoringTest {
    @Supertest
    public static int example(int value) {
        assume(value >= 0);
        return value + 1;
    }

    @Test
    public void markerPreservesBehaviorAndIsDiscoverable() throws Exception {
        assertEquals(4, example(3));
        assertNotNull(AuthoringTest.class.getMethod("example", int.class).getAnnotation(Supertest.class));
        assertEquals(RetentionPolicy.RUNTIME, Supertest.class.getAnnotation(Retention.class).value());
        assertArrayEquals(new ElementType[] {ElementType.METHOD}, Supertest.class.getAnnotation(Target.class).value());
        assertNull(Supertest.class.getAnnotation(java.lang.annotation.Repeatable.class));
    }

    @Test
    public void trueConditionIsEvaluatedOnce() {
        int calls = 0;
        assume(++calls == 1);
        assertEquals(1, calls);
    }

    @Test
    public void falseAssumptionExitsSuccessfullyFromHelperAndWorker() throws Exception {
        for (String mode : new String[] {"false", "worker"}) {
            Result result = child(mode);
            assertEquals(result.output, 0, result.code);
            assertTrue(result.output, result.output.contains("shutdown-hook"));
            assertFalse(result.output, result.output.contains("continued"));
            assertFalse(result.output, result.output.contains("finally-block"));
        }
    }

    @Test
    public void assertionsFailForAdmittedInputs() throws Exception {
        Result result = child("assertion");
        assertNotEquals(result.output, 0, result.code);
        assertTrue(result.output, result.output.contains("AssertionError"));
    }

    private static Result child(String mode) throws Exception {
        String java = new File(System.getProperty("java.home"), "bin/java").getPath();
        String classpath = System.getProperty("surefire.test.class.path", System.getProperty("java.class.path"));
        Process process = new ProcessBuilder(java, "-ea", "-cp", classpath, Probe.class.getName(), mode)
                .redirectErrorStream(true).start();
        if (!process.waitFor(15, TimeUnit.SECONDS)) {
            process.destroyForcibly();
            throw new AssertionError("Child JVM did not terminate");
        }
        ByteArrayOutputStream bytes = new ByteArrayOutputStream();
        try (InputStream stream = process.getInputStream()) {
            byte[] buffer = new byte[1024];
            int count;
            while ((count = stream.read(buffer)) != -1) {
                bytes.write(buffer, 0, count);
            }
        }
        return new Result(process.exitValue(), bytes.toString("UTF-8"));
    }

    private static final class Result {
        final int code;
        final String output;

        Result(int code, String output) {
            this.code = code;
            this.output = output;
        }
    }

    public static final class Probe {
        public static void main(String[] args) throws Exception {
            Runtime.getRuntime().addShutdownHook(new Thread(() -> System.out.println("shutdown-hook")));
            if ("assertion".equals(args[0])) {
                assume(true);
                assert false : "admitted input must fail";
            }
            try {
                if ("worker".equals(args[0])) {
                    Thread worker = new Thread(() -> example(-1));
                    worker.start();
                    worker.join();
                } else {
                    example(-1);
                }
                System.out.println("continued");
                System.exit(41);
            } finally {
                System.out.println("finally-block");
            }
        }
    }
}

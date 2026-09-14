// SPDX-License-Identifier: MIT OR Apache-2.0
package tech.schematic;

import java.lang.annotation.Documented;
import java.lang.annotation.ElementType;
import java.lang.annotation.Retention;
import java.lang.annotation.RetentionPolicy;
import java.lang.annotation.Target;

/**
 * Marks a method as a Schematic supertest: a specification over its typed inputs.
 * This passive marker does not invoke the method or register an ordinary unit test.
 */
@Documented
@Retention(RetentionPolicy.RUNTIME)
@Target(ElementType.METHOD)
public @interface Supertest {
}

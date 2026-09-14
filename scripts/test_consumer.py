#!/usr/bin/env python3
"""Compile against the distributed JAR without Maven or runtime dependencies."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import tempfile

from release import ROOT, VERSION

source = '''import tech.schematic.Supertest;
import static tech.schematic.Assumptions.assume;
public class Consumer {
    @Supertest public static int increment(int value) {
        assume(value >= 0);
        return value + 1;
    }
    public static void main(String[] args) throws Exception {
        if (Consumer.class.getMethod("increment", int.class).getAnnotation(Supertest.class) == null) {
            throw new AssertionError("missing marker");
        }
        if (args.length > 0) {
            increment(-1);
            throw new AssertionError("false assumption continued");
        }
        if (increment(3) != 4) throw new AssertionError("changed behavior");
        System.out.println("accepted");
    }
}
'''


def tool(name: str) -> str:
    if os.environ.get('JAVA_HOME'):
        return str(Path(os.environ['JAVA_HOME']) / 'bin' / (name + ('.exe' if os.name == 'nt' else '')))
    return name


with tempfile.TemporaryDirectory(prefix='supertest-java-consumer-') as directory:
    work = Path(directory)
    (work / 'Consumer.java').write_text(source)
    jar = ROOT / 'dist' / f'schematic-supertest-{VERSION}.jar'
    subprocess.run([tool('javac'), '-cp', str(jar), str(work / 'Consumer.java')], check=True)
    command = [tool('java'), '-ea', '-cp', os.pathsep.join((str(jar), str(work))), 'Consumer']
    for arguments, expected in (([], 'accepted\n'), (['rejected'], '')):
        result = subprocess.run([*command, *arguments], check=True, capture_output=True, text=True, timeout=15)
        assert result.stdout == expected and not result.stderr, result
print('Standalone JAR consumer passed on ' + subprocess.check_output([tool('java'), '-version'], stderr=subprocess.STDOUT, text=True).splitlines()[0])

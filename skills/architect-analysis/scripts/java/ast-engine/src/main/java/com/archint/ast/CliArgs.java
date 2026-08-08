package com.archint.ast;

import java.nio.file.Path;
import java.util.*;

public class CliArgs {
    public final Path source;
    public final Set<String> entrypointFilter;
    public final int maxDepth;
    public final boolean includeTests;

    private CliArgs(Path source, Set<String> entrypointFilter, int maxDepth, boolean includeTests) {
        this.source = source;
        this.entrypointFilter = entrypointFilter;
        this.maxDepth = maxDepth;
        this.includeTests = includeTests;
    }

    public static CliArgs parse(String[] args) {
        Path source = null;
        Set<String> entrypoints = new HashSet<>();
        int depth = Integer.MAX_VALUE;
        boolean includeTests = false;

        for (int i = 0; i < args.length; i++) {
            switch (args[i]) {
                case "--source" -> source = Path.of(args[++i]);
                case "--depth" -> depth = Integer.parseInt(args[++i]);
                case "--include-tests" -> includeTests = true;
                case "--entrypoints" -> {
                    while (i + 1 < args.length && !args[i + 1].startsWith("--"))
                        entrypoints.add(args[++i]);
                }
                case "--format" -> i++; // only json supported, skip value
            }
        }

        if (source == null) {
            System.err.println("ERROR: --source is required");
            System.exit(1);
        }
        if (!source.toFile().isDirectory()) {
            System.err.println("ERROR: --source must be an existing directory: " + source);
            System.exit(1);
        }

        return new CliArgs(source, entrypoints, depth, includeTests);
    }
}

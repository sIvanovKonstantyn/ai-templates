package com.archint.ast;

import spoon.Launcher;
import spoon.compiler.Environment;
import java.util.List;

public class ProjectLoader {

    public static Launcher load(java.nio.file.Path source, boolean includeTests, List<String> errors) {
        Launcher launcher = new Launcher();
        Environment env = launcher.getEnvironment();
        env.setNoClasspath(true);
        env.setAutoImports(false);
        env.setCommentEnabled(false);
        env.setShouldCompile(false);

        launcher.addInputResource(source.toString());

        if (!includeTests) {
            launcher.getEnvironment().setSourceClasspath(new String[0]);
        }

        try {
            launcher.buildModel();
        } catch (Exception e) {
            errors.add("Model build warning: " + e.getMessage());
        }

        return launcher;
    }
}

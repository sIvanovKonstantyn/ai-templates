package com.archint.ast;

import spoon.reflect.declaration.CtType;
import java.util.*;

public class AstEngine {

    public static void main(String[] args) {
        CliArgs cli = CliArgs.parse(args);
        List<String> errors = new ArrayList<>();

        spoon.Launcher launcher = ProjectLoader.load(cli.source, cli.includeTests, errors);
        Collection<CtType<?>> types = launcher.getModel().getAllTypes();

        ComponentClassifier classifier = new ComponentClassifier(types);
        CallGraphBuilder graphBuilder = new CallGraphBuilder(types, classifier);
        graphBuilder.build();

        TransactionAnalyzer txAnalyzer = new TransactionAnalyzer();
        ExternalCallDetector extDetector = new ExternalCallDetector();
        HttpDependencyExtractor httpExtractor = new HttpDependencyExtractor();
        EventDependencyExtractor eventExtractor = new EventDependencyExtractor();
        FlowBuilder flowBuilder = new FlowBuilder(graphBuilder, txAnalyzer, extDetector, httpExtractor, cli.maxDepth);

        List<Map<String, Object>> entrypoints = flowBuilder.buildEntrypoints(
            types, cli.entrypointFilter
        );

        String projectName = cli.source.getFileName() != null ? cli.source.getFileName().toString() : cli.source.toString();

        Map<String, Object> httpDeps = new LinkedHashMap<>();
        httpDeps.put("service", projectName);
        httpDeps.put("dependencies", httpExtractor.extract(types));

        Map<String, Object> eventDeps = new LinkedHashMap<>();
        eventDeps.put("service", projectName);
        eventDeps.put("events", eventExtractor.extract(types));

        Map<String, Object> result = new LinkedHashMap<>();
        result.put("project", projectName);
        result.put("entrypoints", entrypoints);
        result.put("graph", graphBuilder.toJson());
        result.put("httpDependencies", httpDeps);
        result.put("eventDependencies", eventDeps);
        result.put("metadata", Map.of("errors", errors));

        System.out.println(JsonSerializer.toJson(result));
    }
}

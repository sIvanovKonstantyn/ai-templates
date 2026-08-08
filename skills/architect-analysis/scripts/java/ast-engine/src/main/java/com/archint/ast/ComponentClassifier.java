package com.archint.ast;

import spoon.reflect.declaration.CtType;
import spoon.reflect.declaration.CtAnnotation;
import java.util.*;

public class ComponentClassifier {

    private static final Map<String, String> ANNOTATION_TO_TYPE = Map.of(
        "RestController",  "REST_CONTROLLER",
        "Controller",      "CONTROLLER",
        "Service",         "SERVICE",
        "Repository",      "REPOSITORY",
        "Component",       "COMPONENT",
        "Configuration",   "CONFIGURATION"
    );

    private final Map<String, String> typeToComponent = new HashMap<>();

    public ComponentClassifier(Collection<CtType<?>> types) {
        for (CtType<?> type : types) {
            String component = classify(type);
            if (component != null) {
                typeToComponent.put(type.getQualifiedName(), component);
            }
        }
    }

    public String getComponentType(String qualifiedName) {
        return typeToComponent.getOrDefault(qualifiedName, "UNKNOWN");
    }

    public boolean isController(CtType<?> type) {
        String ct = typeToComponent.get(type.getQualifiedName());
        return "REST_CONTROLLER".equals(ct) || "CONTROLLER".equals(ct);
    }

    private String classify(CtType<?> type) {
        for (CtAnnotation<?> ann : type.getAnnotations()) {
            String simpleName = ann.getAnnotationType().getSimpleName();
            String mapped = ANNOTATION_TO_TYPE.get(simpleName);
            if (mapped != null) return mapped;
        }
        return null;
    }
}

package com.archint.ast;

import spoon.reflect.declaration.*;
import spoon.reflect.visitor.filter.TypeFilter;
import spoon.reflect.code.CtInvocation;
import java.util.*;

public class CallGraphBuilder {

    private final Collection<CtType<?>> types;
    private final ComponentClassifier classifier;

    // nodeId -> node map
    private final Map<String, Map<String, Object>> nodes = new LinkedHashMap<>();
    // "from->to" -> edge map (dedup)
    private final Map<String, Map<String, Object>> edges = new LinkedHashMap<>();
    // methodId -> list of callee methodIds
    private final Map<String, List<String>> adjacency = new HashMap<>();

    public CallGraphBuilder(Collection<CtType<?>> types, ComponentClassifier classifier) {
        this.types = types;
        this.classifier = classifier;
    }

    public void build() {
        for (CtType<?> type : types) {
            for (CtMethod<?> method : type.getMethods()) {
                String callerId = methodId(type, method);
                ensureNode(callerId, classifier.getComponentType(type.getQualifiedName()));

                List<CtInvocation<?>> invocations = method.getElements(new TypeFilter<>(CtInvocation.class));
                for (CtInvocation<?> inv : invocations) {
                    try {
                        CtExecutable<?> exec = inv.getExecutable().getDeclaration();
                        if (exec instanceof CtMethod<?> target && target.getDeclaringType() != null) {
                            String calleeId = methodId(target.getDeclaringType(), target);
                            ensureNode(calleeId, classifier.getComponentType(target.getDeclaringType().getQualifiedName()));
                            addEdge(callerId, calleeId);
                        }
                    } catch (Exception ignored) {}
                }
            }
        }
    }

    public List<String> calleesOf(String methodId) {
        return adjacency.getOrDefault(methodId, List.of());
    }

    public Map<String, Object> toJson() {
        Map<String, Object> graph = new LinkedHashMap<>();
        graph.put("nodes", new ArrayList<>(nodes.values()));
        graph.put("edges", new ArrayList<>(edges.values()));
        return graph;
    }

    public String getComponentType(String methodId) {
        Map<String, Object> node = nodes.get(methodId);
        return node != null ? (String) node.get("type") : "UNKNOWN";
    }

    public static String methodId(CtType<?> type, CtMethod<?> method) {
        return type.getSimpleName() + "." + method.getSimpleName();
    }

    private void ensureNode(String id, String componentType) {
        nodes.computeIfAbsent(id, k -> {
            Map<String, Object> n = new LinkedHashMap<>();
            n.put("id", id);
            n.put("type", componentType);
            return n;
        });
    }

    private void addEdge(String from, String to) {
        String key = from + "->" + to;
        if (!edges.containsKey(key)) {
            Map<String, Object> e = new LinkedHashMap<>();
            e.put("from", from);
            e.put("to", to);
            edges.put(key, e);
            adjacency.computeIfAbsent(from, k -> new ArrayList<>()).add(to);
        }
    }
}

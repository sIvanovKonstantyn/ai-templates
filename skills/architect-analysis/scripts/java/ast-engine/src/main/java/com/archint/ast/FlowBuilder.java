package com.archint.ast;

import spoon.reflect.declaration.*;
import spoon.reflect.code.*;
import spoon.reflect.reference.CtFieldReference;
import spoon.reflect.reference.CtTypeReference;
import spoon.reflect.visitor.filter.TypeFilter;
import java.util.*;

public class FlowBuilder {

    private static final Map<String, String> HTTP_MAPPINGS = Map.of(
        "GetMapping",    "GET",
        "PostMapping",   "POST",
        "PutMapping",    "PUT",
        "DeleteMapping", "DELETE",
        "PatchMapping",  "PATCH",
        "RequestMapping","REQUEST"
    );

    private static final Set<String> SCHEDULED_ANNOTATIONS = Set.of(
        "Scheduled", "EventListener", "KafkaListener"
    );

    private static final Set<String> EVENT_CONSUMER_INTERFACES = Set.of(
        "Consumer", "MessageListener", "EventListener"
    );

    private final CallGraphBuilder graph;
    private final TransactionAnalyzer txAnalyzer;
    private final ExternalCallDetector extDetector;
    private final int maxDepth;
    private final Map<String, CtMethod<?>> methodIndex = new HashMap<>();

    public FlowBuilder(CallGraphBuilder graph, TransactionAnalyzer txAnalyzer,
                       ExternalCallDetector extDetector, HttpDependencyExtractor httpExtractor, int maxDepth) {
        this.graph = graph;
        this.txAnalyzer = txAnalyzer;
        this.extDetector = extDetector;
        this.extDetector.setHttpExtractor(httpExtractor);
        this.maxDepth = maxDepth;
    }

    public List<Map<String, Object>> buildEntrypoints(Collection<CtType<?>> types, Set<String> filter) {
        for (CtType<?> type : types)
            for (CtMethod<?> m : type.getMethods())
                methodIndex.put(CallGraphBuilder.methodId(type, m), m);
        List<Map<String, Object>> entrypoints = new ArrayList<>();
        for (CtType<?> type : types) {
            if (!filter.isEmpty() && !filter.contains(type.getSimpleName())) continue;
            for (CtMethod<?> method : type.getMethods()) {
                Map<String, Object> ep = tryBuildEntrypoint(type, method);
                if (ep != null) entrypoints.add(ep);
            }
        }
        return entrypoints;
    }

    private Map<String, Object> tryBuildEntrypoint(CtType<?> type, CtMethod<?> method) {
        for (CtAnnotation<?> ann : method.getAnnotations()) {
            String name = ann.getAnnotationType().getSimpleName();
            if (HTTP_MAPPINGS.containsKey(name)) {
                return buildRestEntrypoint(type, method, ann, name);
            }
            if (SCHEDULED_ANNOTATIONS.contains(name)) {
                return buildSimpleEntrypoint(type, method, name.toUpperCase());
            }
        }
        if (isEventConsumerAccept(type, method)) {
            return buildSimpleEntrypoint(type, method, "EVENT");
        }
        return null;
    }

    private boolean isEventConsumerAccept(CtType<?> type, CtMethod<?> method) {
        if (!"accept".equals(method.getSimpleName())) return false;
        // 1. Direct interface check
        for (CtTypeReference<?> iface : type.getSuperInterfaces()) {
            if (EVENT_CONSUMER_INTERFACES.contains(iface.getSimpleName())) return true;
        }
        // 2. Superclass chain (works when superclass is in source)
        CtTypeReference<?> superRef = type.getSuperclass();
        while (superRef != null) {
            CtType<?> superType = superRef.getTypeDeclaration();
            if (superType == null) break;
            for (CtTypeReference<?> iface : superType.getSuperInterfaces()) {
                if (EVENT_CONSUMER_INTERFACES.contains(iface.getSimpleName())) return true;
            }
            superRef = superType.getSuperclass();
        }
        // 3. Name heuristic fallback: *Consumer classes with accept() are event consumers
        //    Covers cases where the hierarchy is in a dependency JAR (not source)
        return type.getSimpleName().endsWith("Consumer");
    }

    private Map<String, Object> buildRestEntrypoint(CtType<?> type, CtMethod<?> method,
                                                     CtAnnotation<?> ann, String annName) {
        Map<String, Object> ep = new LinkedHashMap<>();
        ep.put("type", "REST");
        ep.put("class", type.getSimpleName());
        ep.put("method", method.getSimpleName());
        ep.put("httpMethod", resolveHttpMethod(ann, annName));
        ep.put("path", extractPath(ann));

        Map<String, Object> tx = txAnalyzer.getTransactionalInfo(method);
        ep.put("transactional", tx != null);
        if (tx != null) tx.forEach(ep::put);

        ep.put("flow", buildFlow(type, method, new HashSet<>(), 0));
        return ep;
    }

    private Map<String, Object> buildSimpleEntrypoint(CtType<?> type, CtMethod<?> method, String epType) {
        Map<String, Object> ep = new LinkedHashMap<>();
        ep.put("type", epType);
        ep.put("class", type.getSimpleName());
        ep.put("method", method.getSimpleName());
        ep.put("flow", buildFlow(type, method, new HashSet<>(), 0));
        return ep;
    }

    private Map<String, Object> buildFlow(CtType<?> type, CtMethod<?> method,
                                           Set<String> visited, int depth) {
        List<Object> steps = new ArrayList<>();
        String nodeId = CallGraphBuilder.methodId(type, method);

        if (depth >= maxDepth || visited.contains(nodeId)) {
            return Map.of("type", "sequence", "steps", steps);
        }
        visited.add(nodeId);

        // External calls
        for (Map<String, Object> ext : extDetector.detect(type, method)) {
            Map<String, Object> step = new LinkedHashMap<>();
            String extType = (String) ext.get("type");
            if ("HTTP".equals(extType)) {
                step.put("call", ext.getOrDefault("targetService", "?") + ":" + ext.getOrDefault("url", "?"));
                step.put("componentType", "HTTP_CLIENT");
                step.put("httpMethod", ext.get("httpMethod"));
                step.put("url", ext.get("url"));
                step.put("targetService", ext.get("targetService"));
                step.put("clientType", ext.get("clientType"));
            } else {
                step.put("externalCall", ext);
            }
            steps.add(step);
        }

        // Structural flow from body
        if (method.getBody() != null) {
            collectStatements(method.getBody().getStatements(), steps, visited, depth);
        }

        // DFS into callees
        for (String calleeId : graph.calleesOf(nodeId)) {
            CtMethod<?> calleeMethod = methodIndex.get(calleeId);
            if (calleeMethod != null && !visited.contains(calleeId)) {
                Map<String, Object> callStep = new LinkedHashMap<>();
                callStep.put("call", calleeId);
                callStep.put("componentType", graph.getComponentType(calleeId));
                callStep.put("flow", buildFlow(calleeMethod.getDeclaringType(), calleeMethod, new HashSet<>(visited), depth + 1));
                steps.add(callStep);
            } else {
                steps.add(Map.of("call", calleeId));
            }
        }

        return Map.of("type", "sequence", "steps", steps);
    }

    private void collectStatements(List<CtStatement> statements, List<Object> steps,
                                    Set<String> visited, int depth) {
        for (CtStatement stmt : statements) {
            if (stmt instanceof CtIf ifStmt) {
                Map<String, Object> branch = new LinkedHashMap<>();
                branch.put("condition", ifStmt.getCondition().toString());
                branch.put("ifTrue", statementsToSteps(blockStatements(ifStmt.getThenStatement()), visited, depth));
                if (ifStmt.getElseStatement() != null) {
                    branch.put("ifFalse", statementsToSteps(blockStatements(ifStmt.getElseStatement()), visited, depth));
                }
                steps.add(branch);
            } else if (stmt instanceof CtTry tryStmt) {
                Map<String, Object> tryBlock = new LinkedHashMap<>();
                tryBlock.put("try", statementsToSteps(tryStmt.getBody().getStatements(), visited, depth));
                List<Object> catches = new ArrayList<>();
                for (CtCatch c : tryStmt.getCatchers()) {
                    catches.add(Map.of("catch", c.getParameter().getType().getSimpleName()));
                }
                if (!catches.isEmpty()) tryBlock.put("catches", catches);
                steps.add(tryBlock);
            } else if (stmt instanceof CtLoop loop) {
                steps.add(Map.of("loop", statementsToSteps(blockStatements(loop.getBody()), visited, depth)));
            }
        }
    }

    private List<Object> statementsToSteps(List<CtStatement> stmts, Set<String> visited, int depth) {
        List<Object> steps = new ArrayList<>();
        collectStatements(stmts, steps, visited, depth + 1);
        return steps;
    }

    private List<CtStatement> blockStatements(CtStatement stmt) {
        if (stmt instanceof CtBlock<?> block) return block.getStatements();
        if (stmt == null) return List.of();
        return List.of(stmt);
    }

    private String resolveHttpMethod(CtAnnotation<?> ann, String annName) {
        if ("RequestMapping".equals(annName)) {
            try {
                var methodVal = ann.getValue("method");
                if (methodVal != null) {
                    List<CtAnnotationFieldAccess<?>> accesses = methodVal.getElements(
                        new TypeFilter<>(CtAnnotationFieldAccess.class));
                    if (!accesses.isEmpty()) return accesses.get(0).getVariable().getSimpleName();
                }
            } catch (Exception ignored) {}
            return "REQUEST";
        }
        return HTTP_MAPPINGS.getOrDefault(annName, "UNKNOWN");
    }

    private String extractPath(CtAnnotation<?> ann) {
        for (String key : List.of("value", "path")) {
            try {
                var expr = ann.getValue(key);
                if (expr == null) continue;
                String resolved = resolveExpression(expr);
                if (resolved != null && !resolved.isBlank()) return resolved;
            } catch (Exception ignored) {}
        }
        return "/";
    }

    /**
     * Recursively resolve an annotation value expression to a concrete string.
     * Handles: string literals, static final constants (CtFieldRead),
     * binary concatenation (+), and array wrappers.
     */
    private String resolveExpression(CtExpression<?> expr) {
        if (expr == null) return null;

        // Unwrap single-element arrays: {"/foo"} → "/foo"
        if (expr instanceof CtNewArray<?> arr) {
            var elements = arr.getElements();
            if (elements.isEmpty()) return "/";
            StringBuilder sb = new StringBuilder();
            for (var el : elements) {
                String v = resolveExpression((CtExpression<?>) el);
                if (v != null) sb.append(v);
            }
            return sb.toString();
        }

        // String literal
        if (expr instanceof CtLiteral<?> lit) {
            Object val = lit.getValue();
            return val != null ? val.toString() : null;
        }

        // Binary operator (string concatenation: "a" + "b")
        if (expr instanceof CtBinaryOperator<?> binOp) {
            String left = resolveExpression(binOp.getLeftHandOperand());
            String right = resolveExpression(binOp.getRightHandOperand());
            if (left != null && right != null) return left + right;
            if (left != null) return left;
            return right;
        }

        // Field read — resolve static final String constants
        if (expr instanceof CtFieldRead<?> fieldRead) {
            return resolveFieldConstant(fieldRead);
        }

        // Fallback: strip quotes and braces from toString()
        String raw = expr.toString().replaceAll("[{}\"]", "").trim();
        return raw.isEmpty() ? null : raw;
    }

    /**
     * Attempt to resolve a CtFieldRead to its compile-time constant value.
     * Works for: static final String FIELD = "value" and static final String FIELD = OTHER + "/suffix"
     */
    private String resolveFieldConstant(CtFieldRead<?> fieldRead) {
        try {
            CtFieldReference<?> ref = fieldRead.getVariable();
            if (ref == null) return fieldRead.toString();
            CtField<?> field = ref.getFieldDeclaration();
            if (field == null) return fieldRead.toString();
            // Must be static final
            if (!field.isStatic() || !field.isFinal()) return fieldRead.toString();
            CtExpression<?> init = field.getDefaultExpression();
            if (init == null) return fieldRead.toString();
            return resolveExpression(init);
        } catch (Exception e) {
            return fieldRead.toString();
        }
    }
}

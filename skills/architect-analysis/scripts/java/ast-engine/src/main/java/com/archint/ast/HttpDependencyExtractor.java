package com.archint.ast;

import spoon.reflect.code.*;
import spoon.reflect.declaration.*;
import spoon.reflect.visitor.filter.TypeFilter;
import java.util.*;

public class HttpDependencyExtractor {

    // RestTemplate methods -> HTTP method
    private static final Map<String, String> REST_TEMPLATE_METHODS = Map.of(
        "getForObject",   "GET",
        "getForEntity",   "GET",
        "postForObject",  "POST",
        "postForEntity",  "POST",
        "exchange",       "EXCHANGE"
    );

    // Apache/OkHttp constructor names -> HTTP method
    private static final Map<String, String> HTTP_CONSTRUCTORS = Map.of(
        "HttpGet",    "GET",
        "HttpPost",   "POST",
        "HttpPut",    "PUT",
        "HttpDelete", "DELETE",
        "HttpPatch",  "PATCH"
    );

    private static final Map<String, String> WEBCLIENT_HTTP_METHODS = Map.of(
        "get", "GET", "post", "POST", "put", "PUT",
        "delete", "DELETE", "patch", "PATCH"
    );

    public List<Map<String, Object>> extract(Collection<CtType<?>> types) {
        List<Map<String, Object>> deps = new ArrayList<>();
        for (CtType<?> type : types) {
            for (CtMethod<?> method : type.getMethods()) {
                deps.addAll(extractFromMethod(type, method));
            }
            deps.addAll(extractFeignClient(type));
        }
        return deps;
    }

    public List<Map<String, Object>> extractFromMethod(CtType<?> type, CtMethod<?> method) {
        List<Map<String, Object>> deps = new ArrayList<>();
        String sourceClass = type.getSimpleName();
        String sourceMethod = method.getSimpleName();

        for (CtInvocation<?> inv : method.getElements(new TypeFilter<>(CtInvocation.class))) {
            try {
                String targetType = inv.getExecutable().getDeclaringType().getSimpleName();
                String methodName = inv.getExecutable().getSimpleName();

                if (targetType.contains("RestTemplate") && REST_TEMPLATE_METHODS.containsKey(methodName)) {
                    deps.add(buildRestTemplateDep(sourceClass, sourceMethod, methodName, inv));
                } else if (targetType.contains("WebClient") || targetType.contains("RequestBodySpec")
                        || targetType.contains("RequestHeadersSpec") || targetType.contains("RequestHeadersUriSpec")) {
                    Map<String, Object> dep = tryExtractWebClientChain(sourceClass, sourceMethod, inv);
                    if (dep != null) deps.add(dep);
                }
            } catch (Exception ignored) {}
        }

        for (CtConstructorCall<?> ctor : method.getElements(new TypeFilter<>(CtConstructorCall.class))) {
            try {
                String ctorName = ctor.getType().getSimpleName();
                String httpMethod = HTTP_CONSTRUCTORS.get(ctorName);
                if (httpMethod != null) {
                    Map<String, Object> dep = new LinkedHashMap<>();
                    dep.put("sourceClass", sourceClass);
                    dep.put("sourceMethod", sourceMethod);
                    dep.put("clientType", ctorName.startsWith("Http") ? "ApacheHttpClient" : "OkHttp");
                    dep.put("httpMethod", httpMethod);
                    dep.put("url", resolveUrl(ctor.getArguments().isEmpty() ? null : ctor.getArguments().get(0)));
                    dep.put("targetService", null);
                    dep.put("line", ctor.getPosition().isValidPosition() ? ctor.getPosition().getLine() : -1);
                    deps.add(dep);
                }
            } catch (Exception ignored) {}
        }

        return deps;
    }

    private Map<String, Object> buildRestTemplateDep(String sourceClass, String sourceMethod,
                                                      String methodName, CtInvocation<?> inv) {
        List<CtExpression<?>> args = inv.getArguments();
        String url = args.isEmpty() ? "?" : resolveUrl(args.get(0));
        String httpMethod = REST_TEMPLATE_METHODS.get(methodName);

        // exchange() may have HttpMethod as 2nd arg
        if ("EXCHANGE".equals(httpMethod) && args.size() >= 2) {
            httpMethod = resolveExchangeMethod(args.get(1));
        }

        Map<String, Object> dep = new LinkedHashMap<>();
        dep.put("sourceClass", sourceClass);
        dep.put("sourceMethod", sourceMethod);
        dep.put("clientType", "RestTemplate");
        dep.put("httpMethod", httpMethod);
        dep.put("url", url);
        dep.put("targetService", extractServiceFromUrl(url));
        dep.put("line", inv.getPosition().isValidPosition() ? inv.getPosition().getLine() : -1);
        return dep;
    }

    /**
     * Walks up the invocation chain to find .post()/.get() etc. and .uri() on a WebClient.
     * Returns a dep only when we find a WebClient HTTP-method call in the chain.
     */
    private Map<String, Object> tryExtractWebClientChain(String sourceClass, String sourceMethod,
                                                          CtInvocation<?> inv) {
        String methodName = inv.getExecutable().getSimpleName();
        if (!WEBCLIENT_HTTP_METHODS.containsKey(methodName)) return null;

        // Found .get()/.post() etc. — now look for .uri() in the same chain
        String httpMethod = WEBCLIENT_HTTP_METHODS.get(methodName);
        String uri = findUriInChain(inv);

        Map<String, Object> dep = new LinkedHashMap<>();
        dep.put("sourceClass", sourceClass);
        dep.put("sourceMethod", sourceMethod);
        dep.put("clientType", "WebClient");
        dep.put("httpMethod", httpMethod);
        dep.put("url", uri != null ? uri : "?");
        dep.put("targetService", uri != null ? extractServiceFromUrl(uri) : null);
        dep.put("line", inv.getPosition().isValidPosition() ? inv.getPosition().getLine() : -1);
        return dep;
    }

    private String findUriInChain(CtInvocation<?> root) {
        // Walk parent chain looking for .uri(...)
        CtElement current = root.getParent();
        while (current != null) {
            if (current instanceof CtInvocation<?> parent) {
                if ("uri".equals(parent.getExecutable().getSimpleName()) && !parent.getArguments().isEmpty()) {
                    return resolveUrl(parent.getArguments().get(0));
                }
            }
            current = current.getParent();
        }
        return null;
    }

    private List<Map<String, Object>> extractFeignClient(CtType<?> type) {
        List<Map<String, Object>> deps = new ArrayList<>();
        if (!type.isInterface()) return deps;

        String feignServiceName = null;
        for (CtAnnotation<?> ann : type.getAnnotations()) {
            if ("FeignClient".equals(ann.getAnnotationType().getSimpleName())) {
                feignServiceName = extractAnnotationString(ann, "name", "value");
                break;
            }
        }
        if (feignServiceName == null) return deps;

        for (CtMethod<?> method : type.getMethods()) {
            for (CtAnnotation<?> ann : method.getAnnotations()) {
                String annName = ann.getAnnotationType().getSimpleName();
                String httpMethod = resolveHttpMethodFromMappingAnnotation(annName);
                if (httpMethod == null) continue;

                String path = extractAnnotationString(ann, "value", "path");
                Map<String, Object> dep = new LinkedHashMap<>();
                dep.put("sourceClass", type.getSimpleName());
                dep.put("sourceMethod", method.getSimpleName());
                dep.put("clientType", "FeignClient");
                dep.put("httpMethod", httpMethod);
                dep.put("url", path != null ? path : "?");
                dep.put("targetService", feignServiceName);
                dep.put("line", method.getPosition().isValidPosition() ? method.getPosition().getLine() : -1);
                deps.add(dep);
            }
        }
        return deps;
    }

    // ── URL resolution ────────────────────────────────────────────────────────

    String resolveUrl(CtExpression<?> expr) {
        if (expr == null) return "?";
        if (expr instanceof CtLiteral<?> lit) {
            Object val = lit.getValue();
            return val != null ? val.toString() : "?";
        }
        if (expr instanceof CtBinaryOperator<?> bin) {
            return resolveUrl(bin.getLeftHandOperand()) + resolveUrl(bin.getRightHandOperand());
        }
        if (expr instanceof CtFieldRead<?> fr) {
            // Try to resolve constant value
            try {
                CtField<?> field = fr.getVariable().getFieldDeclaration();
                if (field != null && field.getDefaultExpression() != null) {
                    return resolveUrl(field.getDefaultExpression());
                }
            } catch (Exception ignored) {}
            return fr.getVariable().getSimpleName();
        }
        // Preserve raw expression for dynamic/config values
        String raw = expr.toString();
        return raw.length() > 200 ? raw.substring(0, 200) + "..." : raw;
    }

    String extractServiceFromUrl(String url) {
        if (url == null || url.startsWith("${") || url.equals("?")) return null;
        try {
            // http://service-name/path or //service-name/path
            String stripped = url.replaceFirst("^https?://", "");
            if (stripped.contains("/")) {
                String host = stripped.substring(0, stripped.indexOf('/'));
                if (!host.isEmpty() && !host.contains("$") && !host.contains("{")) return host;
            }
        } catch (Exception ignored) {}
        return null;
    }

    private String resolveExchangeMethod(CtExpression<?> expr) {
        String raw = expr.toString();
        for (String m : List.of("GET", "POST", "PUT", "DELETE", "PATCH")) {
            if (raw.contains(m)) return m;
        }
        return raw;
    }

    private String resolveHttpMethodFromMappingAnnotation(String annName) {
        return switch (annName) {
            case "GetMapping"    -> "GET";
            case "PostMapping"   -> "POST";
            case "PutMapping"    -> "PUT";
            case "DeleteMapping" -> "DELETE";
            case "PatchMapping"  -> "PATCH";
            case "RequestMapping"-> "REQUEST";
            default -> null;
        };
    }

    private String extractAnnotationString(CtAnnotation<?> ann, String... keys) {
        for (String key : keys) {
            try {
                var expr = ann.getValue(key);
                if (expr == null) continue;
                String raw = expr.toString().replaceAll("[{}\"\\s]", "");
                if (!raw.isEmpty()) return raw;
            } catch (Exception ignored) {}
        }
        return null;
    }
}

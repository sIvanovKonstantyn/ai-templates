package com.archint.ast;

import spoon.reflect.code.CtInvocation;
import spoon.reflect.declaration.CtMethod;
import spoon.reflect.declaration.CtType;
import spoon.reflect.visitor.filter.TypeFilter;
import java.util.*;

public class ExternalCallDetector {

    private static final Map<String, String> NON_HTTP_PATTERNS = new LinkedHashMap<>();

    static {
        NON_HTTP_PATTERNS.put("KafkaTemplate",            "KAFKA");
        NON_HTTP_PATTERNS.put("JmsTemplate",              "JMS");
        NON_HTTP_PATTERNS.put("ApplicationEventPublisher","EVENT");
        NON_HTTP_PATTERNS.put("EventBus",                 "EVENT");
    }

    private HttpDependencyExtractor httpExtractor;

    public void setHttpExtractor(HttpDependencyExtractor httpExtractor) {
        this.httpExtractor = httpExtractor;
    }

    public List<Map<String, Object>> detect(CtType<?> type, CtMethod<?> method) {
        List<Map<String, Object>> result = new ArrayList<>();

        // HTTP calls — enriched via HttpDependencyExtractor
        if (httpExtractor != null) {
            for (Map<String, Object> dep : httpExtractor.extractFromMethod(type, method)) {
                Map<String, Object> call = new LinkedHashMap<>();
                call.put("type", "HTTP");
                call.put("clientType", dep.get("clientType"));
                call.put("httpMethod", dep.get("httpMethod"));
                call.put("url", dep.get("url"));
                call.put("targetService", dep.get("targetService"));
                result.add(call);
            }
        }

        // Non-HTTP external calls
        for (CtInvocation<?> inv : method.getElements(new TypeFilter<>(CtInvocation.class))) {
            try {
                String targetType = inv.getExecutable().getDeclaringType().getSimpleName();
                for (Map.Entry<String, String> entry : NON_HTTP_PATTERNS.entrySet()) {
                    if (targetType.contains(entry.getKey())) {
                        Map<String, Object> call = new LinkedHashMap<>();
                        call.put("type", entry.getValue());
                        call.put("target", targetType);
                        result.add(call);
                        break;
                    }
                }
            } catch (Exception ignored) {}
        }
        return result;
    }
}

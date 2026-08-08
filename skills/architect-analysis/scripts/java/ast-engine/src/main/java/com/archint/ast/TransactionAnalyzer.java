package com.archint.ast;

import spoon.reflect.declaration.*;
import spoon.reflect.code.CtAnnotationFieldAccess;
import spoon.reflect.visitor.filter.TypeFilter;
import java.util.*;
import spoon.reflect.declaration.CtElement;

public class TransactionAnalyzer {

    public Map<String, Object> getTransactionalInfo(CtMethod<?> method) {
        CtAnnotation<?> ann = findTransactional(method);
        if (ann == null) ann = findTransactional(method.getDeclaringType());
        if (ann == null) return null;

        Map<String, Object> tx = new LinkedHashMap<>();
        tx.put("transactional", true);

        String propagation = extractEnumValue(ann, "propagation");
        if (propagation != null) tx.put("propagation", propagation);

        Object readOnly = extractValue(ann, "readOnly");
        if (readOnly != null) tx.put("readOnly", readOnly);

        return tx;
    }

    private CtAnnotation<?> findTransactional(CtElement element) {
        for (CtAnnotation<?> ann : element.getAnnotations()) {
            String name = ann.getAnnotationType().getSimpleName();
            if ("Transactional".equals(name)) return ann;
        }
        return null;
    }

    private String extractEnumValue(CtAnnotation<?> ann, String key) {
        try {
            var expr = ann.getValue(key);
            if (expr == null) return null;
            List<CtAnnotationFieldAccess<?>> accesses = expr.getElements(new TypeFilter<>(CtAnnotationFieldAccess.class));
            if (!accesses.isEmpty()) return accesses.get(0).getVariable().getSimpleName();
        } catch (Exception ignored) {}
        return null;
    }

    private Object extractValue(CtAnnotation<?> ann, String key) {
        try {
            var expr = ann.getValue(key);
            if (expr == null) return null;
            return expr.toString();
        } catch (Exception ignored) {}
        return null;
    }
}

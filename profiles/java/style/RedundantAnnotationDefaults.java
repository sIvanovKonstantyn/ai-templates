import com.sun.source.tree.AnnotationTree;
import com.sun.source.tree.AssignmentTree;
import com.sun.source.tree.CompilationUnitTree;
import com.sun.source.tree.ExpressionTree;
import com.sun.source.tree.IdentifierTree;
import com.sun.source.tree.Tree;
import com.sun.source.util.JavacTask;
import com.sun.source.util.TreePath;
import com.sun.source.util.TreePathScanner;
import com.sun.source.util.Trees;

import javax.lang.model.element.AnnotationMirror;
import javax.lang.model.element.AnnotationValue;
import javax.lang.model.element.Element;
import javax.lang.model.element.ExecutableElement;
import javax.lang.model.element.VariableElement;
import javax.lang.model.type.TypeMirror;
import javax.lang.model.util.Types;
import javax.tools.JavaCompiler;
import javax.tools.StandardJavaFileManager;
import javax.tools.ToolProvider;
import java.io.File;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Objects;

public class RedundantAnnotationDefaults {

    public static void main(String[] args) throws Exception {
        String classpath = Files.readString(Path.of(args[0])).trim();
        String root = Path.of("").toAbsolutePath() + File.separator;
        List<File> files = new ArrayList<>();
        for (int i = 1; i < args.length; i++) {
            files.add(new File(args[i]));
        }
        JavaCompiler compiler = ToolProvider.getSystemJavaCompiler();
        StandardJavaFileManager fileManager = compiler.getStandardFileManager(null, null, null);
        List<String> options = List.of("-proc:none", "-classpath", classpath, "-Xlint:none", "-nowarn");
        JavacTask task = (JavacTask) compiler.getTask(null, fileManager, diagnostic -> { },
                options, null, fileManager.getJavaFileObjectsFromFiles(files));
        Iterable<? extends CompilationUnitTree> units = task.parse();
        task.analyze();
        Trees trees = Trees.instance(task);
        Types types = task.getTypes();
        List<String> findings = new ArrayList<>();
        for (CompilationUnitTree unit : units) {
            String name = unit.getSourceFile().toUri().getPath().replace(root, "");
            new TreePathScanner<Void, Void>() {
                @Override
                public Void visitAnnotation(AnnotationTree annotation, Void unused) {
                    check(getCurrentPath(), annotation, unit, name, trees, types, findings);
                    return super.visitAnnotation(annotation, unused);
                }
            }.scan(unit, null);
        }
        findings.forEach(System.out::println);
    }

    private static void check(TreePath path, AnnotationTree annotation, CompilationUnitTree unit, String name,
                              Trees trees, Types types, List<String> findings) {
        TreePath owner = path.getParentPath() == null ? null : path.getParentPath().getParentPath();
        Element element = owner == null ? null : trees.getElement(owner);
        TypeMirror annotationType = trees.getTypeMirror(new TreePath(path, annotation.getAnnotationType()));
        if (element == null || annotationType == null) {
            return;
        }
        for (AnnotationMirror mirror : element.getAnnotationMirrors()) {
            if (!types.isSameType(mirror.getAnnotationType(), annotationType)) {
                continue;
            }
            Map<? extends ExecutableElement, ? extends AnnotationValue> explicit = mirror.getElementValues();
            for (ExpressionTree argument : annotation.getArguments()) {
                String attribute = attributeName(argument);
                explicit.forEach((method, value) -> {
                    AnnotationValue fallback = method.getDefaultValue();
                    if (method.getSimpleName().contentEquals(attribute) && fallback != null && same(value, fallback, types)) {
                        long line = unit.getLineMap().getLineNumber(trees.getSourcePositions().getStartPosition(unit, argument));
                        findings.add("%s:%d RedundantAnnotationDefault @%s(%s) restates the default value"
                                .formatted(name, line, mirror.getAnnotationType().asElement().getSimpleName(), attribute));
                    }
                });
            }
            return;
        }
    }

    private static String attributeName(ExpressionTree argument) {
        if (argument.getKind() == Tree.Kind.ASSIGNMENT
                && ((AssignmentTree) argument).getVariable() instanceof IdentifierTree identifier) {
            return identifier.getName().toString();
        }
        return "value";
    }

    private static boolean same(AnnotationValue left, AnnotationValue right, Types types) {
        Object a = left.getValue();
        Object b = right.getValue();
        if (a instanceof List<?> first && b instanceof List<?> second) {
            if (first.size() != second.size()) {
                return false;
            }
            for (int i = 0; i < first.size(); i++) {
                if (!same((AnnotationValue) first.get(i), (AnnotationValue) second.get(i), types)) {
                    return false;
                }
            }
            return true;
        }
        if (a instanceof TypeMirror first && b instanceof TypeMirror second) {
            return types.isSameType(first, second);
        }
        if (a instanceof VariableElement first && b instanceof VariableElement second) {
            return first.getSimpleName().contentEquals(second.getSimpleName())
                    && Objects.equals(first.getEnclosingElement(), second.getEnclosingElement());
        }
        if (a instanceof AnnotationMirror || b instanceof AnnotationMirror) {
            return Objects.equals(a.toString(), b.toString());
        }
        return Objects.equals(a, b);
    }
}

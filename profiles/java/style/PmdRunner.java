import net.sourceforge.pmd.PMDConfiguration;
import net.sourceforge.pmd.PmdAnalysis;
import net.sourceforge.pmd.lang.LanguageRegistry;
import net.sourceforge.pmd.reporting.Report;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;

public class PmdRunner {

    public static void main(String[] args) throws Exception {
        Path root = Path.of("").toAbsolutePath();
        PMDConfiguration configuration = new PMDConfiguration();
        configuration.setDefaultLanguageVersion(LanguageRegistry.PMD.getLanguageById("java").getLatestVersion());
        configuration.addRuleSet(args[0]);
        configuration.prependAuxClasspath(Files.readString(Path.of(args[1])).trim());
        configuration.setAnalysisCacheLocation(args[2]);
        for (int i = 3; i < args.length; i++) {
            configuration.addInputPath(Path.of(args[i]));
        }
        List<String> findings = new ArrayList<>();
        try (PmdAnalysis analysis = PmdAnalysis.create(configuration)) {
            Report report = analysis.performAnalysisAndCollectReport();
            report.getViolations().forEach(violation -> findings.add("%s:%d %s %s".formatted(
                    relative(root, violation.getFileId().getAbsolutePath()), violation.getBeginLine(),
                    violation.getRule().getName(), violation.getDescription().replaceAll("\\s+", " "))));
            report.getProcessingErrors().forEach(error -> findings.add("%s:0 PMDProcessingError %s".formatted(
                    relative(root, error.getFileId().getAbsolutePath()), String.valueOf(error.getMsg()).lines().findFirst().orElse(""))));
            report.getConfigurationErrors().forEach(error -> findings.add("pmd/ruleset.xml:0 PMDConfigurationError %s"
                    .formatted(error.issue())));
        }
        findings.forEach(System.out::println);
    }

    private static String relative(Path root, String path) {
        Path file = Path.of(path);
        return file.startsWith(root) ? root.relativize(file).toString() : path;
    }
}

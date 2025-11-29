import * as vscode from 'vscode';
import { ApiClient } from '../services/apiClient';
import { StatusBarManager } from '../ui/statusBar';

export class PRAnalysisCommand {
    constructor(private apiClient: ApiClient, private statusBar: StatusBarManager) { }

    async execute(context: vscode.ExtensionContext) {
        try {
            // Try to get git diff
            const gitExtension = vscode.extensions.getExtension('vscode.git');
            if (!gitExtension?.isActive) {
                vscode.window.showWarningMessage('Git extension not available');
                return;
            }

            this.statusBar.show('Analyzing PR...', 'info');

            // Create sample diff (in production, would get from git)
            const sampleDiff = `
diff --git a/src/test.py b/src/test.py
index 1234567..abcdefg 100644
--- a/src/test.py
+++ b/src/test.py
@@ -1,5 +1,10 @@
def calculate(x, y):
-    return x + y
+    result = x + y
+    for i in range(1000000):  # Performance issue!
+        pass
+    return result
			`;

            const result = await this.apiClient.analyzePR(sampleDiff);

            // Show results in output channel
            const outputChannel = vscode.window.createOutputChannel('AI Agent - PR Analysis');
            outputChannel.clear();
            outputChannel.appendLine('📋 PR Analysis Results\n');

            if (result.security_issues && result.security_issues.length > 0) {
                outputChannel.appendLine('🔒 Security Issues:');
                result.security_issues.forEach((issue) => outputChannel.appendLine(`  • ${issue}`));
                outputChannel.appendLine('');
            }

            if (result.performance_issues && result.performance_issues.length > 0) {
                outputChannel.appendLine('⚡ Performance Issues:');
                result.performance_issues.forEach((issue) => outputChannel.appendLine(`  • ${issue}`));
                outputChannel.appendLine('');
            }

            if (result.quality_issues && result.quality_issues.length > 0) {
                outputChannel.appendLine('📊 Quality Issues:');
                result.quality_issues.forEach((issue) => outputChannel.appendLine(`  • ${issue}`));
                outputChannel.appendLine('');
            }

            outputChannel.show();
            this.statusBar.show('✅ PR analysis complete', 'success');
        } catch (error) {
            vscode.window.showErrorMessage(`PR analysis failed: ${error}`);
            this.statusBar.show('❌ PR analysis failed', 'error');
        }
    }
}

import * as vscode from 'vscode';
import { ApiClient } from '../services/apiClient';
import { StatusBarManager } from '../ui/statusBar';

export class TestGenerationCommand {
    constructor(private apiClient: ApiClient, private statusBar: StatusBarManager) { }

    async execute(context: vscode.ExtensionContext) {
        const editor = vscode.window.activeTextEditor;
        if (!editor) {
            vscode.window.showWarningMessage('No active editor found');
            return;
        }

        this.statusBar.show('Generating tests...', 'info');

        try {
            const code = editor.document.getText();
            const language = editor.document.languageId;

            const result = await this.apiClient.generateTests(code, language);

            // Show in new document
            const doc = await vscode.workspace.openTextDocument({
                language: language === 'python' ? 'python' : 'javascript',
                content: result.test_code
            });

            const column = editor.viewColumn ? editor.viewColumn + 1 : vscode.ViewColumn.Beside;
            await vscode.window.showTextDocument(doc, column);

            // Show message
            vscode.window.showInformationMessage(
                `✅ Generated ${result.test_count} tests for ${result.functions_tested.join(', ')}`
            );

            this.statusBar.show(`✅ Generated ${result.test_count} tests`, 'success');
        } catch (error) {
            vscode.window.showErrorMessage(`Test generation failed: ${error}`);
            this.statusBar.show('❌ Test generation failed', 'error');
        }
    }
}

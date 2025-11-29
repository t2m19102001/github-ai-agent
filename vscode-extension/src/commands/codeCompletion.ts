import * as vscode from 'vscode';
import { ApiClient } from '../services/apiClient';
import { StatusBarManager } from '../ui/statusBar';

export class CodeCompletionCommand {
    constructor(private apiClient: ApiClient, private statusBar: StatusBarManager) { }

    async execute(context: vscode.ExtensionContext) {
        const editor = vscode.window.activeTextEditor;
        if (!editor) {
            vscode.window.showWarningMessage('No active editor found');
            return;
        }

        const position = editor.selection.active;
        const codeBefore = editor.document.getText(
            new vscode.Range(new vscode.Position(0, 0), position)
        );

        this.statusBar.show('Getting completions...', 'info');

        try {
            const suggestions = await this.apiClient.getCompletion(
                codeBefore,
                '',
                editor.document.languageId,
                editor.document.fileName
            );

            if (suggestions.length === 0) {
                vscode.window.showInformationMessage('No suggestions available');
                this.statusBar.show('✨ AI Agent Ready', 'success');
                return;
            }

            // Show quick pick
            const selectedSuggestion = await vscode.window.showQuickPick(
                suggestions.map((s, i) => ({
                    label: `${i + 1}. ${s.text.split('\n')[0].substring(0, 50)}...`,
                    description: `Confidence: ${(s.confidence * 100).toFixed(0)}%`,
                    detail: s.text,
                    suggestion: s
                })),
                {
                    placeHolder: 'Select a completion suggestion'
                }
            );

            if (selectedSuggestion) {
                // Insert suggestion
                const insertPosition = new vscode.Position(position.line, position.character);
                await editor.edit((editBuilder) => {
                    editBuilder.insert(insertPosition, selectedSuggestion.detail);
                });

                this.statusBar.show('✨ Suggestion inserted', 'success');
            }
        } catch (error) {
            vscode.window.showErrorMessage(`Completion error: ${error}`);
            this.statusBar.show('❌ Completion failed', 'error');
        }
    }
}

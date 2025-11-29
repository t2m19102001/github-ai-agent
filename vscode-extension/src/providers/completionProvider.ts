import * as vscode from 'vscode';
import { ApiClient } from '../services/apiClient';

export class CodeCompletionProvider implements vscode.CompletionItemProvider {
    constructor(private apiClient: ApiClient) { }

    async provideCompletionItems(
        document: vscode.TextDocument,
        position: vscode.Position,
        token: vscode.CancellationToken,
        context: vscode.CompletionContext
    ): Promise<vscode.CompletionItem[]> {
        // Check if auto-complete is enabled
        const enabled = vscode.workspace
            .getConfiguration('github-ai-agent')
            .get('enableAutoComplete', true);

        if (!enabled) {
            return [];
        }

        try {
            const codeBefore = document.getText(
                new vscode.Range(new vscode.Position(0, 0), position)
            );

            // Don't trigger on every keystroke
            if (codeBefore.length < 10) {
                return [];
            }

            const suggestions = await this.apiClient.getCompletion(
                codeBefore,
                '',
                document.languageId,
                document.fileName
            );

            return suggestions.map((suggestion, index) => {
                const item = new vscode.CompletionItem(
                    suggestion.text.split('\n')[0].substring(0, 50),
                    this.getKind(suggestion.type)
                );

                item.detail = `Confidence: ${(suggestion.confidence * 100).toFixed(0)}%`;
                item.documentation = suggestion.text;
                item.insertText = suggestion.text;
                item.range = new vscode.Range(position, position);
                item.sortText = String(1000 - index); // Sort by confidence

                return item;
            });
        } catch (error) {
            console.error('Completion provider error:', error);
            return [];
        }
    }

    private getKind(type: string): vscode.CompletionItemKind {
        switch (type) {
            case 'function':
                return vscode.CompletionItemKind.Function;
            case 'method':
                return vscode.CompletionItemKind.Method;
            case 'class':
                return vscode.CompletionItemKind.Class;
            case 'import':
                return vscode.CompletionItemKind.Module;
            default:
                return vscode.CompletionItemKind.Variable;
        }
    }
}

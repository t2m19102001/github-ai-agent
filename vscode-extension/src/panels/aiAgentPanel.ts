import * as vscode from 'vscode';
import { ApiClient } from '../services/apiClient';

export class AIAgentPanel implements vscode.WebviewViewProvider {
    public static readonly viewType = 'github-ai-agent-panel';
    private view?: vscode.WebviewView;

    constructor(
        private extensionUri: vscode.Uri,
        private apiClient: ApiClient
    ) { }

    public resolveWebviewView(
        webviewView: vscode.WebviewView,
        context: vscode.WebviewViewResolveContext,
        token: vscode.CancellationToken
    ) {
        this.view = webviewView;

        webviewView.webview.options = {
            enableScripts: true,
            localResourceRoots: [this.extensionUri]
        };

        webviewView.webview.html = this.getHtmlContent(webviewView.webview);

        // Handle messages from webview
        webviewView.webview.onDidReceiveMessage((message) => {
            this.handleMessage(message);
        });
    }

    private handleMessage(message: any) {
        switch (message.command) {
            case 'generateTests':
                this.handleGenerateTests();
                break;
            case 'analyzePR':
                this.handleAnalyzePR();
                break;
            case 'completeCode':
                this.handleCompleteCode();
                break;
            case 'openSettings':
                vscode.commands.executeCommand('github-ai-agent.openSettings');
                break;
        }
    }

    private async handleGenerateTests() {
        const editor = vscode.window.activeTextEditor;
        if (!editor) {
            vscode.window.showWarningMessage('No active editor');
            return;
        }

        try {
            const code = editor.document.getText();
            const language = editor.document.languageId;

            this.view?.webview.postMessage({
                type: 'status',
                message: 'Generating tests...'
            });

            const result = await this.apiClient.generateTests(code, language);

            this.view?.webview.postMessage({
                type: 'testResult',
                data: result
            });

            // Show preview
            const doc = await vscode.workspace.openTextDocument({
                language: language,
                content: result.test_code
            });

            await vscode.window.showTextDocument(doc, { preview: true });
        } catch (error) {
            vscode.window.showErrorMessage(`Test generation failed: ${error}`);
        }
    }

    private async handleAnalyzePR() {
        vscode.commands.executeCommand('github-ai-agent.analyzePR');
    }

    private async handleCompleteCode() {
        const editor = vscode.window.activeTextEditor;
        if (!editor) {
            vscode.window.showWarningMessage('No active editor');
            return;
        }

        const position = editor.selection.active;
        const codeBefore = editor.document.getText(
            new vscode.Range(new vscode.Position(0, 0), position)
        );

        try {
            this.view?.webview.postMessage({
                type: 'status',
                message: 'Getting completions...'
            });

            const suggestions = await this.apiClient.getCompletion(
                codeBefore,
                '',
                editor.document.languageId
            );

            this.view?.webview.postMessage({
                type: 'completionResult',
                data: suggestions
            });
        } catch (error) {
            vscode.window.showErrorMessage(`Completion failed: ${error}`);
        }
    }

    private getHtmlContent(webview: vscode.Webview): string {
        const styleUri = webview.asWebviewUri(
            vscode.Uri.joinPath(this.extensionUri, 'resources', 'panel.css')
        );

        return `<!DOCTYPE html>
<html lang="en">
<head>
	<meta charset="UTF-8">
	<meta name="viewport" content="width=device-width, initial-scale=1.0">
	<title>GitHub AI Agent</title>
	<link rel="stylesheet" href="${styleUri}">
	<style>
		body {
			padding: 10px;
			font-family: var(--vscode-font-family);
			font-size: var(--vscode-font-size);
		}
		.container {
			display: flex;
			flex-direction: column;
			gap: 10px;
		}
		.header {
			font-size: 18px;
			font-weight: bold;
			color: var(--vscode-foreground);
			margin-bottom: 10px;
		}
		.button {
			background-color: var(--vscode-button-background);
			color: var(--vscode-button-foreground);
			border: none;
			padding: 8px 16px;
			border-radius: 4px;
			cursor: pointer;
			font-size: 14px;
			display: flex;
			align-items: center;
			gap: 8px;
			transition: background-color 0.2s;
		}
		.button:hover {
			background-color: var(--vscode-button-hoverBackground);
		}
		.button-group {
			display: flex;
			flex-direction: column;
			gap: 8px;
		}
		.status {
			padding: 8px;
			border-radius: 4px;
			margin-top: 10px;
			font-size: 12px;
		}
		.status.success {
			background-color: rgba(76, 175, 80, 0.2);
			color: #4caf50;
		}
		.status.error {
			background-color: rgba(244, 67, 54, 0.2);
			color: #f44336;
		}
		.status.info {
			background-color: rgba(33, 150, 243, 0.2);
			color: #2196f3;
		}
		.section {
			margin-bottom: 15px;
			border-bottom: 1px solid var(--vscode-widget-border);
			padding-bottom: 10px;
		}
		.section:last-child {
			border-bottom: none;
		}
		.section-title {
			font-weight: bold;
			margin-bottom: 8px;
			color: var(--vscode-textLink-foreground);
		}
		.info-text {
			font-size: 12px;
			color: var(--vscode-descriptionForeground);
			margin-top: 5px;
		}
	</style>
</head>
<body>
	<div class="container">
		<div class="header">🤖 GitHub AI Agent</div>
		
		<div class="section">
			<div class="section-title">Code Completion</div>
			<p class="info-text">Get intelligent code suggestions</p>
			<div class="button-group">
				<button class="button" id="completeBtn">
					<span>💡 Complete Code</span>
				</button>
			</div>
		</div>

		<div class="section">
			<div class="section-title">Test Generation</div>
			<p class="info-text">Automatically generate unit tests</p>
			<div class="button-group">
				<button class="button" id="testBtn">
					<span>🧪 Generate Tests</span>
				</button>
			</div>
		</div>

		<div class="section">
			<div class="section-title">PR Analysis</div>
			<p class="info-text">Analyze pull requests automatically</p>
			<div class="button-group">
				<button class="button" id="prBtn">
					<span>📋 Analyze PR</span>
				</button>
			</div>
		</div>

		<div class="section">
			<div class="section-title">Settings</div>
			<p class="info-text">Configure extension options</p>
			<div class="button-group">
				<button class="button" id="settingsBtn">
					<span>⚙️ Open Settings</span>
				</button>
			</div>
		</div>

		<div id="status"></div>
	</div>

	<script>
		const vscode = acquireVsCodeApi();

		document.getElementById('completeBtn').addEventListener('click', () => {
			vscode.postMessage({ command: 'completeCode' });
		});

		document.getElementById('testBtn').addEventListener('click', () => {
			vscode.postMessage({ command: 'generateTests' });
		});

		document.getElementById('prBtn').addEventListener('click', () => {
			vscode.postMessage({ command: 'analyzePR' });
		});

		document.getElementById('settingsBtn').addEventListener('click', () => {
			vscode.postMessage({ command: 'openSettings' });
		});

		window.addEventListener('message', (event) => {
			const message = event.data;
			const statusEl = document.getElementById('status');

			if (message.type === 'status') {
				statusEl.innerHTML = \`<div class="status info">\${message.message}</div>\`;
			} else if (message.type === 'testResult') {
				statusEl.innerHTML = \`<div class="status success">✅ Generated \${message.data.test_count} tests</div>\`;
			} else if (message.type === 'completionResult') {
				statusEl.innerHTML = \`<div class="status success">✅ Got \${message.data.length} suggestions</div>\`;
			}
		});
	</script>
</body>
</html>`;
    }
}

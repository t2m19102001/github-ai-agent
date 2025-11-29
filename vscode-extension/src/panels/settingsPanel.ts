import * as vscode from 'vscode';

export class SettingsPanel {
    private panel: vscode.WebviewPanel;

    constructor(private extensionUri: vscode.Uri) {
        this.panel = vscode.window.createWebviewPanel(
            'github-ai-agent-settings',
            'GitHub AI Agent Settings',
            vscode.ViewColumn.One,
            { enableScripts: true }
        );

        this.panel.webview.html = this.getHtmlContent();
        this.panel.webview.onDidReceiveMessage((message) => this.handleMessage(message));
    }

    show() {
        this.panel.reveal();
    }

    private handleMessage(message: any) {
        if (message.type === 'updateSetting') {
            vscode.workspace
                .getConfiguration('github-ai-agent')
                .update(message.setting, message.value, vscode.ConfigurationTarget.Global);
            vscode.window.showInformationMessage('Settings updated');
        }
    }

    private getHtmlContent(): string {
        return `<!DOCTYPE html>
<html lang="en">
<head>
	<meta charset="UTF-8">
	<meta name="viewport" content="width=device-width, initial-scale=1.0">
	<title>GitHub AI Agent Settings</title>
	<style>
		body {
			padding: 20px;
			font-family: var(--vscode-font-family);
			color: var(--vscode-foreground);
		}
		h1 {
			color: var(--vscode-textLink-foreground);
			margin-bottom: 20px;
		}
		.setting-group {
			margin-bottom: 20px;
			padding-bottom: 20px;
			border-bottom: 1px solid var(--vscode-widget-border);
		}
		.setting-group:last-child {
			border-bottom: none;
		}
		.setting-label {
			font-weight: bold;
			margin-bottom: 5px;
			display: block;
		}
		.setting-description {
			font-size: 12px;
			color: var(--vscode-descriptionForeground);
			margin-bottom: 8px;
		}
		input[type="text"],
		input[type="number"],
		input[type="checkbox"],
		select {
			padding: 6px;
			background-color: var(--vscode-input-background);
			color: var(--vscode-input-foreground);
			border: 1px solid var(--vscode-input-border);
			border-radius: 3px;
			font-family: var(--vscode-font-family);
		}
		input[type="text"],
		select {
			width: 100%;
			box-sizing: border-box;
		}
		.checkbox-container {
			display: flex;
			align-items: center;
			gap: 8px;
		}
		button {
			background-color: var(--vscode-button-background);
			color: var(--vscode-button-foreground);
			border: none;
			padding: 8px 16px;
			border-radius: 3px;
			cursor: pointer;
			font-size: 14px;
		}
		button:hover {
			background-color: var(--vscode-button-hoverBackground);
		}
	</style>
</head>
<body>
	<h1>⚙️ GitHub AI Agent Settings</h1>

	<div class="setting-group">
		<label class="setting-label">API Endpoint</label>
		<p class="setting-description">URL of the GitHub AI Agent backend server</p>
		<input type="text" id="apiEndpoint" value="http://localhost:5000" placeholder="http://localhost:5000">
	</div>

	<div class="setting-group">
		<label class="setting-label">Test Framework</label>
		<p class="setting-description">Default framework for test generation</p>
		<select id="testFramework">
			<option value="pytest">pytest (Python)</option>
			<option value="unittest">unittest (Python)</option>
			<option value="jest">jest (JavaScript)</option>
			<option value="vitest">vitest (TypeScript)</option>
			<option value="mocha">mocha (JavaScript)</option>
		</select>
	</div>

	<div class="setting-group">
		<label class="setting-label">Code Coverage Target (%)</label>
		<p class="setting-description">Target coverage percentage for generated tests (0-100)</p>
		<input type="number" id="coverageTarget" min="0" max="100" value="80">
	</div>

	<div class="setting-group">
		<label class="setting-label">Max Suggestions</label>
		<p class="setting-description">Maximum number of code completion suggestions (1-10)</p>
		<input type="number" id="maxSuggestions" min="1" max="10" value="5">
	</div>

	<div class="setting-group">
		<label class="setting-label">Auto-Complete Delay (ms)</label>
		<p class="setting-description">Delay before showing completion suggestions (100-5000ms)</p>
		<input type="number" id="completionDelay" min="100" max="5000" value="1000" step="100">
	</div>

	<div class="setting-group">
		<div class="checkbox-container">
			<input type="checkbox" id="enableAutoComplete" checked>
			<label class="setting-label" for="enableAutoComplete">Enable Auto-Complete</label>
		</div>
		<p class="setting-description">Show code completions while typing</p>
	</div>

	<div class="setting-group">
		<div class="checkbox-container">
			<input type="checkbox" id="enableAutoAnalyze">
			<label class="setting-label" for="enableAutoAnalyze">Enable Auto-Analyze PR</label>
		</div>
		<p class="setting-description">Automatically analyze PRs on file save</p>
	</div>

	<button onclick="saveSettings()">💾 Save Settings</button>

	<script>
		const vscode = acquireVsCodeApi();

		function saveSettings() {
			const settings = {
				'github-ai-agent.apiEndpoint': document.getElementById('apiEndpoint').value,
				'github-ai-agent.testFramework': document.getElementById('testFramework').value,
				'github-ai-agent.coverageTarget': parseInt(document.getElementById('coverageTarget').value),
				'github-ai-agent.maxSuggestions': parseInt(document.getElementById('maxSuggestions').value),
				'github-ai-agent.completionDelay': parseInt(document.getElementById('completionDelay').value),
				'github-ai-agent.enableAutoComplete': document.getElementById('enableAutoComplete').checked,
				'github-ai-agent.enableAutoAnalyze': document.getElementById('enableAutoAnalyze').checked
			};

			Object.entries(settings).forEach(([key, value]) => {
				vscode.postMessage({
					type: 'updateSetting',
					setting: key,
					value: value
				});
			});
		}
	</script>
</body>
</html>`;
    }
}

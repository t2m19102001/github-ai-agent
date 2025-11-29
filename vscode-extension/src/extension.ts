import * as vscode from 'vscode';
import { AIAgentPanel } from './panels/aiAgentPanel';
import { CodeCompletionProvider } from './providers/completionProvider';
import { PRAnalysisCommand } from './commands/prAnalysis';
import { TestGenerationCommand } from './commands/testGeneration';
import { CodeCompletionCommand } from './commands/codeCompletion';
import { SettingsPanel } from './panels/settingsPanel';
import { ApiClient } from './services/apiClient';
import { StatusBarManager } from './ui/statusBar';

let aiAgentPanel: AIAgentPanel;
let statusBar: StatusBarManager;

export async function activate(context: vscode.ExtensionContext) {
    console.log('🚀 GitHub AI Agent Extension activated');

    // Initialize API client
    const apiClient = new ApiClient();
    statusBar = new StatusBarManager();

    // Show loading status
    statusBar.show('Initializing GitHub AI Agent...', 'info');

    try {
        // Check backend connection
        const isConnected = await apiClient.checkConnection();
        if (isConnected) {
            statusBar.show('✅ Connected to AI Agent', 'success');
        } else {
            statusBar.show('⚠️ Backend not available', 'warning');
        }
    } catch (error) {
        statusBar.show('❌ Failed to connect to backend', 'error');
    }

    // Register Panel View
    const panelProvider = new AIAgentPanel(context.extensionUri, apiClient);
    context.subscriptions.push(
        vscode.window.registerWebviewViewProvider(
            'github-ai-agent-panel',
            panelProvider,
            { webviewOptions: { retainContextWhenHidden: true } }
        )
    );

    // Register Code Completion Provider
    const completionProvider = new CodeCompletionProvider(apiClient);
    context.subscriptions.push(
        vscode.languages.registerCompletionItemProvider(
            [
                { scheme: 'file', language: 'python' },
                { scheme: 'file', language: 'javascript' },
                { scheme: 'file', language: 'typescript' },
                { scheme: 'file', language: 'java' },
                { scheme: 'file', language: 'csharp' },
                { scheme: 'file', language: 'cpp' },
                { scheme: 'file', language: 'go' },
                { scheme: 'file', language: 'rust' },
                { scheme: 'file', language: 'ruby' },
                { scheme: 'file', language: 'php' },
                { scheme: 'file', language: 'swift' },
                { scheme: 'file', language: 'kotlin' }
            ],
            completionProvider,
            '.' // Trigger on '.'
        )
    );

    // Register Commands
    const prCommand = new PRAnalysisCommand(apiClient, statusBar);
    const testCommand = new TestGenerationCommand(apiClient, statusBar);
    const completionCommand = new CodeCompletionCommand(apiClient, statusBar);

    context.subscriptions.push(
        vscode.commands.registerCommand('github-ai-agent.analyzePR', () =>
            prCommand.execute(context)
        )
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('github-ai-agent.generateTests', () =>
            testCommand.execute(context)
        )
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('github-ai-agent.completeCode', () =>
            completionCommand.execute(context)
        )
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('github-ai-agent.showPanel', () => {
            vscode.commands.executeCommand('github-ai-agent-panel.focus');
        })
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('github-ai-agent.openSettings', () => {
            const settingsPanel = new SettingsPanel(context.extensionUri);
            settingsPanel.show();
        })
    );

    // Toggle Auto-Complete
    let autoCompleteEnabled = vscode.workspace
        .getConfiguration('github-ai-agent')
        .get('enableAutoComplete', true);

    context.subscriptions.push(
        vscode.commands.registerCommand('github-ai-agent.toggleAutoComplete', async () => {
            autoCompleteEnabled = !autoCompleteEnabled;
            await vscode.workspace
                .getConfiguration('github-ai-agent')
                .update('enableAutoComplete', autoCompleteEnabled, vscode.ConfigurationTarget.Global);

            const msg = autoCompleteEnabled ? 'enabled' : 'disabled';
            statusBar.show(`Auto-complete ${msg}`, 'info');
            vscode.window.showInformationMessage(`AI Agent auto-complete ${msg}`);
        })
    );

    // Listen for configuration changes
    context.subscriptions.push(
        vscode.workspace.onDidChangeConfiguration((event) => {
            if (event.affectsConfiguration('github-ai-agent')) {
                console.log('⚙️ Settings updated');
                statusBar.show('Settings updated', 'info');
            }
        })
    );

    statusBar.show('✨ AI Agent Ready', 'success');
    console.log('✅ GitHub AI Agent Extension initialized successfully');
}

export function deactivate() {
    console.log('👋 GitHub AI Agent Extension deactivated');
    statusBar?.dispose();
}

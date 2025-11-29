import * as vscode from 'vscode';

export class StatusBarManager {
    private statusBarItem: vscode.StatusBarItem;

    constructor() {
        this.statusBarItem = vscode.window.createStatusBarItem(
            vscode.StatusBarAlignment.Right,
            100
        );
        this.statusBarItem.command = 'github-ai-agent.showPanel';
        this.statusBarItem.tooltip = 'Click to open GitHub AI Agent panel';
        this.show('🤖 AI Agent', 'info');
    }

    show(message: string, type: 'success' | 'warning' | 'error' | 'info' = 'info') {
        this.statusBarItem.text = `$(${this.getIcon(type)}) ${message}`;
        this.statusBarItem.show();

        // Color based on type
        switch (type) {
            case 'error':
                this.statusBarItem.backgroundColor = new vscode.ThemeColor('statusBarItem.errorBackground');
                break;
            case 'warning':
                this.statusBarItem.backgroundColor = new vscode.ThemeColor('statusBarItem.warningBackground');
                break;
            case 'success':
                this.statusBarItem.backgroundColor = new vscode.ThemeColor('statusBarItem.remoteBackground');
                break;
            default:
                this.statusBarItem.backgroundColor = undefined;
        }
    }

    private getIcon(type: string): string {
        switch (type) {
            case 'error': return 'error';
            case 'warning': return 'warning';
            case 'success': return 'pass';
            case 'info': return 'info';
            default: return 'circle-large-filled';
        }
    }

    dispose() {
        this.statusBarItem.dispose();
    }
}

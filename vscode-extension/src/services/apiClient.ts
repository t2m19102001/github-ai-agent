import axios, { AxiosInstance } from 'axios';
import * as vscode from 'vscode';

export interface CompletionSuggestion {
    text: string;
    confidence: number;
    type: 'function' | 'method' | 'class' | 'variable' | 'import';
}

export interface TestGenerationResult {
    status: string;
    test_code: string;
    test_count: number;
    language: string;
    framework: string;
    functions_tested: string[];
}

export interface PRAnalysisResult {
    status: string;
    security_issues: string[];
    performance_issues: string[];
    quality_issues: string[];
}

export class ApiClient {
    private client: AxiosInstance;
    private endpoint: string;

    constructor() {
        this.endpoint = vscode.workspace
            .getConfiguration('github-ai-agent')
            .get('apiEndpoint', 'http://localhost:5000');

        this.client = axios.create({
            baseURL: this.endpoint,
            timeout: 30000,
            headers: {
                'Content-Type': 'application/json'
            }
        });
    }

    async checkConnection(): Promise<boolean> {
        try {
            const response = await this.client.get('/');
            return response.status === 200;
        } catch (error) {
            return false;
        }
    }

    async getCompletion(
        codeBefore: string,
        codeAfter: string = '',
        language: string = 'python',
        filePath: string = ''
    ): Promise<CompletionSuggestion[]> {
        try {
            const response = await this.client.post('/api/complete', {
                code_before: codeBefore,
                code_after: codeAfter,
                language: language,
                file_path: filePath,
                max_suggestions: vscode.workspace
                    .getConfiguration('github-ai-agent')
                    .get('maxSuggestions', 5)
            });

            if (response.data.suggestions) {
                return response.data.suggestions.map((s: any) => ({
                    text: s.text || s,
                    confidence: s.confidence || 0.8,
                    type: this.inferType(s.text || s)
                }));
            }
            return [];
        } catch (error) {
            console.error('Completion error:', error);
            return [];
        }
    }

    async generateTests(
        code: string,
        language: string = 'python'
    ): Promise<TestGenerationResult> {
        try {
            const response = await this.client.post('/api/generate-tests', {
                code: code,
                language: language,
                framework: vscode.workspace
                    .getConfiguration('github-ai-agent')
                    .get('testFramework', 'pytest'),
                coverage_target: vscode.workspace
                    .getConfiguration('github-ai-agent')
                    .get('coverageTarget', 80)
            });

            return response.data;
        } catch (error) {
            console.error('Test generation error:', error);
            throw error;
        }
    }

    async analyzePR(
        prDiff: string,
        baseBranch: string = 'main'
    ): Promise<PRAnalysisResult> {
        try {
            const response = await this.client.post('/api/pr/analyze', {
                diff: prDiff,
                base_branch: baseBranch
            });

            return response.data;
        } catch (error) {
            console.error('PR analysis error:', error);
            throw error;
        }
    }

    async suggestTestCases(functionCode: string, language: string = 'python') {
        try {
            const response = await this.client.post('/api/generate-tests/suggest', {
                function_code: functionCode,
                language: language
            });

            return response.data;
        } catch (error) {
            console.error('Test suggestion error:', error);
            throw error;
        }
    }

    async analyzeCoverage(code: string, testCode: string, language: string = 'python') {
        try {
            const response = await this.client.post('/api/generate-tests/coverage', {
                code: code,
                test_code: testCode,
                language: language
            });

            return response.data;
        } catch (error) {
            console.error('Coverage analysis error:', error);
            throw error;
        }
    }

    private inferType(
        suggestion: string
    ): 'function' | 'method' | 'class' | 'variable' | 'import' {
        if (suggestion.includes('import ')) return 'import';
        if (suggestion.includes('class ')) return 'class';
        if (suggestion.includes('def ') || suggestion.includes('function ')) return 'function';
        if (suggestion.includes('(') && suggestion.includes(')')) return 'method';
        return 'variable';
    }

    updateEndpoint(endpoint: string) {
        this.endpoint = endpoint;
        this.client = axios.create({
            baseURL: endpoint,
            timeout: 30000,
            headers: {
                'Content-Type': 'application/json'
            }
        });
    }
}

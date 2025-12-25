#!/usr/bin/env python3
"""
Secret Detection Module
Detects and reports secrets in code and configuration files
"""

import re
import os
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from src.utils.logger import get_logger

logger = get_logger(__name__)


class SecretType(Enum):
    """Types of secrets"""
    API_KEY = "api_key"
    PASSWORD = "password"
    TOKEN = "token"
    CERTIFICATE = "certificate"
    PRIVATE_KEY = "private_key"
    DATABASE_URL = "database_url"
    JWT_SECRET = "jwt_secret"
    GITHUB_TOKEN = "github_token"
    SLACK_TOKEN = "slack_token"
    AWS_ACCESS_KEY = "aws_access_key"
    AWS_SECRET_KEY = "aws_secret_key"
    OAUTH_CLIENT_SECRET = "oauth_client_secret"


class SecretSeverity(Enum):
    """Secret severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class SecretPattern:
    """Secret detection pattern"""
    name: str
    secret_type: SecretType
    severity: SecretSeverity
    pattern: str
    description: str
    examples: List[str]
    false_positives: List[str] = None


@dataclass
class SecretMatch:
    """Secret match result"""
    secret_type: SecretType
    severity: SecretSeverity
    line_number: int
    line_content: str
    file_path: str
    pattern_name: str
    confidence: float


class SecretDetector:
    """Advanced secret detection system"""
    
    def __init__(self):
        self.secret_patterns = []
        self._initialize_patterns()
        
        logger.info("Secret detector initialized")
    
    def _initialize_patterns(self):
        """Initialize secret detection patterns"""
        # API Keys
        self.secret_patterns.extend([
            SecretPattern(
                name="Generic API Key",
                secret_type=SecretType.API_KEY,
                severity=SecretSeverity.HIGH,
                pattern=r'(?i)(api[_-]?key|apikey)\s*[:=]\s*["\']([a-zA-Z0-9]{20,})["\']',
                description="Generic API key",
                examples=["api_key='sk-1234567890abcdef1234567890abcdef'"],
                false_positives=["api_key='example_key'", "apikey='test123'"]
            ),
            SecretPattern(
                name="OpenAI API Key",
                secret_type=SecretType.API_KEY,
                severity=SecretSeverity.CRITICAL,
                pattern=r'(?i)(openai[_-]?api[_-]?key|sk-[a-zA-Z0-9]{48})',
                description="OpenAI API key",
                examples=["sk-1234567890abcdef1234567890abcdef12345678"],
                false_positives=["sk-example", "sk-test"]
            )
        ])
        
        # GitHub Tokens
        self.secret_patterns.extend([
            SecretPattern(
                name="GitHub Personal Access Token",
                secret_type=SecretType.GITHUB_TOKEN,
                severity=SecretSeverity.CRITICAL,
                pattern=r'(?i)(github[_-]?token|gh[_-]?token|ghp[_-]?token)\s*[:=]\s*["\']([a-zA-Z0-9_]{36})["\']',
                description="GitHub personal access token",
                examples=["github_token='ghp_EXAMPLE_TOKEN_PLACEHOLDER'"],
                false_positives=["github_token='ghp_example_token'"]
            ),
            SecretPattern(
                name="GitHub OAuth Token",
                secret_type=SecretType.GITHUB_TOKEN,
                severity=SecretSeverity.HIGH,
                pattern=r'(?i)(github[_-]?oauth[_-]?token)\s*[:=]\s*["\']([a-f0-9]{40})["\']',
                description="GitHub OAuth token",
                examples=["github_oauth_token='1234567890abcdef1234567890abcdef12345678'"]
            )
        ])
        
        # Database URLs
        self.secret_patterns.extend([
            SecretPattern(
                name="Database URL",
                secret_type=SecretType.DATABASE_URL,
                severity=SecretSeverity.HIGH,
                pattern=r'(?i)(database[_-]?url|db[_-]?url)\s*[:=]\s*["\']([a-zA-Z0-9+:/@.-]+)',
                description="Database connection URL",
                examples=["database_url='postgresql://user:password@localhost:5432/dbname'"],
                false_positives=["database_url='sqlite:///app.db'"]
            )
        ])
        
        # Passwords
        self.secret_patterns.extend([
            SecretPattern(
                name="Hardcoded Password",
                secret_type=SecretType.PASSWORD,
                severity=SecretSeverity.HIGH,
                pattern=r'(?i)(password|pwd|pass)\s*[:=]\s*["\']([a-zA-Z0-9!@#$%^&*]{8,})["\']',
                description="Hardcoded password detected",
                examples=["password='supersecretpassword123'"],
                false_positives=["password='password'", "pwd='12345678'", "password='example'"]
            )
        ])
        
        # Slack Tokens
        self.secret_patterns.extend([
            SecretPattern(
                name="Slack Bot Token",
                secret_type=SecretType.SLACK_TOKEN,
                severity=SecretSeverity.HIGH,
                pattern=r'(?i)(slack[_-]?token|slack[_-]?bot[_-]?token)\s*[:=]\s*["\'](xox[baprs]-[0-9]{12}-[0-9]{12}-[0-9]{12}-[a-zA-Z0-9]{24})["\']',
                description="Slack bot token",
                examples=["slack_token='xoxb-EXAMPLE-TOKEN-PLACEHOLDER'"],
                false_positives=["slack_token='xoxb-123456789012-123456789012-123456789012-example'"]
            )
        ])
        
        # AWS Keys
        self.secret_patterns.extend([
            SecretPattern(
                name="AWS Access Key",
                secret_type=SecretType.AWS_ACCESS_KEY,
                severity=SecretSeverity.CRITICAL,
                pattern=r'(?i)(aws[_-]?access[_-]?key[_-]?id)\s*[:=]\s*["\']([A-Z0-9]{20})["\']',
                description="AWS access key ID",
                examples=["aws_access_key_id='AKIAIOSFODNN7EXAMPLE'"],
                false_positives=["aws_access_key_id='AKIAEXAMPLE'"]
            ),
            SecretPattern(
                name="AWS Secret Key",
                secret_type=SecretType.AWS_SECRET_KEY,
                severity=SecretSeverity.CRITICAL,
                pattern=r'(?i)(aws[_-]?secret[_-]?access[_-]?key)\s*[:=]\s*["\']([a-zA-Z0-9+/]{40})["\']',
                description="AWS secret access key",
                examples=["aws_secret_access_key='wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY'"],
                false_positives=["aws_secret_access_key='example'"]
            )
        ])
        
        # JWT Secrets
        self.secret_patterns.extend([
            SecretPattern(
                name="JWT Secret",
                secret_type=SecretType.JWT_SECRET,
                severity=SecretSeverity.HIGH,
                pattern=r'(?i)(jwt[_-]?secret|secret[_-]?key)\s*[:=]\s*["\']([a-zA-Z0-9!@#$%^&*]{16,})["\']',
                description="JWT secret key",
                examples=["jwt_secret='your-256-bit-secret-key'"],
                false_positives=["jwt_secret='secret'", "secret_key='key'"]
            )
        ])
        
        # Private Keys
        self.secret_patterns.extend([
            SecretPattern(
                name="RSA Private Key",
                secret_type=SecretType.PRIVATE_KEY,
                severity=SecretSeverity.CRITICAL,
                pattern=r'-----BEGIN\s+(RSA\s+)?PRIVATE\s+KEY-----',
                description="RSA private key",
                examples=["-----BEGIN RSA PRIVATE KEY-----"],
                false_positives=[]
            ),
            SecretPattern(
                name="SSH Private Key",
                secret_type=SecretType.PRIVATE_KEY,
                severity=SecretSeverity.CRITICAL,
                pattern=r'-----BEGIN\s+OPENSSH\s+PRIVATE\s+KEY-----',
                description="SSH private key",
                examples=["-----BEGIN OPENSSH PRIVATE KEY-----"],
                false_positives=[]
            )
        ])
        
        # OAuth Client Secrets
        self.secret_patterns.extend([
            SecretPattern(
                name="OAuth Client Secret",
                secret_type=SecretType.OAUTH_CLIENT_SECRET,
                severity=SecretSeverity.HIGH,
                pattern=r'(?i)(client[_-]?secret|oauth[_-]?client[_-]?secret)\s*[:=]\s*["\']([a-zA-Z0-9-_]{16,})["\']',
                description="OAuth client secret",
                examples=["client_secret='abcdef1234567890abcdef12345678'"],
                false_positives=["client_secret='example_secret'"]
            )
        ])
    
    def scan_file(self, file_path: str) -> List[SecretMatch]:
        """Scan a single file for secrets"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            return self._scan_content(content, file_path)
            
        except Exception as e:
            logger.error(f"Failed to scan file {file_path}: {e}")
            return []
    
    def scan_directory(self, directory_path: str, 
                      file_extensions: List[str] = None) -> Dict[str, List[SecretMatch]]:
        """Scan directory for secrets"""
        if file_extensions is None:
            file_extensions = ['.py', '.js', '.ts', '.json', '.yml', '.yaml', '.env', '.conf']
        
        results = {}
        
        for root, dirs, files in os.walk(directory_path):
            # Skip hidden directories and common non-source directories
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['node_modules', '__pycache__', 'venv', 'env']]
            
            for file in files:
                file_path = os.path.join(root, file)
                
                # Check file extension
                _, ext = os.path.splitext(file)
                if ext in file_extensions:
                    secrets = self.scan_file(file_path)
                    if secrets:
                        results[file_path] = secrets
        
        return results
    
    def _scan_content(self, content: str, file_path: str) -> List[SecretMatch]:
        """Scan content for secrets"""
        matches = []
        lines = content.split('\n')
        
        for line_num, line in enumerate(lines, 1):
            for pattern in self.secret_patterns:
                # Check for matches
                match = re.search(pattern.pattern, line)
                if match:
                    # Check if it's a false positive
                    if self._is_false_positive(line, pattern):
                        continue
                    
                    # Calculate confidence
                    confidence = self._calculate_confidence(line, pattern)
                    
                    secret_match = SecretMatch(
                        secret_type=pattern.secret_type,
                        severity=pattern.severity,
                        line_number=line_num,
                        line_content=line.strip(),
                        file_path=file_path,
                        pattern_name=pattern.name,
                        confidence=confidence
                    )
                    
                    matches.append(secret_match)
        
        return matches
    
    def _is_false_positive(self, line: str, pattern: SecretPattern) -> bool:
        """Check if match is a false positive"""
        line_lower = line.lower()
        
        for false_positive in pattern.false_positives:
            if false_positive.lower() in line_lower:
                return True
        
        # Common false positive patterns
        false_positive_patterns = [
            'example', 'test', 'demo', 'sample', 'placeholder',
            'xxx', 'yyy', 'zzz', 'abc', '123', 'fake',
            'your-api-key', 'replace-with', 'change-this'
        ]
        
        for fp_pattern in false_positive_patterns:
            if fp_pattern in line_lower:
                return True
        
        return False
    
    def _calculate_confidence(self, line: str, pattern: SecretPattern) -> float:
        """Calculate confidence score for match"""
        confidence = 0.5  # Base confidence
        
        # Increase confidence for longer secrets
        if len(line) > 50:
            confidence += 0.2
        
        # Increase confidence for proper format
        if re.match(r'^\s*[a-zA-Z_][a-zA-Z0-9_]*\s*[:=]\s*["\'][^"\']+["\']\s*$', line):
            confidence += 0.2
        
        # Decrease confidence for obvious test patterns
        if any(word in line.lower() for word in ['test', 'example', 'demo', 'sample']):
            confidence -= 0.3
        
        return min(1.0, max(0.0, confidence))
    
    def get_summary(self, results: Dict[str, List[SecretMatch]]) -> Dict[str, Any]:
        """Get summary of secret detection results"""
        total_secrets = sum(len(secrets) for secrets in results.values())
        
        severity_counts = {
            SecretSeverity.CRITICAL: 0,
            SecretSeverity.HIGH: 0,
            SecretSeverity.MEDIUM: 0,
            SecretSeverity.LOW: 0
        }
        
        type_counts = {}
        
        for secrets in results.values():
            for secret in secrets:
                severity_counts[secret.severity] += 1
                
                if secret.secret_type not in type_counts:
                    type_counts[secret.secret_type] = 0
                type_counts[secret.secret_type] += 1
        
        return {
            'total_secrets': total_secrets,
            'files_with_secrets': len(results),
            'severity_breakdown': {k.value: v for k, v in severity_counts.items()},
            'type_breakdown': {k.value: v for k, v in type_counts.items()},
            'most_common_type': max(type_counts.items(), key=lambda x: x[1])[0] if type_counts else None,
            'highest_severity': max([s.severity for secrets in results.values() for s in secrets], 
                                 key=lambda x: {'critical': 4, 'high': 3, 'medium': 2, 'low': 1}[x.value]).value if results else None
        }


# Global secret detector instance
_secret_detector: Optional[SecretDetector] = None


def get_secret_detector() -> SecretDetector:
    """Get global secret detector instance"""
    global _secret_detector
    if _secret_detector is None:
        _secret_detector = SecretDetector()
    return _secret_detector


# Utility functions
def scan_file_for_secrets(file_path: str) -> List[SecretMatch]:
    """Scan file for secrets"""
    detector = get_secret_detector()
    return detector.scan_file(file_path)


def scan_directory_for_secrets(directory_path: str) -> Dict[str, List[SecretMatch]]:
    """Scan directory for secrets"""
    detector = get_secret_detector()
    return detector.scan_directory(directory_path)


def get_secret_scan_summary(results: Dict[str, List[SecretMatch]]) -> Dict[str, Any]:
    """Get summary of secret scan results"""
    detector = get_secret_detector()
    return detector.get_summary(results)

#!/usr/bin/env python3
"""
Main CLI entry point for AI Agent
Run with: python main.py
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.utils.logger import get_logger, setup_logging
from src.core.config import validate_config, print_config, ENV, DEBUG

logger = get_logger(__name__)


def main():
    """Main entry point"""
    try:
        # Setup logging
        setup_logging()
        
        # Validate configuration
        validate_config()
        
        # Print config summary
        print_config()
        
        print("\n" + "="*70)
        print("🤖 GitHub AI Agent - CLI Mode")
        print("="*70 + "\n")
        
        # Import after config validation
        from src.agents.code_agent import CodeChatAgent
        from src.agent.ai_provider import get_default_provider, ProviderAdapter
        
        base = get_default_provider()
        llm = ProviderAdapter(base)
        agent = CodeChatAgent(llm_provider=llm)
        
        logger.info("✅ Agents initialized")
        
        # Interactive chat loop
        print("Commands:")
        print("  'list' - List all files")
        print("  'read <file>' - Read file")
        print("  'context' - Show code context")
        print("  'quit' - Exit")
        print("\nOr ask any question about your code!\n")
        
        while True:
            try:
                user_input = input("You: ").strip()
                
                if not user_input:
                    continue
                
                if user_input.lower() == 'quit':
                    print("\nGoodbye! 👋")
                    break
                
                # Special commands
                if user_input.lower() == 'list':
                    from src.tools.tools import ListFilesTool
                    tool = ListFilesTool()
                    files = tool.execute()
                    print(f"\n📁 Files ({len(files)}):")
                    for f in files:
                        print(f"  - {f}")
                    print()
                    continue
                
                if user_input.lower().startswith('read '):
                    from src.tools.tools import FileReadTool
                    file_path = user_input[5:].strip()
                    tool = FileReadTool()
                    content = tool.execute(file_path)
                    if content:
                        print(f"\n📄 File: {file_path}")
                        print(f"```\n{content[:1000]}\n```\n")
                    else:
                        print(f"❌ File not found: {file_path}\n")
                    continue
                
                if user_input.lower() == 'context':
                    # TODO: Implement context building
                    print("📚 Loading context...\n")
                    continue
                
                # Regular chat
                print("\n🤖 Assistant: ", end="", flush=True)
                response = agent.chat(user_input)
                print(response)
                print()
            
            except KeyboardInterrupt:
                print("\n\nGoodbye! 👋")
                break
            except Exception as e:
                logger.error(f"Error: {e}")
                print(f"❌ Error: {e}\n")
    
    except ValueError as e:
        print(f"❌ Configuration error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        print(f"❌ Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

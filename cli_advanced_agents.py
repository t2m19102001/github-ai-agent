#!/usr/bin/env python3
"""
CLI tool để tương tác với Advanced AI Agents
Cho phép người dùng thử các agent chuyên biệt từ terminal
"""

import sys
import json
import argparse
from typing import Optional
from src.llm.groq import GroqProvider
from src.agents.agent_factory import create_agent, list_available_agents
from src.utils.logger import get_logger

logger = get_logger(__name__)


class AdvancedAgentCLI:
    """CLI interface cho Advanced AI Agents"""
    
    def __init__(self):
        """Initialize CLI"""
        self.llm = GroqProvider()
        self.current_agent = None
        self.agent_type = None
    
    def list_agents(self):
        """Hiển thị danh sách Agent có sẵn"""
        agents = list_available_agents()
        
        print("\n" + "="*60)
        print("📋 AVAILABLE ADVANCED AGENTS")
        print("="*60 + "\n")
        
        descriptions = {
            "python_expert": "Senior Python Developer & Code Architect",
            "devops": "Senior DevOps Engineer & Cloud Architect",
            "product_manager": "Senior Product Manager & Strategy Advisor",
            "data_scientist": "Senior Data Scientist & ML Engineer",
            "security": "Senior Security Engineer & Compliance Officer",
            "creative": "Creative Writer & Content Strategist"
        }
        
        for i, agent_type in enumerate(agents, 1):
            description = descriptions.get(agent_type, "Advanced AI Agent")
            print(f"{i}. {agent_type.upper()}")
            print(f"   📝 {description}\n")
        
        print("="*60 + "\n")
    
    def select_agent(self, agent_type: str):
        """Chọn một Agent"""
        agents = list_available_agents()
        
        if agent_type not in agents:
            print(f"❌ Invalid agent type: {agent_type}")
            print(f"Available agents: {', '.join(agents)}")
            return False
        
        try:
            self.current_agent = create_agent(agent_type, self.llm)
            self.agent_type = agent_type
            
            print(f"\n✅ Selected Agent: {self.current_agent.profile.name}")
            print(f"📋 Role: {self.current_agent.profile.role}")
            print(f"🎓 Expertise: {', '.join(self.current_agent.profile.expertise)}")
            print()
            
            return True
        except Exception as e:
            print(f"❌ Error creating agent: {e}")
            return False
    
    def chat(self, message: str):
        """Chat với Agent"""
        if not self.current_agent:
            print("❌ No agent selected. Use 'select' command first.")
            return
        
        try:
            print(f"\n🤖 {self.current_agent.profile.name}: ", end="", flush=True)
            response = self.current_agent.chat(message, "groq")
            print(f"\n{response}\n")
        except Exception as e:
            logger.error(f"Chat error: {e}")
            print(f"❌ Error: {e}\n")
    
    def plan(self, task: str):
        """Get multi-step plan từ Agent"""
        if not self.current_agent:
            print("❌ No agent selected. Use 'select' command first.")
            return
        
        try:
            print(f"\n📋 {self.current_agent.profile.name} Planning: \n")
            response = self.current_agent.execute_with_planning(task, "groq")
            print(f"{response}\n")
        except Exception as e:
            logger.error(f"Planning error: {e}")
            print(f"❌ Error: {e}\n")
    
    def execute_code(self, description: str, code: str):
        """Execute code qua Agent"""
        if not self.current_agent:
            print("❌ No agent selected. Use 'select' command first.")
            return
        
        try:
            print(f"\n⚙️ Executing code...\n")
            response = self.current_agent.execute_code_task(description, code)
            print(f"{response}\n")
        except Exception as e:
            logger.error(f"Code execution error: {e}")
            print(f"❌ Error: {e}\n")
    
    def show_status(self):
        """Hiển thị trạng thái Agent hiện tại"""
        if not self.current_agent:
            print("❌ No agent selected. Use 'select' command first.")
            return
        
        try:
            status = self.current_agent.get_agent_status()
            memory_stats = self.current_agent.memory.get_memory_stats()
            
            print("\n" + "="*60)
            print("🤖 AGENT STATUS")
            print("="*60 + "\n")
            
            print(f"Name: {status['name']}")
            print(f"Role: {status['role']}")
            print(f"Expertise: {', '.join(status['expertise'])}")
            print()
            
            print("📊 Memory Statistics:")
            print(f"  • Short-term messages: {memory_stats['short_term_count']}")
            print(f"  • Long-term knowledge: {memory_stats['long_term_count']}")
            print()
            
            print("🛠️ Available Tools:")
            for tool_name in status.get('tools', []):
                print(f"  • {tool_name}")
            print()
            
            print("="*60 + "\n")
        
        except Exception as e:
            logger.error(f"Status error: {e}")
            print(f"❌ Error: {e}\n")
    
    def interactive_mode(self):
        """Interactive chat mode"""
        if not self.current_agent:
            print("❌ No agent selected.")
            return
        
        print(f"\n{'='*60}")
        print(f"💬 INTERACTIVE MODE - {self.current_agent.profile.name}")
        print(f"{'='*60}")
        print("Commands: 'quit' to exit, 'plan <task>' for planning\n")
        
        while True:
            try:
                user_input = input(f"You: ").strip()
                
                if not user_input:
                    continue
                
                if user_input.lower() == 'quit':
                    print("👋 Goodbye!")
                    break
                
                if user_input.lower().startswith('plan '):
                    task = user_input[5:].strip()
                    self.plan(task)
                else:
                    self.chat(user_input)
            
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"❌ Error: {e}")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Advanced AI Agent CLI',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List all agents
  %(prog)s --list
  
  # Select and chat with Python Expert
  %(prog)s --agent python_expert --chat "How to optimize Python code?"
  
  # Get planning from DevOps agent
  %(prog)s --agent devops --plan "Design scalable microservices architecture"
  
  # Interactive mode
  %(prog)s --agent security --interactive
        """
    )
    
    parser.add_argument('--list', action='store_true',
                       help='List all available agents')
    parser.add_argument('--agent', type=str,
                       help='Select agent type')
    parser.add_argument('--chat', type=str,
                       help='Send chat message')
    parser.add_argument('--plan', type=str,
                       help='Get multi-step plan')
    parser.add_argument('--code', type=str,
                       help='Execute code with description')
    parser.add_argument('--interactive', action='store_true',
                       help='Enter interactive mode')
    parser.add_argument('--status', action='store_true',
                       help='Show agent status')
    
    args = parser.parse_args()
    
    cli = AdvancedAgentCLI()
    
    # List agents
    if args.list:
        cli.list_agents()
        return
    
    # Select agent if specified
    if args.agent:
        if not cli.select_agent(args.agent):
            sys.exit(1)
    
    # Show status
    if args.status:
        cli.show_status()
        return
    
    # Chat
    if args.chat:
        cli.chat(args.chat)
        return
    
    # Planning
    if args.plan:
        cli.plan(args.plan)
        return
    
    # Code execution (requires both --code and --agent)
    if args.code:
        if not args.agent:
            print("❌ --agent required for code execution")
            sys.exit(1)
        cli.execute_code("Execute provided code", args.code)
        return
    
    # Interactive mode
    if args.interactive:
        if not args.agent:
            print("❌ --agent required for interactive mode")
            sys.exit(1)
        cli.interactive_mode()
        return
    
    # Default: show help if no arguments
    if not args.agent:
        parser.print_help()
        print("\nℹ️  Use --list to see available agents")
        return
    
    # Interactive by default if agent selected
    cli.interactive_mode()


if __name__ == '__main__':
    main()

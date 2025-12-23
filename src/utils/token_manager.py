from typing import List, Dict, Optional
from src.utils.logger import get_logger
try:
    import tiktoken  # type: ignore
except Exception:
    tiktoken = None

logger = get_logger(__name__)

class TokenManager:
    """
    Manages token counting and context window optimization.
    Uses tiktoken for accurate counting (defaulting to cl100k_base encoding).
    """
    def __init__(self, model: str = "gpt-4"):
        if tiktoken is None:
            class _BasicEncoding:
                def encode(self, text: str):
                    return text.split() if text else []
                def decode(self, tokens: List[str]):
                    return " ".join(tokens)
            self.encoding = _BasicEncoding()
        else:
            try:
                self.encoding = tiktoken.encoding_for_model(model)
            except KeyError:
                self.encoding = tiktoken.get_encoding("cl100k_base")
            
    def count_tokens(self, text: str) -> int:
        """Count tokens in a text string"""
        if not text:
            return 0
        return len(self.encoding.encode(text))
    
    def count_message_tokens(self, messages: List[Dict[str, str]]) -> int:
        """Count tokens in a list of messages (chat format)"""
        num_tokens = 0
        for message in messages:
            # every message follows <im_start>{role/name}\n{content}<im_end>\n
            num_tokens += 4  
            for key, value in message.items():
                num_tokens += self.count_tokens(str(value))
                if key == "name":  # if there's a name, the role is omitted
                    num_tokens += -1  # role is always required and always 1 token
        num_tokens += 2  # every reply is primed with <im_start>assistant
        return num_tokens

    def truncate_text(self, text: str, max_tokens: int) -> str:
        """Truncate text to fit within max_tokens"""
        if self.count_tokens(text) <= max_tokens:
            return text
            
        tokens = self.encoding.encode(text)
        truncated_tokens = tokens[:max_tokens]
        return self.encoding.decode(truncated_tokens) + "...(truncated)"

    def limit_context(self, messages: List[Dict[str, str]], max_tokens: int) -> List[Dict[str, str]]:
        """
        Limit context by removing oldest messages, but ALWAYS keeping:
        1. System prompts (critical instructions)
        2. The most recent user message (the query)
        """
        if not messages:
            return []
            
        # Separate messages
        system_messages = [m for m in messages if m.get("role") == "system"]
        other_messages = [m for m in messages if m.get("role") != "system"]
        
        if not other_messages:
            return system_messages

        # Always keep the last message (the user's query)
        last_message = other_messages.pop()
        
        # Calculate tokens for mandatory items
        system_tokens = self.count_message_tokens(system_messages)
        last_msg_tokens = self.count_message_tokens([last_message])
        
        available_tokens = max_tokens - system_tokens - last_msg_tokens
        
        if available_tokens < 0:
            logger.warning(f"Context overflow! System + Last Msg = {system_tokens + last_msg_tokens} > {max_tokens}")
            # If even system + last message is too big, we must truncate the last message
            # and maybe even system messages (but system is usually small)
            # For now, let's just return what we have and hope the LLM handles it or we truncate the last message
            
            # Try to truncate last message
            if last_msg_tokens > max_tokens - system_tokens:
                 content = last_message.get("content", "")
                 truncated_content = self.truncate_text(content, max(100, max_tokens - system_tokens - 100))
                 last_message["content"] = truncated_content
            
            return system_messages + [last_message]
            
        current_tokens = 0
        kept_messages = []
        
        # Process remaining messages from newest to oldest
        for msg in reversed(other_messages):
            msg_tokens = self.count_message_tokens([msg])
            if current_tokens + msg_tokens <= available_tokens:
                kept_messages.insert(0, msg)
                current_tokens += msg_tokens
            else:
                logger.debug(f"Dropping old message to fit context window ({msg_tokens} tokens)")
                break
                
        return system_messages + kept_messages + [last_message]

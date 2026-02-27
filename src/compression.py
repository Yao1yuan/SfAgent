from typing import List
from langchain_core.messages import BaseMessage, ToolMessage, SystemMessage, AIMessage, HumanMessage

def compress_history(messages: List[BaseMessage], max_token_estimate: int = 20000) -> List[BaseMessage]:
    """
    Compress the message history to avoid hitting token limits.

    Strategy:
    1. Always keep the System Message (first message).
    2. Always keep the last N messages (e.g., last 5) to maintain immediate context.
    3. For older messages:
        a. Truncate 'ToolMessage' content if it's too long (e.g., file reads).
        b. If total length is still too high, summarize or remove oldest turns.

    Args:
        messages: The list of messages in the state.
        max_token_estimate: Rough character count threshold (1 token ~= 4 chars, so 20k tokens ~= 80k chars).
                            Let's use character count for simplicity and speed.

    Returns:
        A new list of messages.
    """
    if not messages:
        return []

    # Make a shallow copy to modify
    compressed = list(messages)

    # 1. Truncate old ToolMessages
    # We define "old" as anything before the last 5 messages.
    # We want to preserve the SystemPrompt (index 0).

    keep_last_n = 5
    if len(compressed) > keep_last_n + 1:
        # Range to process: from index 1 (after system) to len - keep_last_n
        for i in range(1, len(compressed) - keep_last_n):
            msg = compressed[i]
            if isinstance(msg, ToolMessage):
                # If content is very long, truncate it
                content_str = str(msg.content)
                if len(content_str) > 500:
                    compressed[i] = ToolMessage(
                        tool_call_id=msg.tool_call_id,
                        content=content_str[:200] + f"\n... [Output truncated by History Compressor. Original length: {len(content_str)} chars] ...\n" + content_str[-100:],
                        name=msg.name,
                        artifact=msg.artifact
                    )

    # 2. Check total size and prune if needed
    total_chars = sum(len(str(m.content)) for m in compressed)

    # Threshold: 80,000 chars (approx 20k tokens)
    char_limit = max_token_estimate * 4

    if total_chars > char_limit:
        print(f"[Compressor] History size ({total_chars} chars) exceeds limit ({char_limit}). Pruning...")

        # Pruning Strategy: Remove oldest messages between System and Last-N
        # We replace removed messages with a single SystemMessage summary placeholder
        # In a real "Infinite Memory" system, we would use an LLM to summarize them.
        # For this implementation (Step 2), we will simply drop them and add a marker.

        # Calculate how many to drop
        # We need to drop enough to get under the limit.
        # Let's drop chunks of 5 messages until we are safe.

        # Always keep index 0
        system_msg = compressed[0]
        recent_msgs = compressed[-keep_last_n:]

        # The middle part is candidates for removal
        middle_msgs = compressed[1:-keep_last_n]

        # If we have middle messages, remove the first half of them
        if middle_msgs:
            # Drop older half of the middle
            drop_count = max(1, len(middle_msgs) // 2)
            kept_middle = middle_msgs[drop_count:]

            summary_msg = SystemMessage(content=f"[System: Pruned {drop_count} oldest messages to save context window.]")

            compressed = [system_msg, summary_msg] + kept_middle + recent_msgs

            new_chars = sum(len(str(m.content)) for m in compressed)
            print(f"[Compressor] Pruned to {new_chars} chars.")

    return compressed

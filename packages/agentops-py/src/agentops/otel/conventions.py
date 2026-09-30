from __future__ import annotations

from enum import StrEnum


class GenAI(StrEnum):
    SYSTEM = "gen_ai.system"
    REQUEST_MODEL = "gen_ai.request.model"
    RESPONSE_MODEL = "gen_ai.response.model"
    USAGE_INPUT_TOKENS = "gen_ai.usage.input_tokens"
    USAGE_OUTPUT_TOKENS = "gen_ai.usage.output_tokens"
    OPERATION_NAME = "gen_ai.operation.name"
    TOOL_NAME = "gen_ai.tool.name"
    TOOL_CALL_ID = "gen_ai.tool.call.id"

class AgentOps(StrEnum):
    """AgentOps-specific extensions."""
    RUN_ID = "agentops.run_id"
    ROLE = "agentops.role"
    PROMPT_SHA = "agentops.prompt_sha"
    AGENT_NAME = "agentops.agent_name"
    EVAL_RESULT = "agentops.eval_result"
    INPUT = "agentops.input"
    OUTPUT = "agentops.output"
    ATTRIBUTION = "agentops.attribution"

export const GenAI = {
  System: "gen_ai.system",
  RequestModel: "gen_ai.request.model",
  ResponseModel: "gen_ai.response.model",
  UsageInputTokens: "gen_ai.usage.input_tokens",
  UsageOutputTokens: "gen_ai.usage.output_tokens",
  OperationName: "gen_ai.operation.name",
  ToolName: "gen_ai.tool.name",
  ToolCallId: "gen_ai.tool.call.id",
} as const;

export const AgentOps = {
  RunId: "agentops.run_id",
  Role: "agentops.role",
  PromptSha: "agentops.prompt_sha",
  AgentName: "agentops.agent_name",
  EvalResult: "agentops.eval_result",
  Input: "agentops.input",
  Output: "agentops.output",
} as const;

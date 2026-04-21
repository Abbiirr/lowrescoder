"""Stage 0A JSON-RPC schema for the Rust TUI/backend contract."""

from __future__ import annotations

from typing import Any

try:
    from pydantic import BaseModel, ConfigDict, Field
except ModuleNotFoundError:  # pragma: no cover - direct PTY stubs only need constants
    class BaseModel:  # type: ignore[too-many-ancestors]
        pass

    def _config_dict(**_: object) -> dict[str, object]:
        return {}

    def _field(  # type: ignore[misc]
        *,
        default_factory: object | None = None,
        default: object | None = None,
    ) -> object:
        if default_factory is not None:
            return default_factory()
        return default

    ConfigDict = _config_dict
    Field = _field

METHOD_ON_STATUS = "on_status"
METHOD_ON_ERROR = "on_error"
METHOD_ON_TOKEN = "on_token"
METHOD_ON_THINKING = "on_thinking"
METHOD_ON_DONE = "on_done"
METHOD_ON_TOOL_CALL = "on_tool_call"
METHOD_ON_TASK_STATE = "on_task_state"
METHOD_ON_COST_UPDATE = "on_cost_update"
METHOD_ON_TOOL_REQUEST = "on_tool_request"
METHOD_ON_ASK_USER = "on_ask_user"

METHOD_CHAT = "chat"
METHOD_CANCEL = "cancel"
METHOD_COMMAND = "command"
METHOD_COMMAND_LIST = "command.list"
METHOD_SESSION_NEW = "session.new"
METHOD_SESSION_LIST = "session.list"
METHOD_MODEL_LIST = "model.list"
METHOD_PROVIDER_LIST = "provider.list"
METHOD_SESSION_RESUME = "session.resume"
METHOD_TASK_LIST = "task.list"
METHOD_SUBAGENT_LIST = "subagent.list"
METHOD_SUBAGENT_CANCEL = "subagent.cancel"
METHOD_PLAN_STATUS = "plan.status"
METHOD_PLAN_SET = "plan.set"
METHOD_CONFIG_GET = "config.get"
METHOD_CONFIG_SET = "config.set"
METHOD_MEMORY_LIST = "memory.list"
METHOD_CHECKPOINT_LIST = "checkpoint.list"
METHOD_CHECKPOINT_RESTORE = "checkpoint.restore"
METHOD_PLAN_EXPORT = "plan.export"
METHOD_PLAN_SYNC = "plan.sync"
METHOD_STEER = "steer"
METHOD_SESSION_FORK = "session.fork"
METHOD_SHUTDOWN = "shutdown"


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RpcError(StrictModel):
    code: int
    message: str


class RpcMessage(StrictModel):
    jsonrpc: str
    id: int | None = None
    method: str | None = None
    params: Any | None = None
    result: Any | None = None
    error: RpcError | None = None


class EmptyParams(StrictModel):
    pass


class ErrorParams(StrictModel):
    message: str


class StatusParams(StrictModel):
    model: str
    provider: str
    mode: str
    session_id: str | None = None


class TokenParams(StrictModel):
    text: str


class ThinkingParams(StrictModel):
    text: str


class DoneParams(StrictModel):
    tokens_in: int
    tokens_out: int
    cancelled: bool = False
    layer_used: int = 0


class ToolCallParams(StrictModel):
    name: str
    status: str
    result: str | None = None
    args: str | None = None


class TaskEntry(StrictModel):
    id: str
    title: str
    status: str


class SubagentEntry(StrictModel):
    id: str
    role: str
    status: str


class TaskStateParams(StrictModel):
    tasks: list[TaskEntry] = Field(default_factory=list)
    subagents: list[SubagentEntry] = Field(default_factory=list)


class CostUpdateParams(StrictModel):
    cost: str
    tokens_in: int
    tokens_out: int


class ToolRequestParams(StrictModel):
    tool: str
    args: str


class AskUserRequestParams(StrictModel):
    question: str
    options: list[str] = Field(default_factory=list)
    allow_text: bool = False


class ChatParams(StrictModel):
    message: str
    session_id: str | None = None


class CommandParams(StrictModel):
    cmd: str


class CommandListEntry(StrictModel):
    name: str
    aliases: list[str] = Field(default_factory=list)
    description: str = ""


class CommandListResult(StrictModel):
    commands: list[CommandListEntry]


class CommandResult(StrictModel):
    ok: bool
    compacted: bool = False
    messages_compacted: int = 0
    summary_tokens: int = 0


class SessionNewParams(StrictModel):
    title: str | None = None


class SessionCreateResult(StrictModel):
    session_id: str


class SessionResumeParams(StrictModel):
    session_id: str


class SessionResumeResult(StrictModel):
    session_id: str
    title: str | None = None


class SessionInfo(StrictModel):
    id: str
    title: str
    model: str
    provider: str


class SessionListResult(StrictModel):
    sessions: list[SessionInfo]


class ProviderListResult(StrictModel):
    providers: list[str]
    current: str


class ModelListResult(StrictModel):
    models: list[str]
    current: str


class SubagentCancelParams(StrictModel):
    subagent_id: str


class SubagentCancelResult(StrictModel):
    success: bool


class PlanStatusResult(StrictModel):
    mode: str


class PlanSetParams(StrictModel):
    mode: str


class PlanSetResult(StrictModel):
    mode: str
    changed: bool


class ConfigSetParams(StrictModel):
    key: str
    value: str


class OkResult(StrictModel):
    ok: bool


class SteerParams(StrictModel):
    message: str


class ForkSessionResult(StrictModel):
    new_session_id: str


CANONICAL_METHODS = (
    METHOD_ON_STATUS,
    METHOD_ON_ERROR,
    METHOD_ON_TOKEN,
    METHOD_ON_THINKING,
    METHOD_ON_DONE,
    METHOD_ON_TOOL_CALL,
    METHOD_ON_TASK_STATE,
    METHOD_ON_COST_UPDATE,
    METHOD_ON_TOOL_REQUEST,
    METHOD_ON_ASK_USER,
    METHOD_CHAT,
    METHOD_CANCEL,
    METHOD_COMMAND,
    METHOD_COMMAND_LIST,
    METHOD_SESSION_NEW,
    METHOD_SESSION_LIST,
    METHOD_MODEL_LIST,
    METHOD_PROVIDER_LIST,
    METHOD_SESSION_RESUME,
    METHOD_TASK_LIST,
    METHOD_SUBAGENT_LIST,
    METHOD_SUBAGENT_CANCEL,
    METHOD_PLAN_STATUS,
    METHOD_PLAN_SET,
    METHOD_CONFIG_GET,
    METHOD_CONFIG_SET,
    METHOD_MEMORY_LIST,
    METHOD_CHECKPOINT_LIST,
    METHOD_CHECKPOINT_RESTORE,
    METHOD_PLAN_EXPORT,
    METHOD_PLAN_SYNC,
    METHOD_STEER,
    METHOD_SESSION_FORK,
    METHOD_SHUTDOWN,
)

COMPAT_METHOD_ALIASES: dict[str, str] = {}

PARAM_MODELS: dict[str, type[BaseModel]] = {
    METHOD_ON_STATUS: StatusParams,
    METHOD_ON_ERROR: ErrorParams,
    METHOD_ON_TOKEN: TokenParams,
    METHOD_ON_THINKING: ThinkingParams,
    METHOD_ON_DONE: DoneParams,
    METHOD_ON_TOOL_CALL: ToolCallParams,
    METHOD_ON_TASK_STATE: TaskStateParams,
    METHOD_ON_COST_UPDATE: CostUpdateParams,
    METHOD_ON_TOOL_REQUEST: ToolRequestParams,
    METHOD_ON_ASK_USER: AskUserRequestParams,
    METHOD_CHAT: ChatParams,
    METHOD_CANCEL: EmptyParams,
    METHOD_COMMAND: CommandParams,
    METHOD_COMMAND_LIST: EmptyParams,
    METHOD_SESSION_NEW: SessionNewParams,
    METHOD_SESSION_LIST: EmptyParams,
    METHOD_MODEL_LIST: EmptyParams,
    METHOD_PROVIDER_LIST: EmptyParams,
    METHOD_SESSION_RESUME: SessionResumeParams,
    METHOD_TASK_LIST: EmptyParams,
    METHOD_SUBAGENT_LIST: EmptyParams,
    METHOD_SUBAGENT_CANCEL: SubagentCancelParams,
    METHOD_PLAN_STATUS: EmptyParams,
    METHOD_PLAN_SET: PlanSetParams,
    METHOD_CONFIG_GET: EmptyParams,
    METHOD_CONFIG_SET: ConfigSetParams,
    METHOD_MEMORY_LIST: EmptyParams,
    METHOD_CHECKPOINT_LIST: EmptyParams,
    METHOD_PLAN_EXPORT: EmptyParams,
    METHOD_STEER: SteerParams,
    METHOD_SESSION_FORK: EmptyParams,
    METHOD_SHUTDOWN: EmptyParams,
}

RESULT_MODELS: dict[str, type[BaseModel]] = {
    METHOD_CANCEL: OkResult,
    METHOD_COMMAND: CommandResult,
    METHOD_COMMAND_LIST: CommandListResult,
    METHOD_SESSION_NEW: SessionCreateResult,
    METHOD_SESSION_LIST: SessionListResult,
    METHOD_MODEL_LIST: ModelListResult,
    METHOD_PROVIDER_LIST: ProviderListResult,
    METHOD_SESSION_RESUME: SessionResumeResult,
    METHOD_SUBAGENT_CANCEL: SubagentCancelResult,
    METHOD_PLAN_STATUS: PlanStatusResult,
    METHOD_PLAN_SET: PlanSetResult,
    METHOD_CONFIG_SET: OkResult,
    METHOD_SESSION_FORK: ForkSessionResult,
    METHOD_SHUTDOWN: OkResult,
}

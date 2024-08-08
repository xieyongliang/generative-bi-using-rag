from typing import Any, Union
from pydantic import BaseModel


class Question(BaseModel):
    query: str
    bedrock_model_id: str = "anthropic.claude-3-sonnet-20240229-v1:0"
    use_rag_flag: bool = True
    visualize_results_flag: bool = True
    intent_ner_recognition_flag: bool = True
    agent_cot_flag: bool = True
    profile_name: str
    explain_gen_process_flag: bool = True
    gen_suggested_question_flag: bool = False
    answer_with_insights: bool = False
    top_k: float = 250
    top_p: float = 0.9
    max_tokens: int = 2048
    temperature: float = 0.01
    context_window: int = 5
    session_id: str = "-1"
    user_id: str = "admin"


class HistoryRequest(BaseModel):
    user_id: str
    profile_name: str
    log_type: str = "chat_history"


class HistorySessionRequest(BaseModel):
    session_id: str
    profile_name: str
    user_id: str
    log_type: str = "chat_history"


class DlsetQuestion(BaseModel):
    #  与 table_name 相同
    profile_name: str
    table_id: int
    query: str
    user_id: str = "admin"
    session_id: str = "-1"
    token: str
    with_history: bool = False
    bedrock_model_id: str = "anthropic.claude-3-5-sonnet-20240620-v1:0"
    use_rag_flag: bool = True
    visualize_results_flag: bool = True
    intent_ner_recognition_flag: bool = True
    agent_cot_flag: bool = True
    gen_suggested_question_flag: bool = False
    top_k: float = 250
    top_p: float = 0.9
    max_tokens: int = 2048
    temperature: float = 0.01
    context_window: int = 5


class Example(BaseModel):
    score: float
    question: str
    answer: str


class QueryEntity(BaseModel):
    query: str
    sql: str


class FeedBackInput(BaseModel):
    feedback_type: str
    data_profiles: str
    query: str
    query_intent: str
    query_answer: str
    session_id: str = "-1"
    user_id: str = "admin"


class Option(BaseModel):
    data_profiles: list[str]
    bedrock_model_ids: list[str]


class CustomQuestion(BaseModel):
    custom_question: list[str]


class ChartEntity(BaseModel):
    chart_type: str
    chart_data: list[Any]


class SQLSearchResult(BaseModel):
    sql: str
    sql_data: list[Any]
    data_show_type: str
    sql_gen_process: str
    data_analyse: str
    sql_data_chart: list[ChartEntity]


class JSONSearchResult(BaseModel):
    json: str
    think_process: str


class TaskSQLSearchResult(BaseModel):
    sub_task_query: str
    sql_search_result: SQLSearchResult


class KnowledgeSearchResult(BaseModel):
    knowledge_response: str


class AgentSearchResult(BaseModel):
    agent_sql_search_result: list[TaskSQLSearchResult]
    agent_summary: str


class AskReplayResult(BaseModel):
    query_rewrite: str


class Answer(BaseModel):
    query: str
    query_rewrite: str = ""
    query_intent: str
    knowledge_search_result: KnowledgeSearchResult
    sql_search_result: SQLSearchResult
    agent_search_result: AgentSearchResult
    ask_rewrite_result: AskReplayResult
    suggested_question: list[str]


class SupersetAnswer(BaseModel):
    query: str
    query_intent: str
    knowledge_search_result: KnowledgeSearchResult
    json_search_result: JSONSearchResult
    agent_search_result: AgentSearchResult
    suggested_question: list[str]


class Message(BaseModel):
    type: str
    content: Union[str, Answer]


class DlsetMessage(BaseModel):
    type: str
    content: Union[str, SupersetAnswer]


class HistoryMessage(BaseModel):
    session_id: str
    messages: list[Message]
    title: str


class DlsetHistoryMessage(BaseModel):
    session_id: str
    messages: list[Message]
    title: str


class ChatHistory(BaseModel):
    messages: list[HistoryMessage]

import logging
import string

import pandas as pd

from api.schemas import Answer, KnowledgeSearchResult, SQLSearchResult, AgentSearchResult, AskReplayResult, \
    AskEntitySelect
from nlq.core.chat_context import ProcessingContext
from nlq.core.state import QueryState
from utils.apis import get_sql_result_tool
from utils.llm import get_query_intent, get_query_rewrite, knowledge_search, text_to_sql, data_analyse_tool, \
    generate_suggested_question
from utils.text_search import entity_retrieve_search, qa_retrieve_search
from utils.tool import get_generated_sql

logger = logging.getLogger(__name__)


class QueryStateMachine:
    def __init__(self, context: ProcessingContext):
        self.state = self.get_state_from_name("INITIAL")
        self.previous_state = self.get_state_from_name(context.previous_state)
        self.context = context
        self.answer = Answer(
            query="",
            query_rewrite="",
            query_intent="",
            knowledge_search_result=KnowledgeSearchResult(
                knowledge_response=""
            ),
            sql_search_result=SQLSearchResult(
                sql="",
                sql_data=[],
                data_show_type="",
                sql_gen_process="",
                data_analyse="",
                sql_data_chart=[]
            ),
            agent_search_result=AgentSearchResult(
                agent_sql_search_result=[],
                agent_summary=""
            ),
            ask_rewrite_result=AskReplayResult(
                query_rewrite=""
            ),
            suggested_question=[],
            ask_entity_select=AskEntitySelect(
                entity_select="",
                entity_info={}
            )
        )

        self.search_intent_flag = False
        self.reject_intent_flag = False
        self.agent_intent_flag = False
        self.knowledge_search_flag = False

        self.intent_search_result = {}
        self.agent_search_result = {}
        self.intent_response = {}
        self.entity_slot = []
        self.normal_search_entity_slot = []
        self.normal_search_qa_retrival = []
        self.agent_qa_retrieval = []

    def transition(self, new_state):
        self.state = new_state

    def get_answer(self):
        return self.answer

    def get_state(self):
        return self.state

    def get_state_from_name(self, state_name):
        if state_name == QueryState.INITIAL.name:
            return QueryState.INITIAL
        elif state_name == QueryState.ASK_ENTITY_SELECT:
            return QueryState.ASK_ENTITY_SELECT

    def run(self):
        if self.context.previous_state == QueryState.ASK_ENTITY_SELECT.name:
            self.transition(QueryState.COMPLETE)

        while self.state != QueryState.COMPLETE and self.state != QueryState.ERROR:
            if self.state == QueryState.INITIAL:
                self.handle_initial()
            elif self.get_state() == QueryState.REJECT_INTENT:
                self.handle_reject_intent()
            elif self.get_state() == QueryState.KNOWLEDGE_SEARCH:
                self.handle_knowledge_search()
            elif self.state == QueryState.ENTITY_RETRIEVAL:
                self.handle_entity_retrieval()
            elif self.state == QueryState.QA_RETRIEVAL:
                self.handle_qa_retrieval()
            elif self.state == QueryState.SQL_GENERATION:
                self.handle_sql_generation()
            elif self.state == QueryState.INTENT_RECOGNITION:
                self.handle_intent_recognition()
            elif self.state == QueryState.EXECUTE_QUERY:
                self.handle_execute_query()
            elif self.state == QueryState.ANALYZE_DATA:
                self.handle_analyze_data()
            elif self.state == QueryState.ASK_ENTITY_SELECT:
                self.handle_entity_selection()
            else:
                self.state = QueryState.ERROR

    def handle_initial(self):
        if self.context.context_window > 0:
            self._handle_query_rewrite()
        else:
            self.context.query_rewrite = self.context.search_box
            self.transition(QueryState.INTENT_RECOGNITION)

    def _handle_query_rewrite(self):
        query_rewrite_result = get_query_rewrite(self.context.model_type, self.context.search_box,
                                                 self.context.database_profile['prompt_map'],
                                                 self.context.user_query_history)
        query_rewrite_intent = query_rewrite_result.get("intent")
        self.context.query_rewrite = query_rewrite_result.get("query")
        if query_rewrite_intent == "ask_in_reply":
            self._set_ask_in_reply_result()
        else:
            self.answer.query_rewrite = query_rewrite_result.get("query")
            self.answer.query = self.context.search_box
            self.transition(QueryState.INTENT_RECOGNITION)

    def _set_ask_in_reply_result(self):
        self.answer.query = self.context.search_box
        self.answer.query_intent = "ask_in_reply"
        self.answer.query_rewrite = self.context.query_rewrite

        self.answer.ask_rewrite_result.query_rewrite = self.context.query_rewrite
        self.transition(QueryState.COMPLETE)

    def handle_entity_retrieval(self):
        self.normal_search_entity_slot = self._perform_entity_retrieval()
        same_name_entity = {}
        for each_entity in self.normal_search_entity_slot:
            if each_entity['_source']['entity_count'] > 1 and each_entity['_score'] > 0.98:
                same_name_entity[each_entity['_source']['entity']] = each_entity['_source']['entity_table_info']
        if len(same_name_entity) > 0:
            if self.context.previous_state != "ASK_ENTITY_SELECT":
                self.answer.ask_entity_select.entity_info = same_name_entity
                self.transition(QueryState.ASK_ENTITY_SELECT)
            else:
                self.transition(QueryState.QA_RETRIEVAL)
        else:
            self.transition(QueryState.QA_RETRIEVAL)

    def _perform_entity_retrieval(self):
        if self.context.use_rag_flag:
            return entity_retrieve_search(self.entity_slot, self.context.opensearch_info, self.context.selected_profile)
        else:
            return []

    def handle_qa_retrieval(self):
        self.normal_search_qa_retrival = self._perform_qa_retrieval()
        self.transition(QueryState.SQL_GENERATION)

    def _perform_qa_retrieval(self):
        if self.context.use_rag_flag:
            return qa_retrieve_search(self.context.query_rewrite, self.context.opensearch_info,
                                      self.context.selected_profile)
        return []

    def handle_sql_generation(self):
        sql, response = self._generate_sql()
        self.intent_search_result["sql"] = sql
        self.intent_search_result["response"] = response
        self.answer.sql_search_result.sql = sql
        self.answer.sql_search_result.sql_gen_process = get_generated_sql(response)
        if self.context.visualize_results_flag:
            self.transition(QueryState.EXECUTE_QUERY)
        else:
            self.transition(QueryState.COMPLETE)

    def _generate_sql(self):
        try:
            response = text_to_sql(self.context.database_profile['tables_info'], self.context.database_profile['hints'],
                                   self.context.database_profile['prompt_map'], self.context.query_rewrite,
                                   model_id=self.context.model_type, sql_examples=self.normal_search_qa_retrival,
                                   ner_example=self.normal_search_entity_slot,
                                   dialect=self.context.database_profile['db_type'])
            sql = get_generated_sql(response)
            return sql, response
        except Exception as e:
            logger.error("handle_sql_generation is error")
            logger.error(e)
            return "", ""

    def _generate_sql_again(self):
        try:
            response = text_to_sql(self.context.database_profile['tables_info'],
                                   self.context.database_profile['hints'],
                                   self.context.database_profile['prompt_map'],
                                   self.context.query_rewrite,
                                   model_id=self.context.model_type,
                                   sql_examples=self.normal_search_qa_retrival,
                                   ner_example=self.normal_search_entity_slot,
                                   dialect=self.context.database_profile['db_type'],
                                   model_provider=None,
                                   additional_info='''\n NOTE: when I try to write a SQL <sql>{sql_statement}</sql>, I got an error <error>{error}</error>. Please consider and avoid this problem. '''.format(
                                       sql_statement=self.intent_search_result["sql_execute_result"]["sql"],
                                       error=self.intent_search_result["sql_execute_result"]["error_info"]))
            sql = get_generated_sql(response)
            return sql, response
        except Exception as e:
            logger.error("handle_sql_generation is error")
            logger.error(e)
            return "", ""

    def handle_agent_sql_generation(self):
        pass

    def handle_intent_recognition(self):
        if self.context.intent_ner_recognition_flag:
            intent_response = get_query_intent(self.context.model_type, self.context.query_rewrite,
                                               self.context.database_profile['prompt_map'])
            self.intent_response = intent_response
            self._process_intent_response(intent_response)
        else:
            self.search_intent_flag = True
        self._transition_based_on_intent()

    def _process_intent_response(self, intent_response):
        intent = intent_response.get("intent", "normal_search")
        self.entity_slot = intent_response.get("slot", [])
        if intent == "reject_search":
            self.reject_intent_flag = True
            self.search_intent_flag = False
        elif intent == "agent_search":
            self.agent_intent_flag = True
            if self.context.agent_cot_flag:
                self.search_intent_flag = False
            else:
                self.search_intent_flag = True
                self.agent_intent_flag = False
        elif intent == "knowledge_search":
            self.knowledge_search_flag = True
            self.search_intent_flag = False
            self.agent_intent_flag = False
        else:
            self.search_intent_flag = True

    def _transition_based_on_intent(self):
        if self.reject_intent_flag:
            self.answer.query_intent = "reject_search"
            self.transition(QueryState.REJECT_INTENT)
        elif self.knowledge_search_flag:
            self.transition(QueryState.KNOWLEDGE_SEARCH)
        elif self.agent_intent_flag:
            self.answer.query_intent = "agent_search"
        else:
            self.answer.query_intent = "normal_search"
        self.transition(QueryState.ENTITY_RETRIEVAL)

    def handle_reject_intent(self):
        self.answer.query = self.context.search_box
        self.answer.query_rewrite = self.context.query_rewrite
        self.answer.query_intent = "reject_search"
        self.transition(QueryState.COMPLETE)

    def handle_knowledge_search(self):
        response = knowledge_search(search_box=self.context.query_rewrite, model_id=self.context.model_type,
                                    prompt_map=self.context.database_profile["prompt_map"])
        self.answer.query = self.context.search_box
        self.answer.query_rewrite = self.context.query_rewrite
        self.answer.query_intent = "knowledge_search"
        self.answer.knowledge_search_result.knowledge_response = response
        self.transition(QueryState.COMPLETE)

    def handle_entity_selection(self):
        # Handle entity selection
        entity_select_format = "根据您的描述，检索到多个相同名称的实体，请选择您想要查询的实体。\n"
        alphabet_list = list(string.ascii_uppercase)
        index = 0
        for entity in self.answer.ask_entity_select.entity_info:
            entity_value = self.answer.ask_entity_select.entity_info[entity]
            entity_name = entity
            entity_desc = "实体：" + entity_name + "，有如下维度值：\n"
            for each_value in entity_value:
                if index < len(alphabet_list):
                    entity_desc += alphabet_list[index] + " ："
                    entity_desc = entity_desc + "数据表：" + each_value["table_name"] + "，" + "列名是：" + each_value["column_name"] + "，" + "查询值是：" + each_value["value"] + "\n"
                    index = index + 1
            entity_select_format += entity_desc
        self.answer.query_intent = "entity_select"
        self.answer.ask_entity_select.entity_select = entity_select_format
        self.transition(QueryState.COMPLETE)

    def handle_execute_query(self):
        sql = self.intent_search_result.get("sql", "")
        sql_execute_result = self._execute_sql(sql)
        self.intent_search_result["sql_execute_result"] = sql_execute_result
        self.answer.sql_search_result.sql_data = sql_execute_result["data"]
        if self.context.data_with_analyse and sql_execute_result["status_code"] == 200:
            self.transition(QueryState.ANALYZE_DATA)
        elif sql_execute_result["status_code"] == 200:
            self.transition(QueryState.COMPLETE)
        elif sql_execute_result["status_code"] == 500 and self.context.auto_correction_flag:
            sql, response = self._generate_sql_again()
            sql_execute_result = self._execute_sql(sql)
            self.answer.sql_search_result.sql = sql
            self.answer.sql_search_result.sql_gen_process = get_generated_sql(response)
            self.intent_search_result["sql_execute_result"] = sql_execute_result
            self.answer.sql_search_result.sql_data = sql_execute_result["data"]
            if self.context.data_with_analyse and sql_execute_result["status_code"] == 200:
                self.transition(QueryState.ANALYZE_DATA)
            elif sql_execute_result["status_code"] == 200:
                self.transition(QueryState.COMPLETE)
            else:
                self.transition(QueryState.ERROR)
        else:
            self.transition(QueryState.ERROR)

    def _execute_sql(self, sql):
        if sql == "":
            return {"data": pd.DataFrame(), "sql": sql, "status_code": 500, "error_info": "The SQL is empty."}
        return get_sql_result_tool(self.context.database_profile, sql)

    def handle_analyze_data(self):
        # Analyze the data
        search_intent_analyse_result = data_analyse_tool(self.context.model_type,
                                                         self.context.database_profile['prompt_map'],
                                                         self.context.query_rewrite,
                                                         self.intent_search_result["sql_execute_result"][
                                                             "data"].to_json(
                                                             orient='records',
                                                             force_ascii=False), "query")
        self.answer.sql_search_result.data_analyse = search_intent_analyse_result
        self.transition(QueryState.COMPLETE)

    def handle_agent_analyze_data(self):
        # Analyze the data

        # search_intent_analyse_result = data_analyse_tool(self.context.model_type, prompt_map,
        #                                                      self.context.query_rewrite,
        #                                                      search_intent_result["data"].to_json(
        #                                                          orient='records',
        #                                                          force_ascii=False), "query")
        self.transition(QueryState.COMPLETE)

    def handle_suggest_question(self):
        # Handle suggest question
        if self.context.gen_suggested_question_flag:
            if self.search_intent_flag or self.agent_intent_flag:
                generated_sq = generate_suggested_question(self.context.database_profile['prompt_map'],
                                                           self.context.query_rewrite,
                                                           model_id=self.context.model_type)
                split_strings = generated_sq.split("[generate]")
                gen_sq_list = [s.strip() for s in split_strings if s.strip()]
                self.answer.suggested_question = gen_sq_list

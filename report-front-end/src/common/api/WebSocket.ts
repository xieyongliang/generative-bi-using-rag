import useWebSocket from "react-use-websocket";
import { DEFAULT_QUERY_CONFIG } from "../constant/constants";
import { SendJsonMessage } from "react-use-websocket/src/lib/types";
import { Dispatch, SetStateAction } from "react";
import { ChatBotHistoryItem, ChatBotMessageItem, ChatBotMessageType } from "../../components/chatbot-panel/types";
import cookie from 'react-cookies';
import { Global } from "../constant/global";
import { Session } from "../../components/session-panel/types";

export function createWssClient(
  setStatusMessage: Dispatch<SetStateAction<ChatBotMessageItem[]>>,
  setSessions: Dispatch<SetStateAction<Session[]>>
) {
  const socketUrl = process.env.VITE_WEBSOCKET_URL as string;
  const {sendJsonMessage}
    // eslint-disable-next-line react-hooks/rules-of-hooks
    = useWebSocket(socketUrl, {
    onOpen: () => console.log('opened'),
    //Will attempt to reconnect on all close events, such as server shutting down
    shouldReconnect: () => true,
    onMessage: (message) => handleWebSocketMessage(message)
  });

  const handleWebSocketMessage = (message: MessageEvent) => {
    console.log(message.data);
    const messageJson = JSON.parse(message.data);
    if (messageJson.content["X-Status-Code"] === 401) {
      const patchEvent = new CustomEvent("unauthorized", {
        detail: {},
      });
      window.dispatchEvent(patchEvent);
      return;
    } else if (messageJson.content["X-Status-Code"] === 200) {
      if (messageJson.content["X-User-Id"]) {
        const patchEvent = new CustomEvent("authorized", {
          detail: {
            userId: messageJson.content["X-User-Id"],
            userName: messageJson.content["X-User-Name"],
          },
        });
        window.dispatchEvent(patchEvent);
      }
    }
    if (messageJson.content_type === "state") {
      setStatusMessage((historyMessage) =>
        [...historyMessage, messageJson]);
    } else {
      setStatusMessage([]);
      setSessions((prevState) => {
        return prevState.map((session) => {
          if (messageJson.session_id !== session.session_id) {
            return session;
          } else {
            return {
              session_id: session.session_id,
              title: session.title,
              messages: [...session.messages, {
                type: ChatBotMessageType.AI,
                content: messageJson.content
              }]
            }
          }
        })
      });
    }
  };

  return sendJsonMessage;
}

export function queryWithWS(props: {
  query: string;
  configuration: any;
  sendMessage: SendJsonMessage;
  setMessageHistory: Dispatch<SetStateAction<ChatBotHistoryItem[]>>;
  setSessions: Dispatch<SetStateAction<Session[]>>;
  userId: string;
  sessionId: string;
}) {
  props.setSessions((prevState: any) => {
    return prevState.map((session: Session) => {
      if (props.sessionId !== session.session_id) {
        return session;
      } else {
        return {
          session_id: session.session_id,
          title: session.title === "New Chat" ? props.query : session.title,
          messages: [...session.messages, {
            type: ChatBotMessageType.Human,
            content: props.query
          }]
        }
      }
    })
  });
  const jwtToken = cookie.load("dlunifiedtoken") || "";
  const param = {
    query: props.query,
    bedrock_model_id: props.configuration.selectedLLM || DEFAULT_QUERY_CONFIG.selectedLLM,
    use_rag_flag: true,
    visualize_results_flag: true,
    intent_ner_recognition_flag: props.configuration.intentChecked,
    agent_cot_flag: props.configuration.complexChecked,
    profile_name: Global.profile ? Global.profile : props.configuration.selectedDataPro || DEFAULT_QUERY_CONFIG.selectedDataPro,
    explain_gen_process_flag: true,
    gen_suggested_question_flag: props.configuration.modelSuggestChecked,
    answer_with_insights: props.configuration.answerInsightChecked || DEFAULT_QUERY_CONFIG.answerInsightChecked,
    top_k: props.configuration.topK,
    top_p: props.configuration.topP,
    max_tokens: props.configuration.maxLength,
    temperature: props.configuration.temperature,
    context_window: props.configuration.contextWindow,
    session_id: props.sessionId,
    user_id: props.userId || "none",
    dlunifiedtoken: jwtToken
  };
  console.log("param: ", param);
  props.sendMessage(param);
}

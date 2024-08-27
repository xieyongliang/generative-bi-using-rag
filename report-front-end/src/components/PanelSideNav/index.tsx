import {
  Box,
  Button,
  ContentLayout,
  Header,
} from "@cloudscape-design/components";
import { useEffect } from "react";
import { useSelector } from "react-redux";
import { v4 as uuid } from "uuid";
import { getSessions } from "../../utils/api/API";
import { UserState } from "../../utils/helpers/types";
import "./style.scss";
import useGlobalContext from "../../hooks/useGlobalContext";

export const PanelSideNav = () => {
  const userInfo = useSelector((state: UserState) => state.userInfo);
  const queryConfig = useSelector((state: UserState) => state.queryConfig);
  const { setCurrentSessionId, setSessions, sessions, currentSessionId } =
    useGlobalContext();

  useEffect(() => {
    getSessions({
      user_id: userInfo.userId,
      profile_name: queryConfig.selectedDataPro,
    }).then((sessions) => {
      console.log({ sessions });
      if (sessions?.length) {
        return setSessions(sessions);
      }
      const sessionId = uuid();
      setSessions([
        {
          session_id: sessionId,
          title: "New Chat",
          messages: [],
        },
        ...sessions
          .filter((item: any) => item.session_id !== "")
          .map((item: any) => {
            return {
              session_id: item.session_id,
              title: item.title,
              messages: [],
            };
          }),
      ]);
      setCurrentSessionId(sessionId);
    });
  }, [
    userInfo.userId,
    queryConfig.selectedDataPro,
    setCurrentSessionId,
    setSessions,
  ]);

  return (
    <ContentLayout
      defaultPadding
      disableOverlap
      headerVariant="divider"
      header={<Header variant="h3">Chat Sessions</Header>}
    >
      <Box margin={{ top: "l" }}>
        <Button
          fullWidth
          iconName="add-plus"
          className="new_session_btn"
          onClick={() => {
            const sessionId = uuid();
            setSessions([
              {
                session_id: sessionId,
                title: "New Chat",
                messages: [],
              },
              ...sessions,
            ]);
            setCurrentSessionId(sessionId);
          }}
        >
          New Chat
        </Button>
        <div style={{ marginTop: 20 }}>
          {sessions?.map((ses, idx) => (
            <div
              key={idx}
              style={{
                backgroundColor:
                  ses.session_id === currentSessionId ? "lightgray" : "white",
              }}
              className="session_container"
            >
              <Button
                iconName="contact"
                className="session"
                onClick={() => {
                  console.log("Switch sessionId: ", ses);
                  setCurrentSessionId(ses.session_id);
                }}
              >
                {ses.title || "New Chat"}
              </Button>
            </div>
          ))}
        </div>
      </Box>
    </ContentLayout>
  );
};

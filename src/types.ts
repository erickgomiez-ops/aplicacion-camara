export type ChatMessage = {
  id: string;
  role: "user" | "assistant" | "system";
  text: string;
  timestamp: string;
};

export type AssistantStatus = "offline" | "booting" | "online" | "listening" | "speaking";

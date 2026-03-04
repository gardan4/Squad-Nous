export interface FieldInfo {
  name: string;
  type: string;
  description: string;
  required: boolean;
  format: string | null;
  enum: string[] | null;
}

export interface SchemaResponse {
  schema_version: string;
  title: string;
  description: string;
  fields: FieldInfo[];
}

export interface CreateSessionResponse {
  session_id: string;
  status: string;
}

export interface ChatRequest {
  session_id: string;
  message: string;
}

export interface ChatResponse {
  session_id: string;
  response: string;
  status: string;
  extracted_fields: Record<string, unknown>;
}

export interface Message {
  role: "user" | "assistant";
  content: string;
  timestamp?: string;
}

export interface DetectedField {
  name: string;
  type: string;
  description: string;
  enum: string[] | null;
}

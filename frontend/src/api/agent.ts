import { authFetch, authJson } from '../lib/auth';

const API_BASE_URL = '/api';

export interface AgentContribution {
    agent: string;
    reasoning: string[];
    confidence: string;
}

export interface AgentAction {
    type: string;
    data: string;
    description?: string;
}

export interface AgentResponse {
    message: string;
    session_id: string;
    agents_involved?: string[];
    agent_contributions?: AgentContribution[];
    metrics_used?: Record<string, unknown>;
    actions?: AgentAction[];
    timestamp?: string;
}

export interface FeedbackRequest {
    query_id: string;
    rating: number; // 1 or -1
    agent_name: string;
    comment?: string;
    original_query?: string;
}

export const agentApi = {
    /**
     * Send a query to the multi-agent system.
     */
    chatWithAgent: async (query: string, sessionId?: string): Promise<AgentResponse> => {
        try {
            return await authJson<AgentResponse>(`${API_BASE_URL}/chat/`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                message: query,
                session_id: sessionId
                }),
            });
        } catch (error) {
            console.error("Agent API Error:", error);
            throw error;
        }
    },

    /**
     * Submit user feedback.
     */
    submitFeedback: async (feedback: FeedbackRequest): Promise<void> => {
        try {
            const response = await authFetch(`${API_BASE_URL}/feedback/`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(feedback),
            });
            if (!response.ok) {
                throw new Error(`Feedback API failed (${response.status})`);
            }
        } catch (error) {
            console.error("Feedback API Error:", error);
            // Don't throw, just log
        }
    }
};

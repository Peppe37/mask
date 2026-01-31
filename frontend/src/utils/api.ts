export interface Project {
    id: string;
    name: string;
    description: string | null;
    context_summary: string | null;
    color: string;
    icon: string;
}

export interface ChatSession {
    id: string;
    created_at: string;
    title: string | null;
    project_id: string | null;
}

export interface ChatMessage {
    id?: string;
    role: 'user' | 'assistant' | 'system';
    content: string;
    created_at?: string;
}

const API_BASE_URL = 'http://localhost:8000/api';



export const api = {
    // --- Projects ---
    async createProject(name: string, description?: string): Promise<Project> {
        const response = await fetch(`${API_BASE_URL}/projects`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, description })
        });
        return response.json();
    },

    async listProjects(): Promise<Project[]> {
        const response = await fetch(`${API_BASE_URL}/projects`);
        return response.json();
    },

    async updateProjectSummary(projectId: string): Promise<void> {
        await fetch(`${API_BASE_URL}/projects/${projectId}/summary`, {
            method: 'POST'
        });
    },

    async updateProjectColor(projectId: string, color: string): Promise<void> {
        await fetch(`${API_BASE_URL}/projects/${projectId}/color`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ color })
        });
    },

    async updateProjectIcon(projectId: string, icon: string): Promise<void> {
        await fetch(`${API_BASE_URL}/projects/${projectId}/icon`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ icon })
        });
    },

    async deleteProject(projectId: string): Promise<void> {
        await fetch(`${API_BASE_URL}/projects/${projectId}`, {
            method: 'DELETE'
        });
    },

    // --- Sessions ---
    async createSession(title: string = "New Chat", projectId?: string): Promise<ChatSession> {
        const response = await fetch(`${API_BASE_URL}/sessions`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ title, project_id: projectId })
        });
        return response.json();
    },

    async listSessions(): Promise<ChatSession[]> {
        const response = await fetch(`${API_BASE_URL}/sessions`);
        return response.json();
    },

    async deleteSession(sessionId: string): Promise<void> {
        await fetch(`${API_BASE_URL}/sessions/${sessionId}`, {
            method: 'DELETE'
        });
    },

    async renameSession(sessionId: string, title: string): Promise<void> {
        await fetch(`${API_BASE_URL}/sessions/${sessionId}/rename`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ title })
        });
    },

    async assignSessionToProject(sessionId: string, projectId: string | null): Promise<void> {
        await fetch(`${API_BASE_URL}/sessions/${sessionId}/project`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ project_id: projectId })
        });
    },

    async generateSessionTitle(sessionId: string, firstMessage: string): Promise<{ title: string }> {
        const response = await fetch(`${API_BASE_URL}/sessions/${sessionId}/generate-title`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ first_message: firstMessage })
        });
        return response.json();
    },

    async getSessionMessages(sessionId: string): Promise<ChatMessage[]> {
        const response = await fetch(`${API_BASE_URL}/sessions/${sessionId}/messages`);
        return response.json();
    },

    async sendMessageStream(sessionId: string, message: string, onChunk: (chunk: string) => void): Promise<void> {
        const response = await fetch(`${API_BASE_URL}/chat`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ message, session_id: sessionId }),
        });

        if (!response.ok) {
            throw new Error('Network response was not ok');
        }

        const reader = response.body?.getReader();
        const decoder = new TextDecoder();

        while (true) {
            const { done, value } = await reader!.read();
            if (done) break;
            const chunk = decoder.decode(value, { stream: true });
            onChunk(chunk);
        }
    }
};

import React, { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import { MessageBubble } from './MessageBubble';
import { InputArea } from './InputArea';
import { TypingIndicator } from './TypingIndicator';
import { ThinkingStatus } from './ThinkingStatus';
import { api, type ChatSession, type Project } from '../utils/api';
import { applyTheme, loadBranding, getCurrentTheme } from '../utils/theme';
import { ContextMenu, type MenuItem } from './ContextMenu';
import { ColorPicker } from './ColorPicker';
import { IconPicker } from './IconPicker';

interface Message {
    role: 'user' | 'assistant';
    content: string;
}

export const ChatInterface: React.FC = () => {
    // State
    const [messages, setMessages] = useState<Message[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const [currentTheme, setCurrentTheme] = useState(getCurrentTheme());
    const [thinkingStatus, setThinkingStatus] = useState<string | null>(null);

    const [projects, setProjects] = useState<Project[]>([]);
    const [currentProject, setCurrentProject] = useState<Project | null>(null);

    const [sessions, setSessions] = useState<ChatSession[]>([]);
    const [currentSession, setCurrentSession] = useState<ChatSession | null>(null);

    // UI State for creating project
    const [isCreatingProject, setIsCreatingProject] = useState(false);
    const [newProjectName, setNewProjectName] = useState("");

    // Context Menu & Dialogs
    const [contextMenu, setContextMenu] = useState<{ x: number, y: number, items: MenuItem[] } | null>(null);
    const [renameInput, setRenameInput] = useState<{ type: 'chat' | 'project', id: string, value: string } | null>(null);
    const [assignDialog, setAssignDialog] = useState<string | null>(null); // session id
    const [colorPicker, setColorPicker] = useState<{ projectId: string, current: string } | null>(null);
    const [iconPicker, setIconPicker] = useState<{ projectId: string, current: string } | null>(null);

    // Track if this is the first message in a session
    const [messageCount, setMessageCount] = useState(0);

    const messagesEndRef = useRef<HTMLDivElement>(null);

    // Initial Load
    useEffect(() => {
        loadBranding().then(config => {
            applyTheme(currentTheme, config);
        });
        Promise.all([
            api.listProjects(),
            api.listSessions()
        ]).then(([loadedProjects, loadedSessions]) => {
            setProjects(loadedProjects);
            setSessions(loadedSessions);
        });
    }, [currentTheme]);

    // Scroll to bottom
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    // Load messages when session changes
    useEffect(() => {
        setMessages([]);
        setMessageCount(0);

        if (currentSession) {
            setIsLoading(true);
            api.getSessionMessages(currentSession.id)
                .then(loadedMessages => {
                    // Adapt backend messages to frontend format if needed
                    // Backend: { role, content, ... }
                    // Frontend Message: { role, content }
                    setMessages(loadedMessages.map(m => ({
                        role: m.role as 'user' | 'assistant',
                        content: m.content
                    })));
                    setMessageCount(loadedMessages.length);
                })
                .catch(console.error)
                .finally(() => setIsLoading(false));
        }
    }, [currentSession]);

    // Project handlers
    const handleCreateProject = async () => {
        if (!newProjectName.trim()) return;
        const project = await api.createProject(newProjectName);
        setProjects([project, ...projects]);
        setNewProjectName("");
        setIsCreatingProject(false);
    };

    const selectProject = (project: Project) => {
        setCurrentProject(project);
        const projectSessions = sessions.filter(s => s.project_id === project.id);
        if (projectSessions.length > 0) {
            setCurrentSession(projectSessions[0]);
        } else {
            setCurrentSession(null);
        }
    };

    // Session handlers
    const deleteCurrentSession = async () => {
        if (!currentSession) return;
        if (window.confirm("Are you sure you want to delete this chat?")) {
            await api.deleteSession(currentSession.id);
            setSessions(prev => prev.filter(s => s.id !== currentSession.id));
            setCurrentSession(null);
            setMessages([]);
        }
    };

    const handleSendMessage = async (content: string) => {
        if (!currentSession) {
            // Auto-create session if sending message without one
            const session = await api.createSession("New Chat", currentProject?.id);
            setSessions([session, ...sessions]);
            setCurrentSession(session);
            performSend(session.id, content);
            return;
        }
        performSend(currentSession.id, content);
    };

    const performSend = async (sessionId: string, content: string) => {
        const newUserMessage: Message = { role: 'user', content };
        setMessages(prev => [...prev, newUserMessage]);
        setIsLoading(true);

        // Auto-naming: if this is the first user message, generate title
        const isFirstMsg = messageCount === 0;

        try {
            let aiResponse = '';

            // NOTE: We do NOT add an empty assistant message immediately.
            // We wait for the stream to start or use the Loading indicator.

            await api.sendMessageStream(sessionId, content, (type, content) => {
                if (type === 'status') {
                    setThinkingStatus(content);
                } else if (type === 'token') {
                    // Clear thinking status once we get tokens (or keep it if mixed? usually clear or change to "Generating...")
                    setThinkingStatus(null);

                    setMessages(prev => {
                        const newMessages = [...prev];
                        const lastMsg = newMessages[newMessages.length - 1];

                        if (lastMsg && lastMsg.role === 'assistant') {
                            // Append to existing assistant message
                            lastMsg.content = aiResponse + content;
                        } else {
                            // First chunk! Add the assistant message
                            newMessages.push({ role: 'assistant', content: content });
                        }
                        return newMessages;
                    });
                    aiResponse += content;
                }
            });

            // Auto-naming separate process
            if (isFirstMsg) {
                api.generateSessionTitle(sessionId, content).then(result => {
                    setSessions(prev => prev.map(s =>
                        s.id === sessionId ? { ...s, title: result.title } : s
                    ));
                    if (currentSession?.id === sessionId) {
                        setCurrentSession(prev => prev ? { ...prev, title: result.title } : null);
                    }
                }).catch(console.error);
            }

            setMessageCount(prev => prev + 1);

            if (currentProject) {
                api.updateProjectSummary(currentProject.id).catch(console.error);
            }

        } catch (error) {
            console.error(error);
            setMessages(prev => [...prev, { role: 'assistant', content: 'Sorry, something went wrong.' }]);
        } finally {
            setIsLoading(false);
        }
    };




    const toggleTheme = async () => {
        const config = await loadBranding();
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        applyTheme(newTheme, config);
        setCurrentTheme(newTheme);
    };

    // Context Menu Handlers
    const handleChatRightClick = (e: React.MouseEvent, session: ChatSession) => {
        e.preventDefault();
        const items: MenuItem[] = [
            {
                label: 'Rename',
                onClick: () => setRenameInput({ type: 'chat', id: session.id, value: session.title || 'New Chat' })
            },
            {
                label: 'Assign to Project',
                onClick: () => setAssignDialog(session.id)
            },
            {
                label: 'Delete',
                onClick: async () => {
                    await api.deleteSession(session.id);
                    setSessions(prev => prev.filter(s => s.id !== session.id));
                    if (currentSession?.id === session.id) {
                        setCurrentSession(null);
                        setMessages([]);
                    }
                },
                danger: true
            }
        ];
        setContextMenu({ x: e.clientX, y: e.clientY, items });
    };

    const handleProjectRightClick = (e: React.MouseEvent, project: Project) => {
        e.preventDefault();
        const items: MenuItem[] = [
            {
                label: 'Rename',
                onClick: () => setRenameInput({ type: 'project', id: project.id, value: project.name })
            },
            {
                label: 'Change Color',
                onClick: () => setColorPicker({ projectId: project.id, current: project.color })
            },
            {
                label: 'Change Icon',
                onClick: () => setIconPicker({ projectId: project.id, current: project.icon })
            },
            {
                label: 'Delete',
                onClick: async () => {
                    if (window.confirm(`Delete project "${project.name}"?`)) {
                        await api.deleteProject(project.id);
                        setProjects(prev => prev.filter(p => p.id !== project.id));
                        if (currentProject?.id === project.id) {
                            setCurrentProject(null);
                        }
                    }
                },
                danger: true
            }
        ];
        setContextMenu({ x: e.clientX, y: e.clientY, items });
    };

    // Dialog Handlers
    const handleRenameSubmit = async () => {
        if (!renameInput) return;
        const { type, id, value } = renameInput;

        if (type === 'chat') {
            await api.renameSession(id, value);
            setSessions(prev => prev.map(s => s.id === id ? { ...s, title: value } : s));
            if (currentSession?.id === id) {
                setCurrentSession(prev => prev ? { ...prev, title: value } : null);
            }
        } else {
            await api.createProject(value); // This should be update, but we don't have that endpoint
            setProjects(prev => prev.map(p => p.id === id ? { ...p, name: value } : p));
        }
        setRenameInput(null);
    };

    const handleAssignToProject = async (projectId: string | null) => {
        if (!assignDialog) return;
        await api.assignSessionToProject(assignDialog, projectId);
        setSessions(prev => prev.map(s =>
            s.id === assignDialog ? { ...s, project_id: projectId } : s
        ));
        setAssignDialog(null);
    };

    const handleColorChange = async (color: string) => {
        if (!colorPicker) return;
        await api.updateProjectColor(colorPicker.projectId, color);
        setProjects(prev => prev.map(p =>
            p.id === colorPicker.projectId ? { ...p, color } : p
        ));
        if (currentProject?.id === colorPicker.projectId) {
            setCurrentProject(prev => prev ? { ...prev, color } : null);
        }
    };

    const handleIconChange = async (icon: string) => {
        if (!iconPicker) return;
        await api.updateProjectIcon(iconPicker.projectId, icon);
        setProjects(prev => prev.map(p =>
            p.id === iconPicker.projectId ? { ...p, icon } : p
        ));
        if (currentProject?.id === iconPicker.projectId) {
            setCurrentProject(prev => prev ? { ...prev, icon } : null);
        }
    };

    return (
        <div className="app-layout">
            {/* Sidebar */}
            <div className="sidebar">
                {/* Projects Section */}
                <div className="sidebar-header">
                    <h2>Projects</h2>
                    <button onClick={() => setIsCreatingProject(!isCreatingProject)}>
                        <svg viewBox="0 0 16 16" fill="currentColor">
                            <path d="M8 0a1 1 0 0 1 1 1v6h6a1 1 0 1 1 0 2H9v6a1 1 0 1 1-2 0V9H1a1 1 0 0 1 0-2h6V1a1 1 0 0 1 1-1z" />
                        </svg>
                    </button>
                </div>
                {isCreatingProject && (
                    <div className="new-project-form">
                        <input
                            type="text"
                            placeholder="Project name"
                            value={newProjectName}
                            onChange={(e) => setNewProjectName(e.target.value)}
                            onKeyDown={(e) => e.key === 'Enter' && handleCreateProject()}
                        />
                        <button onClick={handleCreateProject}>Create</button>
                    </div>
                )}
                <div className="project-list">
                    {projects.map(p => (
                        <div
                            key={p.id}
                            className={`project-item ${currentProject?.id === p.id ? 'active' : ''}`}
                            onClick={() => selectProject(p)}
                            onContextMenu={(e) => handleProjectRightClick(e, p)}
                            style={{ borderLeft: `3px solid ${p.color}` }}
                        >
                            <span className="project-icon">{p.icon}</span>
                            <span className="project-name">{p.name}</span>
                        </div>
                    ))}
                </div>

                <div className="sidebar-divider" />

                {/* Chats Section */}
                <div className="sidebar-header">
                    <h3>Chats</h3>
                    <button onClick={() => {
                        setCurrentSession(null);
                        setMessages([]);
                    }}>
                        <svg viewBox="0 0 16 16" fill="currentColor">
                            <path d="M8 0a1 1 0 0 1 1 1v6h6a1 1 0 1 1 0 2H9v6a1 1 0 1 1-2 0V9H1a1 1 0 0 1 0-2h6V1a1 1 0 0 1 1-1z" />
                        </svg>
                    </button>
                </div>
                <div className="session-list">
                    {sessions.filter(s => !currentProject || s.project_id === currentProject.id).map(s => (
                        <div
                            key={s.id}
                            className={`session-item ${currentSession?.id === s.id ? 'active' : ''}`}
                            onClick={() => setCurrentSession(s)}
                            onContextMenu={(e) => handleChatRightClick(e, s)}
                        >
                            <ReactMarkdown>{s.title || s.id.slice(0, 8)}</ReactMarkdown>
                        </div>
                    ))}
                </div>
            </div>

            {/* Main Chat Area */}
            <div className="chat-interface">
                <header className="chat-header">
                    <div className="header-controls">
                        <div className="logo-container">
                            <img src="/logo.svg" alt="Mask Logo" className="app-logo" />
                            <h1>Mask Agent</h1>
                        </div>
                        <div className="session-controls">
                            <button onClick={toggleTheme} className="theme-toggle" title="Toggle Theme">
                                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                    {currentTheme === 'dark' ? (
                                        <>
                                            <circle cx="12" cy="12" r="5" />
                                            <line x1="12" y1="1" x2="12" y2="3" />
                                            <line x1="12" y1="21" x2="12" y2="23" />
                                            <line x1="4.22" y1="4.22" x2="5.64" y2="5.64" />
                                            <line x1="18.36" y1="18.36" x2="19.78" y2="19.78" />
                                            <line x1="1" y1="12" x2="3" y2="12" />
                                            <line x1="21" y1="12" x2="23" y2="12" />
                                            <line x1="4.22" y1="19.78" x2="5.64" y2="18.36" />
                                            <line x1="18.36" y1="5.64" x2="19.78" y2="4.22" />
                                        </>
                                    ) : (
                                        <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
                                    )}
                                </svg>
                            </button>
                            {currentSession && (
                                <button onClick={deleteCurrentSession} className="control-btn delete-chat" title="Delete Chat">
                                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                        <polyline points="3 6 5 6 21 6" />
                                        <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                                        <line x1="10" y1="11" x2="10" y2="17" />
                                        <line x1="14" y1="11" x2="14" y2="17" />
                                    </svg>
                                </button>
                            )}
                        </div>
                    </div>
                    {currentProject && (
                        <div className="project-banner">
                            Project: <strong>{currentProject.name}</strong>
                            <span className="context-indicator" title={currentProject.context_summary || ""}>
                                Context Active
                            </span>
                        </div>
                    )}
                </header>

                <div className="messages-area">
                    {messages.length === 0 ? (
                        <div className="empty-state">
                            <p><strong>Welcome to Mask Agent!</strong></p>
                            <p>Start a conversation by typing a message below.</p>
                        </div>
                    ) : (
                        messages.map((msg, idx) => (
                            <MessageBubble key={idx} role={msg.role} content={msg.content} />
                        ))
                    )}
                    {isLoading && messages[messages.length - 1]?.role === 'user' && (
                        <>
                            <ThinkingStatus status={thinkingStatus} />
                            {!thinkingStatus && <TypingIndicator />}
                        </>
                    )}
                    <div ref={messagesEndRef} />
                </div>

                <InputArea onSendMessage={handleSendMessage} isLoading={isLoading} />
            </div>

            {/* Context Menu */}
            {contextMenu && (
                <ContextMenu
                    x={contextMenu.x}
                    y={contextMenu.y}
                    items={contextMenu.items}
                    onClose={() => setContextMenu(null)}
                />
            )}

            {/* Rename Dialog */}
            {renameInput && (
                <div className="dialog-overlay" onClick={() => setRenameInput(null)}>
                    <div className="dialog-content" onClick={e => e.stopPropagation()}>
                        <h3>Rename {renameInput.type === 'chat' ? 'Chat' : 'Project'}</h3>
                        <input
                            type="text"
                            value={renameInput.value}
                            onChange={e => setRenameInput({ ...renameInput, value: e.target.value })}
                            onKeyDown={e => e.key === 'Enter' && handleRenameSubmit()}
                            autoFocus
                        />
                        <div className="dialog-actions">
                            <button onClick={() => setRenameInput(null)}>Cancel</button>
                            <button onClick={handleRenameSubmit} className="primary">Rename</button>
                        </div>
                    </div>
                </div>
            )}

            {/* Assign to Project Dialog */}
            {assignDialog && (
                <div className="dialog-overlay" onClick={() => setAssignDialog(null)}>
                    <div className="dialog-content" onClick={e => e.stopPropagation()}>
                        <h3>Assign to Project</h3>
                        <div className="project-select-list">
                            <button onClick={() => handleAssignToProject(null)}>No Project</button>
                            {projects.map(p => (
                                <button key={p.id} onClick={() => handleAssignToProject(p.id)}>
                                    <span>{p.icon}</span> {p.name}
                                </button>
                            ))}
                        </div>
                    </div>
                </div>
            )}

            {/* Color Picker */}
            {colorPicker && (
                <ColorPicker
                    value={colorPicker.current}
                    onChange={handleColorChange}
                    onClose={() => setColorPicker(null)}
                />
            )}

            {/* Icon Picker */}
            {iconPicker && (
                <IconPicker
                    value={iconPicker.current}
                    onChange={handleIconChange}
                    onClose={() => setIconPicker(null)}
                />
            )}
        </div>
    );
};

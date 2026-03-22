import { useState, useRef, useEffect } from 'react'
import { Send, Bot, User, Sparkles, ChevronRight, ChevronLeft, Mic, MicOff, Activity, Timer, GitBranch, AlertTriangle } from 'lucide-react'
import { authFetch } from '../lib/auth'

const CHAT_MESSAGES_KEY = 'finagent_chat_messages'
const CHAT_TIMELINE_KEY = 'finagent_chat_timeline'
const CHAT_METRICS_KEY = 'finagent_chat_metrics'

interface ChatAction {
    type: string
    data: string
    description?: string
}

interface Message {
    id: string
    role: 'user' | 'assistant'
    content: string
    timestamp: Date
    agentsInvolved?: string[]
    reasoning?: string[]
    actions?: ChatAction[]
}

interface AgentContribution {
    agent: string
    reasoning: string[]
    confidence: string
}

interface ChatApiResponse {
    message: string
    session_id: string
    agents_involved?: string[]
    agent_contributions?: AgentContribution[]
    metrics_used?: Record<string, unknown>
    actions?: ChatAction[]
    timestamp?: string
}

type TimelineEventType = 'query' | 'agent' | 'system' | 'error'

interface TimelineEvent {
    id: string
    eventType: TimelineEventType
    title: string
    detail: string
    agent?: string
    confidence?: string
    timestamp: Date
}

interface RunMetrics {
    latencyMs: number | null
    agentsUsed: number
    reasoningSteps: number
    actionsTriggered: number
    confidenceSummary: string
    requestStatus: 'idle' | 'processing' | 'success' | 'error'
    lastUpdated: Date | null
    apiMetrics: Record<string, unknown>
}

interface WebkitSpeechRecognitionResult {
    transcript: string
}

interface WebkitSpeechRecognitionEvent extends Event {
    results: ArrayLike<ArrayLike<WebkitSpeechRecognitionResult>>
}

interface WebkitSpeechRecognitionErrorEvent extends Event {
    error: string
}

interface WebkitSpeechRecognition {
    continuous: boolean
    interimResults: boolean
    lang: string
    onresult: ((event: WebkitSpeechRecognitionEvent) => void) | null
    onerror: ((event: WebkitSpeechRecognitionErrorEvent) => void) | null
    onend: (() => void) | null
    start: () => void
    stop: () => void
}

interface WebkitSpeechRecognitionConstructor {
    new(): WebkitSpeechRecognition
}

declare global {
    interface Window {
        webkitSpeechRecognition?: WebkitSpeechRecognitionConstructor
    }
}

const confidenceBadgeClass = (confidence: string) => {
    const normalized = confidence.toUpperCase()
    if (normalized.includes('HIGH')) return 'badge-success'
    if (normalized.includes('MEDIUM')) return 'badge-warning'
    if (normalized.includes('LOW')) return 'badge-danger'
    return 'badge-info'
}

const summarizeConfidence = (contributions: AgentContribution[]): string => {
    if (contributions.length === 0) return 'N/A'

    const normalized = contributions.map((c) => c.confidence.toUpperCase())
    const highCount = normalized.filter((c) => c.includes('HIGH')).length
    const mediumCount = normalized.filter((c) => c.includes('MEDIUM')).length

    if (highCount === normalized.length) return 'HIGH'
    if (highCount > 0 && mediumCount > 0) return 'MIXED'
    if (highCount > 0) return 'MEDIUM-HIGH'
    if (mediumCount > 0) return 'MEDIUM'
    return 'LOW'
}

const metricValueToText = (value: unknown): string => {
    if (value === undefined || value === null) return 'N/A'
    if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') {
        return String(value)
    }
    try {
        return JSON.stringify(value)
    } catch {
        return 'N/A'
    }
}

const defaultWelcomeMessage: Message = {
    id: '1',
    role: 'assistant',
    content: "Hello! I'm your AI Financial Advisor. I can help you with investment decisions, retirement planning, budget analysis, and more. All your data stays private and is processed locally. How can I help you today?",
    timestamp: new Date(),
    agentsInvolved: ['orchestrator'],
}

const defaultTimeline: TimelineEvent[] = [{
    id: 'timeline-bootstrap',
    eventType: 'system',
    title: 'Session Ready',
    detail: 'Live agent timeline initialized.',
    timestamp: new Date(),
}]

const defaultMetrics: RunMetrics = {
    latencyMs: null,
    agentsUsed: 0,
    reasoningSteps: 0,
    actionsTriggered: 0,
    confidenceSummary: 'N/A',
    requestStatus: 'idle',
    lastUpdated: null,
    apiMetrics: {},
}

function loadFromSession<T>(key: string, fallback: T): T {
    try {
        const raw = sessionStorage.getItem(key)
        if (raw) {
            const parsed = JSON.parse(raw)
            // Restore Date objects from ISO strings
            if (Array.isArray(parsed)) {
                return parsed.map((item: Record<string, unknown>) => ({
                    ...item,
                    timestamp: item.timestamp ? new Date(item.timestamp as string) : new Date(),
                })) as T
            }
            if (parsed && typeof parsed === 'object' && 'lastUpdated' in parsed) {
                return {
                    ...parsed,
                    lastUpdated: parsed.lastUpdated ? new Date(parsed.lastUpdated) : null,
                } as T
            }
            return parsed as T
        }
    } catch { /* ignore */ }
    return fallback
}

export default function ChatPage() {
    const [messages, setMessages] = useState<Message[]>(() =>
        loadFromSession<Message[]>(CHAT_MESSAGES_KEY, [defaultWelcomeMessage])
    )
    const [input, setInput] = useState('')
    const [isLoading, setIsLoading] = useState(false)
    const [showReasoning, setShowReasoning] = useState(true)
    const [sessionId, setSessionId] = useState<string | null>(() => localStorage.getItem('finagent_session_id'))
    const [timelineEvents, setTimelineEvents] = useState<TimelineEvent[]>(() =>
        loadFromSession<TimelineEvent[]>(CHAT_TIMELINE_KEY, defaultTimeline)
    )
    const [runMetrics, setRunMetrics] = useState<RunMetrics>(() =>
        loadFromSession<RunMetrics>(CHAT_METRICS_KEY, defaultMetrics)
    )
    const messagesEndRef = useRef<HTMLDivElement>(null)

    // Persist messages to sessionStorage whenever they change
    useEffect(() => {
        sessionStorage.setItem(CHAT_MESSAGES_KEY, JSON.stringify(messages))
    }, [messages])

    // Persist timeline events
    useEffect(() => {
        sessionStorage.setItem(CHAT_TIMELINE_KEY, JSON.stringify(timelineEvents))
    }, [timelineEvents])

    // Persist run metrics
    useEffect(() => {
        sessionStorage.setItem(CHAT_METRICS_KEY, JSON.stringify(runMetrics))
    }, [runMetrics])

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }

    useEffect(() => {
        scrollToBottom()
    }, [messages])

    // Voice Interface
    const [isListening, setIsListening] = useState(false)
    const recognitionRef = useRef<WebkitSpeechRecognition | null>(null)

    useEffect(() => {
        if (window.webkitSpeechRecognition) {
            const SpeechRecognition = window.webkitSpeechRecognition
            recognitionRef.current = new SpeechRecognition()
            recognitionRef.current.continuous = false
            recognitionRef.current.interimResults = false
            recognitionRef.current.lang = 'en-US' // Default to English, can be dynamic based on I18nContext

            recognitionRef.current.onresult = (event: WebkitSpeechRecognitionEvent) => {
                const transcript = event.results[0][0].transcript
                setInput(prev => prev + (prev ? ' ' : '') + transcript)
                setIsListening(false)
            }

            recognitionRef.current.onerror = (event: WebkitSpeechRecognitionErrorEvent) => {
                console.error('Speech recognition error', event.error)
                setIsListening(false)
            }

            recognitionRef.current.onend = () => {
                setIsListening(false)
            }
        }
    }, [])

    const toggleListening = () => {
        if (isListening) {
            recognitionRef.current?.stop()
        } else {
            setIsListening(true)
            recognitionRef.current?.start()
        }
    }

    const addTimelineEvent = (event: Omit<TimelineEvent, 'id' | 'timestamp'>) => {
        const timelineEvent: TimelineEvent = {
            id: `${Date.now()}-${Math.random().toString(16).slice(2, 8)}`,
            timestamp: new Date(),
            ...event,
        }
        setTimelineEvents((prev) => [timelineEvent, ...prev].slice(0, 80))
    }

    const handleSend = async () => {
        const queryText = input.trim()
        if (!queryText || isLoading) return

        const userMessage: Message = {
            id: Date.now().toString(),
            role: 'user',
            content: queryText,
            timestamp: new Date(),
        }

        setMessages(prev => [...prev, userMessage])
        setInput('')
        setIsLoading(true)
        setRunMetrics((prev) => ({
            ...prev,
            requestStatus: 'processing',
        }))
        addTimelineEvent({
            eventType: 'query',
            title: 'User Query Submitted',
            detail: queryText,
        })
        addTimelineEvent({
            eventType: 'system',
            title: 'Orchestrator Routing',
            detail: 'Selecting and coordinating specialized agents.',
        })

        const requestStartedAt = performance.now()

        try {
            const response = await authFetch('/api/chat/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: queryText, session_id: sessionId }),
            })

            if (!response.ok) {
                throw new Error(`Chat request failed with status ${response.status}`)
            }

            const data: ChatApiResponse = await response.json()
            const contributions = data.agent_contributions || []
            const agentsInvolved = data.agents_involved || []
            const actions = data.actions || []
            const reasoningSteps = contributions.reduce((sum, contribution) => sum + contribution.reasoning.length, 0)
            const latencyMs = Math.round(performance.now() - requestStartedAt)

            if (data.session_id && data.session_id !== sessionId) {
                setSessionId(data.session_id)
                localStorage.setItem('finagent_session_id', data.session_id)
            }

            const assistantMessage: Message = {
                id: (Date.now() + 1).toString(),
                role: 'assistant',
                content: data.message,
                timestamp: new Date(),
                agentsInvolved,
                reasoning: contributions.flatMap((c: AgentContribution) => c.reasoning),
                actions,
            }

            setMessages(prev => [...prev, assistantMessage])
            setRunMetrics({
                latencyMs,
                agentsUsed: agentsInvolved.length,
                reasoningSteps,
                actionsTriggered: actions.length,
                confidenceSummary: summarizeConfidence(contributions),
                requestStatus: 'success',
                lastUpdated: new Date(),
                apiMetrics: data.metrics_used || {},
            })

            if (contributions.length > 0) {
                for (const contribution of contributions) {
                    addTimelineEvent({
                        eventType: 'agent',
                        title: `${contribution.agent} completed`,
                        detail: contribution.reasoning[0] || 'Agent finished analysis.',
                        agent: contribution.agent,
                        confidence: contribution.confidence,
                    })
                }
            } else {
                for (const agentName of agentsInvolved) {
                    addTimelineEvent({
                        eventType: 'agent',
                        title: `${agentName} completed`,
                        detail: 'Agent contributed to final response.',
                        agent: agentName,
                    })
                }
            }

            addTimelineEvent({
                eventType: 'system',
                title: 'Response Delivered',
                detail: `Completed in ${latencyMs} ms.`,
            })
        } catch (error) {
            console.error('Chat request failed:', error)
            setRunMetrics((prev) => ({
                ...prev,
                requestStatus: 'error',
                lastUpdated: new Date(),
            }))
            addTimelineEvent({
                eventType: 'error',
                title: 'Request Failed',
                detail: error instanceof Error ? error.message : 'Unexpected chat error.',
            })
            const errorMessage: Message = {
                id: (Date.now() + 1).toString(),
                role: 'assistant',
                content: "I'm having trouble connecting to the backend. Please make sure the server is running on port 8000.",
                timestamp: new Date(),
            }
            setMessages(prev => [...prev, errorMessage])
        } finally {
            setIsLoading(false)
        }
    }

    const latestAgents = messages
        .slice()
        .reverse()
        .find((msg) => msg.role === 'assistant' && msg.agentsInvolved && msg.agentsInvolved.length > 0)
        ?.agentsInvolved || []

    const statusText = runMetrics.requestStatus === 'processing'
        ? 'Processing'
        : runMetrics.requestStatus === 'success'
            ? 'Ready'
            : runMetrics.requestStatus === 'error'
                ? 'Error'
                : 'Idle'

    return (
        <div className="flex h-[calc(100vh-4rem)] gap-6">
            {/* Chat Panel */}
            <div className={`flex-1 flex flex-col transition-all duration-300 ${showReasoning ? '' : 'max-w-4xl mx-auto'}`}>
                <div className="mb-6">
                    <h1 className="text-3xl font-bold gradient-text">AI Financial Advisor</h1>
                    <p className="text-slate-400 mt-1">Get personalized financial guidance powered by multi-agent AI</p>
                </div>

                {/* Messages */}
                <div className="flex-1 overflow-auto space-y-4 pr-2">
                    {messages.map((msg) => (
                        <div
                            key={msg.id}
                            className={`flex gap-4 animate-fadeIn ${msg.role === 'user' ? 'justify-end' : ''}`}
                        >
                            {msg.role === 'assistant' && (
                                <div className="w-10 h-10 rounded-xl gradient-accent flex items-center justify-center flex-shrink-0">
                                    <Bot className="w-5 h-5 text-white" />
                                </div>
                            )}

                            <div className={`max-w-2xl ${msg.role === 'user' ? 'order-first' : ''}`}>
                                <div
                                    className={`rounded-2xl p-4 ${msg.role === 'user'
                                        ? 'bg-primary-600 text-white'
                                        : 'glass'
                                        }`}
                                >
                                    <p className="whitespace-pre-wrap">{msg.content}</p>
                                </div>

                                {msg.actions && msg.actions.map((action, idx) => (
                                    action.type === 'image' && (
                                        <div key={idx} className="mt-3 glass rounded-xl p-2">
                                            <img
                                                src={action.data}
                                                alt={action.description || 'Generated Chart'}
                                                className="rounded-lg w-full"
                                            />
                                            {action.description && (
                                                <p className="text-xs text-center text-slate-400 mt-2">{action.description}</p>
                                            )}
                                        </div>
                                    )
                                ))}

                                {msg.agentsInvolved && msg.agentsInvolved.length > 0 && (
                                    <div className="flex items-center gap-2 mt-2 flex-wrap">
                                        <span className="text-xs text-slate-500">Agents:</span>
                                        {msg.agentsInvolved.map((agent) => (
                                            <span key={agent} className="badge badge-info">
                                                {agent}
                                            </span>
                                        ))}
                                    </div>
                                )}
                            </div>

                            {msg.role === 'user' && (
                                <div className="w-10 h-10 rounded-xl bg-slate-700 flex items-center justify-center flex-shrink-0">
                                    <User className="w-5 h-5 text-slate-300" />
                                </div>
                            )}
                        </div>
                    ))}

                    {isLoading && (
                        <div className="flex gap-4 animate-fadeIn">
                            <div className="w-10 h-10 rounded-xl gradient-accent flex items-center justify-center">
                                <Sparkles className="w-5 h-5 text-white animate-pulse" />
                            </div>
                            <div className="glass rounded-2xl p-4">
                                <div className="flex items-center gap-2">
                                    <div className="w-2 h-2 bg-primary-400 rounded-full animate-bounce" />
                                    <div className="w-2 h-2 bg-primary-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }} />
                                    <div className="w-2 h-2 bg-primary-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }} />
                                    <span className="text-slate-400 ml-2">Analyzing with multi-agent system...</span>
                                </div>
                            </div>
                        </div>
                    )}

                    <div ref={messagesEndRef} />
                </div>

                {/* Input */}
                <div className="mt-4">
                    <div className="glass rounded-2xl p-4 flex gap-4">
                        <input
                            type="text"
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                            placeholder="Ask about investments, retirement, budget analysis..."
                            className="flex-1 bg-transparent border-none outline-none text-slate-100 placeholder-slate-500"
                        />
                        <button
                            onClick={toggleListening}
                            className={`p-2 rounded-xl transition-colors ${isListening ? 'bg-red-500/20 text-red-400 animate-pulse' : 'hover:bg-slate-700/50 text-slate-400'
                                }`}
                            title="Voice Input"
                        >
                            {isListening ? <MicOff className="w-5 h-5" /> : <Mic className="w-5 h-5" />}
                        </button>
                        <button
                            onClick={handleSend}
                            disabled={isLoading || !input.trim()}
                            className="btn-primary flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                            <Send className="w-4 h-4" />
                            Send
                        </button>
                    </div>
                    <p className="text-xs text-slate-500 mt-2 text-center">
                        🔒 Your data is processed locally and never sent to external servers
                    </p>
                </div>
            </div>

            {/* Reasoning Panel Toggle */}
            <button
                onClick={() => setShowReasoning(!showReasoning)}
                className="fixed right-0 top-1/2 -translate-y-1/2 glass-dark p-2 rounded-l-xl z-10"
            >
                {showReasoning ? <ChevronRight className="w-5 h-5" /> : <ChevronLeft className="w-5 h-5" />}
            </button>

            {/* Reasoning Panel */}
            {showReasoning && (
                <div className="w-96 glass-dark rounded-2xl p-6 animate-fadeIn overflow-auto">
                    <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
                        <GitBranch className="w-5 h-5 text-primary-400" />
                        Live Agent Timeline
                    </h2>

                    <div className="space-y-4">
                        <div className="glass rounded-xl p-4">
                            <h3 className="text-sm font-medium text-slate-300 mb-3 flex items-center gap-2">
                                <Activity className="w-4 h-4 text-primary-400" />
                                Run Metrics
                            </h3>
                            <div className="grid grid-cols-2 gap-2 text-xs">
                                <div className="bg-slate-900/50 rounded-lg p-2">
                                    <div className="text-slate-400">Status</div>
                                    <div className={`font-semibold ${runMetrics.requestStatus === 'error' ? 'text-red-400' : runMetrics.requestStatus === 'processing' ? 'text-yellow-400' : 'text-green-400'}`}>
                                        {statusText}
                                    </div>
                                </div>
                                <div className="bg-slate-900/50 rounded-lg p-2">
                                    <div className="text-slate-400">Latency</div>
                                    <div className="font-semibold text-slate-100">
                                        {runMetrics.latencyMs !== null ? `${runMetrics.latencyMs} ms` : 'N/A'}
                                    </div>
                                </div>
                                <div className="bg-slate-900/50 rounded-lg p-2">
                                    <div className="text-slate-400">Agents</div>
                                    <div className="font-semibold text-slate-100">{runMetrics.agentsUsed}</div>
                                </div>
                                <div className="bg-slate-900/50 rounded-lg p-2">
                                    <div className="text-slate-400">Reasoning Steps</div>
                                    <div className="font-semibold text-slate-100">{runMetrics.reasoningSteps}</div>
                                </div>
                                <div className="bg-slate-900/50 rounded-lg p-2">
                                    <div className="text-slate-400">Actions</div>
                                    <div className="font-semibold text-slate-100">{runMetrics.actionsTriggered}</div>
                                </div>
                                <div className="bg-slate-900/50 rounded-lg p-2">
                                    <div className="text-slate-400">Confidence</div>
                                    <div className="font-semibold text-primary-300">{runMetrics.confidenceSummary}</div>
                                </div>
                            </div>
                            {runMetrics.lastUpdated && (
                                <div className="mt-3 text-xs text-slate-500 flex items-center gap-1">
                                    <Timer className="w-3 h-3" />
                                    Last run: {runMetrics.lastUpdated.toLocaleTimeString()}
                                </div>
                            )}
                        </div>

                        <div className="glass rounded-xl p-4">
                            <h3 className="text-sm font-medium text-slate-300 mb-2">Latest Agents</h3>
                            <div className="flex flex-wrap gap-2">
                                {latestAgents.length > 0 ? latestAgents.map((agent) => (
                                    <span key={agent} className="badge badge-info">
                                        {agent}
                                    </span>
                                )) : <span className="text-xs text-slate-500">No agent run yet</span>}
                            </div>
                        </div>

                        <div className="glass rounded-xl p-4">
                            <h3 className="text-sm font-medium text-slate-300 mb-2">Backend Metrics</h3>
                            {Object.keys(runMetrics.apiMetrics).length === 0 ? (
                                <p className="text-xs text-slate-500">No backend metrics returned for the last run.</p>
                            ) : (
                                <div className="space-y-2">
                                    {Object.entries(runMetrics.apiMetrics).map(([key, value]) => (
                                        <div key={key} className="flex items-start justify-between gap-2 text-xs">
                                            <span className="text-slate-400">{key}</span>
                                            <span className="text-slate-200 text-right break-all max-w-[70%]">
                                                {metricValueToText(value)}
                                            </span>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>

                        <div className="glass rounded-xl p-4">
                            <h3 className="text-sm font-medium text-slate-300 mb-3">Execution Timeline</h3>
                            <div className="space-y-3 max-h-[360px] overflow-auto pr-1">
                                {timelineEvents.map((event) => (
                                    <div key={event.id} className="border-l border-slate-700 pl-3">
                                        <div className="flex items-center justify-between gap-2">
                                            <div className="flex items-center gap-2 min-w-0">
                                                <span
                                                    className={`w-2 h-2 rounded-full flex-shrink-0 ${event.eventType === 'error'
                                                        ? 'bg-red-500'
                                                        : event.eventType === 'agent'
                                                            ? 'bg-primary-400'
                                                            : event.eventType === 'query'
                                                                ? 'bg-blue-400'
                                                                : 'bg-slate-400'
                                                        }`}
                                                />
                                                <p className="text-xs text-slate-100 truncate">{event.title}</p>
                                            </div>
                                            <span className="text-[10px] text-slate-500 flex-shrink-0">
                                                {event.timestamp.toLocaleTimeString()}
                                            </span>
                                        </div>
                                        <p className="text-xs text-slate-400 mt-1">{event.detail}</p>
                                        <div className="mt-2 flex items-center gap-2 flex-wrap">
                                            {event.agent && (
                                                <span className="badge badge-info text-[10px]">{event.agent}</span>
                                            )}
                                            {event.confidence && (
                                                <span className={`badge text-[10px] ${confidenceBadgeClass(event.confidence)}`}>
                                                    {event.confidence}
                                                </span>
                                            )}
                                            {event.eventType === 'error' && (
                                                <span className="inline-flex items-center gap-1 text-[10px] text-red-400">
                                                    <AlertTriangle className="w-3 h-3" />
                                                    Check backend logs
                                                </span>
                                            )}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    )
}

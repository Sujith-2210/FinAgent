import { useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import { Bot, Activity, Zap, Shield, Clock } from 'lucide-react'
import { authJson } from '../lib/auth'

interface Agent {
    name: string
    description: string
    status: string
    last_invoked: string | null
    read_layers: string[]
    write_layers: string[]
}

interface AgentsData {
    agents: Agent[]
    total: number
    active_count: number
}

const agentIcons: Record<string, ReactNode> = {
    orchestrator: <Zap className="w-5 h-5" />,
    finance_reasoning: <Activity className="w-5 h-5" />,
    knowledge: <Bot className="w-5 h-5" />,
    explainability: <Bot className="w-5 h-5" />,
    alert: <Shield className="w-5 h-5" />,
}

const agentColors: Record<string, string> = {
    orchestrator: 'from-blue-500 to-blue-600',
    finance_reasoning: 'from-green-500 to-green-600',
    knowledge: 'from-orange-500 to-orange-600',
    explainability: 'from-purple-500 to-purple-600',
    alert: 'from-red-500 to-red-600',
}

export default function AgentsPage() {
    const [data, setData] = useState<AgentsData | null>(null)
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        let active = true
        const loadStatus = async () => {
            try {
                const payload = await authJson<AgentsData>('/api/agents/status')
                if (!active) return
                setData(payload)
            } catch (error) {
                console.error('Failed to fetch agent status:', error)
            } finally {
                if (active) {
                    setLoading(false)
                }
            }
        }

        void loadStatus()
        return () => {
            active = false
        }
    }, [])

    if (loading) {
        return (
            <div className="flex items-center justify-center h-64">
                <div className="animate-spin w-8 h-8 border-2 border-primary-400 border-t-transparent rounded-full" />
            </div>
        )
    }

    return (
        <div className="space-y-8">
            <div>
                <h1 className="text-3xl font-bold gradient-text">Multi-Agent System</h1>
                <p className="text-slate-400 mt-1">Monitor and manage your AI agents</p>
            </div>

            {/* Summary */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="glass rounded-xl p-4">
                    <div className="text-sm text-slate-400 mb-1">Total Agents</div>
                    <div className="text-3xl font-bold">{data?.total || 0}</div>
                </div>
                <div className="glass rounded-xl p-4">
                    <div className="text-sm text-slate-400 mb-1">Active Now</div>
                    <div className="text-3xl font-bold text-green-400">{data?.active_count || 0}</div>
                </div>
                <div className="glass rounded-xl p-4">
                    <div className="text-sm text-slate-400 mb-1">System Status</div>
                    <div className="flex items-center gap-2">
                        <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
                        <span className="text-green-400">Operational</span>
                    </div>
                </div>
            </div>

            {/* Agent Cards */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {data?.agents.map((agent) => (
                    <div key={agent.name} className="glass rounded-2xl overflow-hidden">
                        {/* Header */}
                        <div className={`bg-gradient-to-r ${agentColors[agent.name] || 'from-slate-500 to-slate-600'} p-4`}>
                            <div className="flex items-center justify-between">
                                <div className="flex items-center gap-3">
                                    <div className="w-10 h-10 rounded-xl bg-white/20 flex items-center justify-center text-white">
                                        {agentIcons[agent.name] || <Bot className="w-5 h-5" />}
                                    </div>
                                    <div>
                                        <h3 className="font-semibold text-white capitalize">
                                            {agent.name.replace(/_/g, ' ')}
                                        </h3>
                                        <div className="flex items-center gap-2">
                                            <div className={`w-2 h-2 rounded-full ${agent.status === 'active' ? 'bg-green-400 animate-pulse' : 'bg-gray-400'
                                                }`} />
                                            <span className="text-sm text-white/80">{agent.status}</span>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>

                        {/* Body */}
                        <div className="p-4 space-y-4">
                            <p className="text-sm text-slate-400">{agent.description}</p>

                            {/* Read Layers */}
                            <div>
                                <h4 className="text-xs font-medium text-slate-500 uppercase mb-2">Read Access</h4>
                                <div className="flex flex-wrap gap-1">
                                    {agent.read_layers.map((layer) => (
                                        <span key={layer} className="badge badge-info text-xs">
                                            {layer.replace(/_/g, ' ')}
                                        </span>
                                    ))}
                                </div>
                            </div>

                            {/* Write Layers */}
                            <div>
                                <h4 className="text-xs font-medium text-slate-500 uppercase mb-2">Write Access</h4>
                                <div className="flex flex-wrap gap-1">
                                    {agent.write_layers.map((layer) => (
                                        <span key={layer} className="badge badge-warning text-xs">
                                            {layer.replace(/_/g, ' ')}
                                        </span>
                                    ))}
                                </div>
                            </div>

                            {/* Last Invoked */}
                            <div className="flex items-center gap-2 text-xs text-slate-500">
                                <Clock className="w-3 h-3" />
                                <span>
                                    Last invoked: {agent.last_invoked || 'Never'}
                                </span>
                            </div>
                        </div>
                    </div>
                ))}
            </div>

            {/* Agent Architecture */}
            <div className="glass rounded-2xl p-6">
                <h2 className="text-lg font-semibold mb-4">Agent Collaboration Flow</h2>
                <div className="flex items-center justify-center gap-4 overflow-x-auto py-4">
                    <div className="text-center">
                        <div className="w-16 h-16 rounded-full bg-slate-700 flex items-center justify-center mx-auto mb-2">
                            👤
                        </div>
                        <span className="text-sm text-slate-400">User</span>
                    </div>
                    <div className="text-2xl text-slate-600">→</div>
                    <div className="text-center">
                        <div className="w-16 h-16 rounded-full bg-gradient-to-r from-blue-500 to-blue-600 flex items-center justify-center mx-auto mb-2">
                            <Zap className="w-6 h-6 text-white" />
                        </div>
                        <span className="text-sm text-slate-400">Orchestrator</span>
                    </div>
                    <div className="text-2xl text-slate-600">→</div>
                    <div className="flex gap-2">
                        <div className="text-center">
                            <div className="w-12 h-12 rounded-full bg-gradient-to-r from-green-500 to-green-600 flex items-center justify-center mx-auto mb-2">
                                <Activity className="w-5 h-5 text-white" />
                            </div>
                            <span className="text-xs text-slate-400">Finance</span>
                        </div>
                        <div className="text-center">
                            <div className="w-12 h-12 rounded-full bg-gradient-to-r from-orange-500 to-orange-600 flex items-center justify-center mx-auto mb-2">
                                <Bot className="w-5 h-5 text-white" />
                            </div>
                            <span className="text-xs text-slate-400">Knowledge</span>
                        </div>
                    </div>
                    <div className="text-2xl text-slate-600">→</div>
                    <div className="text-center">
                        <div className="w-16 h-16 rounded-full bg-gradient-to-r from-purple-500 to-purple-600 flex items-center justify-center mx-auto mb-2">
                            <Bot className="w-6 h-6 text-white" />
                        </div>
                        <span className="text-sm text-slate-400">Explainability</span>
                    </div>
                    <div className="text-2xl text-slate-600">→</div>
                    <div className="text-center">
                        <div className="w-16 h-16 rounded-full bg-slate-700 flex items-center justify-center mx-auto mb-2">
                            💬
                        </div>
                        <span className="text-sm text-slate-400">Response</span>
                    </div>
                </div>
            </div>
        </div>
    )
}

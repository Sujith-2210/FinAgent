import { Shield, Eye, Lock, FileText, CheckCircle, XCircle } from 'lucide-react'

export default function PrivacyPage() {
    const privacyFeatures = [
        {
            icon: Lock,
            title: 'Local LLM Processing',
            description: 'All AI reasoning happens locally using Gemma 3 4B. Your data never leaves your device.',
            status: 'active',
        },
        {
            icon: Eye,
            title: 'Value Masking',
            description: 'Raw financial values (₹ amounts) are converted to privacy-preserving bands (LOW/MEDIUM/HIGH).',
            status: 'active',
        },
        {
            icon: Shield,
            title: 'Context Access Control',
            description: 'Each agent can only access specific context layers as defined in their permissions.',
            status: 'active',
        },
        {
            icon: FileText,
            title: 'Audit Logging',
            description: 'All context access and agent activity is logged for transparency and compliance.',
            status: 'active',
        },
    ]

    const dataAccessLog = [
        { agent: 'orchestrator', layer: 'user_goals_context', operation: 'read', timestamp: '2 min ago' },
        { agent: 'finance_reasoning', layer: 'user_financial_context', operation: 'read', timestamp: '2 min ago' },
        { agent: 'finance_reasoning', layer: 'transactional_signals', operation: 'read', timestamp: '2 min ago' },
        { agent: 'explainability', layer: 'agent_working_memory', operation: 'read', timestamp: '1 min ago' },
    ]

    return (
        <div className="space-y-8">
            <div>
                <h1 className="text-3xl font-bold gradient-text">Privacy & Audit</h1>
                <p className="text-slate-400 mt-1">Transparency into how your data is protected</p>
            </div>

            {/* Privacy Status */}
            <div className="glass rounded-2xl p-6 border border-green-500/30">
                <div className="flex items-center gap-4 mb-4">
                    <div className="w-12 h-12 rounded-xl bg-green-500/20 flex items-center justify-center">
                        <Shield className="w-6 h-6 text-green-400" />
                    </div>
                    <div>
                        <h2 className="text-lg font-semibold text-green-400">Privacy Level: HIGH</h2>
                        <p className="text-sm text-slate-400">All privacy features are active</p>
                    </div>
                </div>

                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-4">
                    <div className="text-center">
                        <div className="text-2xl font-bold text-green-400">0</div>
                        <div className="text-xs text-slate-500">External API Calls</div>
                    </div>
                    <div className="text-center">
                        <div className="text-2xl font-bold text-green-400">100%</div>
                        <div className="text-xs text-slate-500">Values Masked</div>
                    </div>
                    <div className="text-center">
                        <div className="text-2xl font-bold text-green-400">Local</div>
                        <div className="text-xs text-slate-500">LLM Processing</div>
                    </div>
                    <div className="text-center">
                        <div className="text-2xl font-bold text-green-400">Active</div>
                        <div className="text-xs text-slate-500">Audit Logging</div>
                    </div>
                </div>
            </div>

            {/* Privacy Features */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {privacyFeatures.map((feature) => (
                    <div key={feature.title} className="glass rounded-xl p-4">
                        <div className="flex items-start gap-4">
                            <div className="w-10 h-10 rounded-xl bg-primary-500/20 flex items-center justify-center">
                                <feature.icon className="w-5 h-5 text-primary-400" />
                            </div>
                            <div className="flex-1">
                                <div className="flex items-center justify-between mb-1">
                                    <h3 className="font-medium">{feature.title}</h3>
                                    {feature.status === 'active' ? (
                                        <CheckCircle className="w-4 h-4 text-green-400" />
                                    ) : (
                                        <XCircle className="w-4 h-4 text-red-400" />
                                    )}
                                </div>
                                <p className="text-sm text-slate-400">{feature.description}</p>
                            </div>
                        </div>
                    </div>
                ))}
            </div>

            {/* Data Access Log */}
            <div className="glass rounded-2xl p-6">
                <h2 className="text-lg font-semibold mb-4">Recent Data Access Log</h2>
                <div className="overflow-x-auto">
                    <table className="w-full">
                        <thead>
                            <tr className="text-left text-sm text-slate-500 border-b border-slate-700">
                                <th className="pb-3">Agent</th>
                                <th className="pb-3">Layer Accessed</th>
                                <th className="pb-3">Operation</th>
                                <th className="pb-3">Timestamp</th>
                            </tr>
                        </thead>
                        <tbody>
                            {dataAccessLog.map((log, index) => (
                                <tr key={index} className="border-b border-slate-700/50 text-sm">
                                    <td className="py-3">
                                        <span className="badge badge-info">{log.agent}</span>
                                    </td>
                                    <td className="py-3 text-slate-300">
                                        {log.layer.replace(/_/g, ' ')}
                                    </td>
                                    <td className="py-3">
                                        <span className={`badge ${log.operation === 'read' ? 'badge-success' : 'badge-warning'}`}>
                                            {log.operation}
                                        </span>
                                    </td>
                                    <td className="py-3 text-slate-500">{log.timestamp}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>

            {/* Privacy by Design */}
            <div className="glass rounded-2xl p-6">
                <h2 className="text-lg font-semibold mb-4">Privacy by Design Principles</h2>
                <div className="space-y-3">
                    {[
                        'Context is read-only by default - agents must declare intent to access',
                        'Raw financial values never enter LLM prompts - only privacy-masked bands',
                        'Working memory is cleared after each session',
                        'Every context update is versioned and auditable',
                        'Agents operate under strict context access contracts',
                    ].map((principle, index) => (
                        <div key={index} className="flex items-start gap-3">
                            <CheckCircle className="w-5 h-5 text-green-400 flex-shrink-0 mt-0.5" />
                            <span className="text-slate-300">{principle}</span>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    )
}

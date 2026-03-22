import { useState } from 'react'
import { Bot, Shield, Cpu, Save, RefreshCw, CheckCircle } from 'lucide-react'

const STORAGE_KEY = 'finagent_settings'

interface AgentSettings {
    [key: string]: boolean
}

interface AppSettings {
    agentSettings: AgentSettings
    privacyLevel: string
    llmModel: string
    maxTokens: number
    temperature: number
    auditLogging: boolean
    fiMcpUrl: string
    phoneNumber: string
}

const DEFAULT_SETTINGS: AppSettings = {
    agentSettings: {
        finance_reasoning: true,
        knowledge: true,
        explainability: true,
        alert: true,
    },
    privacyLevel: 'HIGH',
    llmModel: 'gemma3:4b',
    maxTokens: 2048,
    temperature: 0.7,
    auditLogging: true,
    fiMcpUrl: 'http://localhost:8080/mcp/stream',
    phoneNumber: '2222222222',
}

function loadSettings(): AppSettings {
    try {
        const raw = localStorage.getItem(STORAGE_KEY)
        if (raw) {
            const parsed = JSON.parse(raw)
            return { ...DEFAULT_SETTINGS, ...parsed }
        }
    } catch {
        // corrupt data — fall back
    }
    return { ...DEFAULT_SETTINGS }
}

function saveSettings(settings: AppSettings): void {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(settings))
}

export default function SettingsPage() {
    const [settings, setSettings] = useState<AppSettings>(loadSettings)
    const [saving, setSaving] = useState(false)
    const [saved, setSaved] = useState(false)

    // Destructure for easy access
    const { agentSettings, privacyLevel, llmModel, maxTokens, temperature, auditLogging, fiMcpUrl, phoneNumber } = settings

    const update = <K extends keyof AppSettings>(key: K, value: AppSettings[K]) => {
        setSettings(prev => ({ ...prev, [key]: value }))
        setSaved(false)
    }

    const toggleAgent = (agent: string) => {
        setSettings(prev => ({
            ...prev,
            agentSettings: { ...prev.agentSettings, [agent]: !prev.agentSettings[agent] },
        }))
        setSaved(false)
    }

    const handleSave = async () => {
        setSaving(true)
        saveSettings(settings)
        // Brief delay for UX feedback
        await new Promise(resolve => setTimeout(resolve, 400))
        setSaving(false)
        setSaved(true)
        setTimeout(() => setSaved(false), 2000)
    }

    return (
        <div className="space-y-8 max-w-3xl">
            <div>
                <h1 className="text-3xl font-bold gradient-text">Settings</h1>
                <p className="text-slate-400 mt-1">Configure your FinAgent experience</p>
            </div>

            {/* Agent Settings */}
            <div className="glass rounded-2xl p-6">
                <div className="flex items-center gap-3 mb-6">
                    <div className="w-10 h-10 rounded-xl bg-primary-500/20 flex items-center justify-center">
                        <Bot className="w-5 h-5 text-primary-400" />
                    </div>
                    <div>
                        <h2 className="text-lg font-semibold">Agent Settings</h2>
                        <p className="text-sm text-slate-400">Enable or disable specialized agents</p>
                    </div>
                </div>

                <div className="space-y-4">
                    {Object.entries(agentSettings).map(([agent, enabled]) => (
                        <div key={agent} className="flex items-center justify-between p-4 glass rounded-xl">
                            <div>
                                <h3 className="font-medium capitalize">{agent.replace(/_/g, ' ')}</h3>
                                <p className="text-sm text-slate-500">
                                    {agent === 'finance_reasoning' && 'Core financial calculations and analysis'}
                                    {agent === 'knowledge' && 'External facts and regulations lookup'}
                                    {agent === 'explainability' && 'Human-readable explanations'}
                                    {agent === 'alert' && 'Proactive financial alerts'}
                                </p>
                            </div>
                            <button
                                onClick={() => toggleAgent(agent)}
                                className={`relative w-12 h-6 rounded-full transition-colors ${enabled ? 'bg-primary-500' : 'bg-slate-700'
                                    }`}
                            >
                                <div
                                    className={`absolute top-1 w-4 h-4 rounded-full bg-white transition-transform ${enabled ? 'left-7' : 'left-1'
                                        }`}
                                />
                            </button>
                        </div>
                    ))}
                </div>

                <p className="text-xs text-slate-500 mt-4">
                    Note: Orchestrator agent cannot be disabled.
                </p>
            </div>

            {/* Privacy Settings */}
            <div className="glass rounded-2xl p-6">
                <div className="flex items-center gap-3 mb-6">
                    <div className="w-10 h-10 rounded-xl bg-green-500/20 flex items-center justify-center">
                        <Shield className="w-5 h-5 text-green-400" />
                    </div>
                    <div>
                        <h2 className="text-lg font-semibold">Privacy Settings</h2>
                        <p className="text-sm text-slate-400">Control data privacy levels</p>
                    </div>
                </div>

                <div className="space-y-4">
                    <div>
                        <label className="block text-sm font-medium text-slate-300 mb-2">
                            Privacy Level
                        </label>
                        <select
                            value={privacyLevel}
                            onChange={(e) => update('privacyLevel', e.target.value)}
                            className="input"
                        >
                            <option value="HIGH">HIGH - Maximum privacy (recommended)</option>
                            <option value="MEDIUM">MEDIUM - Balanced privacy</option>
                            <option value="LOW">LOW - Minimal privacy (not recommended)</option>
                        </select>
                        <p className="text-xs text-slate-500 mt-2">
                            Higher privacy levels apply more aggressive value masking.
                        </p>
                    </div>

                    <div className="flex items-center justify-between p-4 glass rounded-xl">
                        <div>
                            <h3 className="font-medium">Audit Logging</h3>
                            <p className="text-sm text-slate-500">Log all context access and agent activity</p>
                        </div>
                        <button
                            onClick={() => update('auditLogging', !auditLogging)}
                            className={`relative w-12 h-6 rounded-full transition-colors ${auditLogging ? 'bg-primary-500' : 'bg-slate-700'}`}
                        >
                            <div className={`absolute top-1 w-4 h-4 rounded-full bg-white transition-transform ${auditLogging ? 'left-7' : 'left-1'}`} />
                        </button>
                    </div>
                </div>
            </div>

            {/* LLM Settings */}
            <div className="glass rounded-2xl p-6">
                <div className="flex items-center gap-3 mb-6">
                    <div className="w-10 h-10 rounded-xl bg-accent-500/20 flex items-center justify-center">
                        <Cpu className="w-5 h-5 text-accent-400" />
                    </div>
                    <div>
                        <h2 className="text-lg font-semibold">LLM Settings</h2>
                        <p className="text-sm text-slate-400">Configure local language model</p>
                    </div>
                </div>

                <div className="space-y-4">
                    <div>
                        <label className="block text-sm font-medium text-slate-300 mb-2">
                            Model
                        </label>
                        <select
                            value={llmModel}
                            onChange={(e) => update('llmModel', e.target.value)}
                            className="input"
                        >
                            <option value="gemma3:4b">Gemma 3 4B (Recommended)</option>
                            <option value="llama3:8b">Llama 3 8B</option>
                            <option value="mistral:7b">Mistral 7B</option>
                        </select>
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                        <div>
                            <label className="block text-sm font-medium text-slate-300 mb-2">
                                Max Tokens
                            </label>
                            <input
                                type="number"
                                value={maxTokens}
                                onChange={(e) => update('maxTokens', Number(e.target.value))}
                                className="input"
                            />
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-slate-300 mb-2">
                                Temperature
                            </label>
                            <input
                                type="number"
                                value={temperature}
                                onChange={(e) => update('temperature', Number(e.target.value))}
                                step={0.1}
                                min={0}
                                max={1}
                                className="input"
                            />
                        </div>
                    </div>
                </div>
            </div>

            {/* MCP Connection */}
            <div className="glass rounded-2xl p-6">
                <div className="flex items-center gap-3 mb-6">
                    <div className="w-10 h-10 rounded-xl bg-blue-500/20 flex items-center justify-center">
                        <RefreshCw className="w-5 h-5 text-blue-400" />
                    </div>
                    <div>
                        <h2 className="text-lg font-semibold">MCP Connection</h2>
                        <p className="text-sm text-slate-400">Fi MCP server settings</p>
                    </div>
                </div>

                <div className="space-y-4">
                    <div>
                        <label className="block text-sm font-medium text-slate-300 mb-2">
                            Fi MCP URL
                        </label>
                        <input
                            type="text"
                            value={fiMcpUrl}
                            onChange={(e) => update('fiMcpUrl', e.target.value)}
                            className="input"
                        />
                    </div>
                    <div>
                        <label className="block text-sm font-medium text-slate-300 mb-2">
                            Phone Number (for test data)
                        </label>
                        <input
                            type="text"
                            value={phoneNumber}
                            onChange={(e) => update('phoneNumber', e.target.value)}
                            className="input"
                        />
                        <p className="text-xs text-slate-500 mt-2">
                            Use test phone numbers from fi-mcp-dev (e.g., 2222222222 for full assets)
                        </p>
                    </div>
                </div>
            </div>

            {/* Save Button */}
            <div className="flex justify-end items-center gap-3">
                {saved && (
                    <span className="flex items-center gap-1 text-sm text-green-400 animate-fadeIn">
                        <CheckCircle className="w-4 h-4" />
                        Settings saved
                    </span>
                )}
                <button
                    onClick={handleSave}
                    disabled={saving}
                    className="btn-primary flex items-center gap-2"
                >
                    {saving ? (
                        <RefreshCw className="w-4 h-4 animate-spin" />
                    ) : (
                        <Save className="w-4 h-4" />
                    )}
                    {saving ? 'Saving...' : 'Save Settings'}
                </button>
            </div>
        </div>
    )
}

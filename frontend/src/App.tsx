import { BrowserRouter, Routes, Route } from 'react-router-dom'
import React from 'react'
import Layout from './components/Layout'
import RequireAuth from './components/RequireAuth'
import SplashScreen from './components/SplashScreen'
import AuthPage from './pages/AuthPage'
import ChatPage from './pages/ChatPage'
import DashboardPage from './pages/DashboardPage'
import ContextPage from './pages/ContextPage'
import AgentsPage from './pages/AgentsPage'
import AlertsPage from './pages/AlertsPage'
import PrivacyPage from './pages/PrivacyPage'
import SettingsPage from './pages/SettingsPage'
import { AuthProvider } from './context/AuthContext'
import { I18nProvider } from './context/I18nContext'
import './index.css'

function App() {
  const [showSplash, setShowSplash] = React.useState(true);

  if (showSplash) {
    return <SplashScreen onComplete={() => setShowSplash(false)} />;
  }

  return (
    <AuthProvider>
      <I18nProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/auth" element={<AuthPage />} />
            <Route
              path="/"
              element={(
                <RequireAuth>
                  <Layout />
                </RequireAuth>
              )}
            >
              <Route index element={<ChatPage />} />
              <Route path="dashboard" element={<DashboardPage />} />
              <Route path="context" element={<ContextPage />} />
              <Route path="agents" element={<AgentsPage />} />
              <Route path="alerts" element={<AlertsPage />} />
              <Route path="privacy" element={<PrivacyPage />} />
              <Route path="settings" element={<SettingsPage />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </I18nProvider>
    </AuthProvider>
  )
}

export default App

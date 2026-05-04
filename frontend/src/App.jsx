import { Routes, Route, Link, useLocation, Navigate, useNavigate } from 'react-router-dom'
import { useState, useEffect, createContext, useContext, useCallback } from 'react'
import TrendsPage from './pages/TrendsPage'
import GeneratorPage from './pages/GeneratorPage'
import ScriptViewerPage from './pages/ScriptViewerPage'
import NovelUploadPage from './pages/NovelUploadPage'
import ScriptListPage from './pages/ScriptListPage'
import LoginPage from './pages/LoginPage'
import AccountManagementPage from './pages/AccountManagementPage'
import { api } from './services/api'

// Global background task context
const BackgroundTaskContext = createContext()

export function useBackgroundTask() {
  return useContext(BackgroundTaskContext)
}

export function BackgroundTaskProvider({ children }) {
  const [tasks, setTasks] = useState([]) // {id, label, type}

  const addTask = useCallback((id, label, type = 'default') => {
    setTasks(prev => {
      if (prev.find(t => t.id === id)) return prev
      return [...prev, { id, label, type }]
    })
  }, [])

  const removeTask = useCallback((id) => {
    setTasks(prev => prev.filter(t => t.id !== id))
  }, [])

  return (
    <BackgroundTaskContext.Provider value={{ tasks, addTask, removeTask }}>
      {children}
      {tasks.length > 0 && <BackgroundSpinner tasks={tasks} />}
    </BackgroundTaskContext.Provider>
  )
}

function BackgroundSpinner({ tasks }) {
  return (
    <div className="fixed bottom-4 right-4 z-50 animate-fade-in">
      <div className="bg-white border border-ink-200 rounded-xl shadow-lg px-4 py-3 flex items-center gap-3 min-w-[200px]">
        <span className="spinner" style={{ width: 20, height: 20, borderWidth: 2 }} />
        <div className="flex-1 min-w-0">
          <div className="text-sm font-medium text-ink-800 truncate">
            {tasks[tasks.length - 1].label}
          </div>
          {tasks.length > 1 && (
            <div className="text-xs text-ink-400">还有 {tasks.length - 1} 个后台任务</div>
          )}
        </div>
      </div>
    </div>
  )
}

function ProtectedRoute({ children }) {
  const token = localStorage.getItem('token');
  if (!token) {
    return <Navigate to="/login" replace />;
  }
  return children;
}

function App() {
  const location = useLocation()
  const navigate = useNavigate()
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const [user, setUser] = useState(null)

  useEffect(() => {
    const stored = localStorage.getItem('user');
    if (stored) {
      try {
        setUser(JSON.parse(stored));
      } catch {}
    }
  }, []);

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    setUser(null);
    navigate('/login');
  };

  const navItems = [
    { path: '/', label: '热点趋势' },
    { path: '/generate', label: '生成剧本' },
    { path: '/novel', label: '小说改编' },
    { path: '/scripts', label: '我的剧本' },
  ]

  if (user?.is_admin) {
    navItems.push({ path: '/accounts', label: '账号管理' });
  }

  const isActive = (path) => {
    if (path === '/') return location.pathname === '/'
    return location.pathname.startsWith(path)
  }

  // Background trend fetching on mount
  const { addTask, removeTask } = useBackgroundTask()
  useEffect(() => {
    if (!localStorage.getItem('token')) return;

    const taskId = 'trends-fetch'
    addTask(taskId, '正在获取热点数据...')
    api.getTrendsFetchStatus().then(data => {
      if (data.fetching) return // already fetching
      // Trigger a refresh if no cache
      return api.getTrends().catch(() => {})
    }).catch(() => {}).finally(() => {
      setTimeout(() => removeTask(taskId), 1000)
    })
  }, [])

  if (location.pathname === '/login') {
    return (
      <Routes>
        <Route path="/login" element={<LoginPage />} />
      </Routes>
    );
  }

  return (
    <div className="min-h-screen bg-[#fafaf8] flex flex-col">
      {/* Header */}
      <header className="bg-white border-b border-ink-100 sticky top-0 z-50">
        <div className="mx-auto px-6 sm:px-10 lg:px-16">
          <div className="flex items-center justify-between h-14">
            {/* Logo */}
            <Link to="/" className="flex items-center gap-2.5 no-underline">
              <span className="text-lg font-semibold text-ink-900 tracking-tight">短剧创作</span>
            </Link>

            {/* Desktop Nav */}
            <nav className="hidden md:flex items-center gap-1">
              {navItems.map((item) => (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`px-3 py-1.5 text-sm font-medium rounded-lg transition-colors no-underline ${
                    isActive(item.path)
                      ? 'bg-brand-50 text-brand-700'
                      : 'text-ink-600 hover:text-ink-900 hover:bg-ink-50'
                  }`}
                >
                  {item.label}
                </Link>
              ))}
            </nav>

            <div className="hidden md:flex items-center gap-3">
              {user && (
                <span className="text-sm text-ink-600">{user.username}</span>
              )}
              <button
                onClick={handleLogout}
                className="px-3 py-1.5 text-sm text-ink-500 hover:text-ink-700 hover:bg-ink-50 rounded-lg transition-colors"
              >
                退出
              </button>
            </div>

            {/* Mobile menu button */}
            <button
              className="md:hidden p-2 text-ink-600 hover:text-ink-900"
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            >
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                {mobileMenuOpen ? (
                  <path d="M18 6L6 18M6 6l12 12" />
                ) : (
                  <path d="M3 12h18M3 6h18M3 18h18" />
                )}
              </svg>
            </button>
          </div>

          {/* Mobile Nav */}
          {mobileMenuOpen && (
            <nav className="md:hidden pb-3 border-t border-ink-100 pt-2">
              {navItems.map((item) => (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`block px-3 py-2 text-sm font-medium rounded-lg no-underline ${
                    isActive(item.path)
                      ? 'bg-brand-50 text-brand-700'
                      : 'text-ink-600 hover:bg-ink-50'
                  }`}
                  onClick={() => setMobileMenuOpen(false)}
                >
                  {item.label}
                </Link>
              ))}
              <div className="border-t border-ink-100 mt-2 pt-2 px-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-ink-600">{user?.username}</span>
                  <button
                    onClick={handleLogout}
                    className="text-sm text-ink-500 hover:text-ink-700"
                  >
                    退出
                  </button>
                </div>
              </div>
            </nav>
          )}
        </div>
      </header>

      {/* Main Content */}
      <main className="mx-auto px-6 sm:px-10 lg:px-16 py-6">
        <Routes>
          <Route path="/" element={<ProtectedRoute><TrendsPage /></ProtectedRoute>} />
          <Route path="/generate" element={<ProtectedRoute><GeneratorPage /></ProtectedRoute>} />
          <Route path="/generate/:taskId" element={<ProtectedRoute><GeneratorPage /></ProtectedRoute>} />
          <Route path="/novel" element={<ProtectedRoute><NovelUploadPage /></ProtectedRoute>} />
          <Route path="/scripts" element={<ProtectedRoute><ScriptListPage /></ProtectedRoute>} />
          <Route path="/scripts/:scriptId" element={<ProtectedRoute><ScriptViewerPage /></ProtectedRoute>} />
          <Route path="/accounts" element={<ProtectedRoute><AccountManagementPage /></ProtectedRoute>} />
        </Routes>
      </main>

      {/* Footer */}
      <footer className="border-t border-ink-100 bg-white mt-auto">
        <div className="mx-auto px-6 sm:px-10 lg:px-16 py-4">
          <div className="flex items-center justify-between text-xs text-ink-400">
            <span>短剧创作工具</span>
            <span>数据来源: 红果短剧 / 番茄小说</span>
          </div>
        </div>
      </footer>
    </div>
  )
}

export default App

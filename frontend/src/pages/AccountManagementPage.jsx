import { useState, useEffect } from 'react';
import { api } from '../services/api';

export default function AccountManagementPage() {
  const [accounts, setAccounts] = useState([]);
  const [newUsername, setNewUsername] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadAccounts();
  }, []);

  const loadAccounts = async () => {
    try {
      const result = await api.listAccounts();
      setAccounts(result.accounts);
    } catch (err) {
      setError('加载账号列表失败');
    }
  };

  const handleCreateAccount = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    setLoading(true);

    try {
      await api.createAccount(newUsername, newPassword);
      setSuccess(`账号 "${newUsername}" 创建成功`);
      setNewUsername('');
      setNewPassword('');
      loadAccounts();
    } catch (err) {
      setError(err.message || '创建失败');
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteAccount = async (username) => {
    if (!confirm(`确定要删除账号 "${username}" 吗？`)) return;

    try {
      await api.deleteAccount(username);
      setSuccess('账号已删除');
      loadAccounts();
    } catch (err) {
      setError(err.message || '删除失败');
    }
  };

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-white mb-6">账号管理</h1>

      {/* Create Account Form */}
      <div className="bg-slate-800/50 rounded-xl p-6 border border-slate-700/50 mb-8">
        <h2 className="text-lg font-semibold text-white mb-4">创建新账号</h2>
        <form onSubmit={handleCreateAccount} className="flex gap-4 items-end">
          <div className="flex-1">
            <label className="block text-sm text-slate-400 mb-1">用户名</label>
            <input
              type="text"
              value={newUsername}
              onChange={(e) => setNewUsername(e.target.value)}
              className="w-full px-4 py-2 bg-slate-700/50 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-purple-500"
              placeholder="至少3个字符"
              minLength={3}
              required
            />
          </div>
          <div className="flex-1">
            <label className="block text-sm text-slate-400 mb-1">密码</label>
            <input
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              className="w-full px-4 py-2 bg-slate-700/50 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-purple-500"
              placeholder="至少6个字符"
              minLength={6}
              required
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            className="px-6 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 focus:outline-none focus:ring-2 focus:ring-purple-500 disabled:opacity-50 transition-colors"
          >
            {loading ? '创建中...' : '创建'}
          </button>
        </form>

        {error && (
          <div className="mt-3 text-red-400 text-sm bg-red-500/10 py-2 px-4 rounded-lg">
            {error}
          </div>
        )}
        {success && (
          <div className="mt-3 text-green-400 text-sm bg-green-500/10 py-2 px-4 rounded-lg">
            {success}
          </div>
        )}
      </div>

      {/* Account List */}
      <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-700/50">
          <h2 className="text-lg font-semibold text-white">账号列表</h2>
        </div>
        <div className="divide-y divide-slate-700/50">
          {accounts.map((account) => (
            <div key={account.id} className="px-6 py-4 flex items-center justify-between">
              <div>
                <span className="text-white font-medium">{account.username}</span>
                {account.is_admin && (
                  <span className="ml-2 px-2 py-0.5 bg-purple-500/20 text-purple-400 text-xs rounded-full">
                    管理员
                  </span>
                )}
                <div className="text-sm text-slate-500 mt-1">
                  创建时间：{new Date(account.created_at).toLocaleString('zh-CN')}
                </div>
              </div>
              {!account.is_admin && (
                <button
                  onClick={() => handleDeleteAccount(account.username)}
                  className="px-3 py-1 text-red-400 hover:bg-red-500/10 rounded-lg transition-colors"
                >
                  删除
                </button>
              )}
            </div>
          ))}
          {accounts.length === 0 && (
            <div className="px-6 py-8 text-center text-slate-500">
              暂无账号
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

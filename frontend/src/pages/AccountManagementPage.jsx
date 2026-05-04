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
      <h1 className="text-2xl font-bold text-ink-900">账号管理</h1>

      {/* Create Account Form */}
      <div className="card p-6">
        <h2 className="text-lg font-semibold text-ink-900 mb-4">创建新账号</h2>
        <form onSubmit={handleCreateAccount} className="flex gap-4 items-end">
          <div className="flex-1">
            <label className="label">用户名</label>
            <input
              type="text"
              value={newUsername}
              onChange={(e) => setNewUsername(e.target.value)}
              className="input"
              placeholder="至少3个字符"
              minLength={3}
              required
            />
          </div>
          <div className="flex-1">
            <label className="label">密码</label>
            <input
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              className="input"
              placeholder="至少6个字符"
              minLength={6}
              required
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            className="btn btn-primary"
          >
            {loading ? '创建中...' : '创建'}
          </button>
        </form>

        {error && (
          <div className="mt-3 text-sm text-red-600 bg-red-50 border border-red-200 py-2 px-4 rounded-lg">
            {error}
          </div>
        )}
        {success && (
          <div className="mt-3 text-sm text-green-700 bg-green-50 border border-green-200 py-2 px-4 rounded-lg">
            {success}
          </div>
        )}
      </div>

      {/* Account List */}
      <div className="card overflow-hidden">
        <div className="px-6 py-4 border-b border-ink-100">
          <h2 className="text-lg font-semibold text-ink-900">账号列表</h2>
        </div>
        <div className="divide-y divide-ink-100">
          {accounts.map((account) => (
            <div key={account.id} className="px-6 py-4 flex items-center justify-between">
              <div>
                <span className="text-ink-900 font-medium">{account.username}</span>
                {account.is_admin && (
                  <span className="ml-2 badge badge-brand">管理员</span>
                )}
                <div className="text-sm text-ink-400 mt-1">
                  创建时间：{new Date(account.created_at).toLocaleString('zh-CN')}
                </div>
              </div>
              {!account.is_admin && (
                <button
                  onClick={() => handleDeleteAccount(account.username)}
                  className="btn btn-ghost text-sm text-red-500 hover:text-red-700"
                >
                  删除
                </button>
              )}
            </div>
          ))}
          {accounts.length === 0 && (
            <div className="px-6 py-8 text-center text-ink-400">
              暂无账号
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

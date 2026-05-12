import { useState, useEffect, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../services/api';

export default function AdminPage() {
  const [tab, setTab] = useState('accounts'); // 'accounts' | 'scripts'

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-ink-900">后台管理</h1>
          <p className="text-sm text-ink-500 mt-1">账号与剧本管理（仅管理员）</p>
        </div>
        <Link to="/" className="btn btn-ghost text-sm no-underline">返回首页</Link>
      </div>

      <div className="flex gap-2 border-b border-ink-100">
        <TabButton active={tab === 'accounts'} onClick={() => setTab('accounts')}>
          账号管理
        </TabButton>
        <TabButton active={tab === 'scripts'} onClick={() => setTab('scripts')}>
          剧本管理
        </TabButton>
      </div>

      {tab === 'accounts' ? <AccountsTab /> : <ScriptsTab />}
    </div>
  );
}

function TabButton({ active, onClick, children }) {
  return (
    <button
      onClick={onClick}
      className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors ${
        active
          ? 'border-brand-500 text-brand-700'
          : 'border-transparent text-ink-500 hover:text-ink-900'
      }`}
    >
      {children}
    </button>
  );
}

function Banner({ type, message, onClose }) {
  if (!message) return null;
  const cls =
    type === 'error'
      ? 'text-red-600 bg-red-50 border-red-200'
      : 'text-green-700 bg-green-50 border-green-200';
  return (
    <div className={`text-sm border py-2 px-4 rounded-lg flex items-start justify-between gap-3 ${cls}`}>
      <span className="whitespace-pre-line">{message}</span>
      <button onClick={onClose} className="text-xs opacity-60 hover:opacity-100">关闭</button>
    </div>
  );
}

// ==================== Accounts Tab ====================

function AccountsTab() {
  const [accounts, setAccounts] = useState([]);
  const [scriptsByOwner, setScriptsByOwner] = useState({});
  const [newUsername, setNewUsername] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [loading, setLoading] = useState(false);
  const [expanded, setExpanded] = useState(null); // username whose scripts are open

  useEffect(() => {
    loadAll();
  }, []);

  const loadAll = async () => {
    try {
      const [accountRes, scriptsRes] = await Promise.all([
        api.listAccounts(),
        api.adminListAllScripts(),
      ]);
      setAccounts(accountRes.accounts || []);
      const byOwner = {};
      for (const s of scriptsRes.items || []) {
        const o = s.owner || '(none)';
        if (!byOwner[o]) byOwner[o] = [];
        byOwner[o].push(s);
      }
      setScriptsByOwner(byOwner);
    } catch (err) {
      setError(err.message || '加载失败');
    }
  };

  const handleCreate = async (e) => {
    e.preventDefault();
    setError(''); setSuccess(''); setLoading(true);
    try {
      await api.createAccount(newUsername, newPassword);
      setSuccess(`账号 "${newUsername}" 创建成功`);
      setNewUsername(''); setNewPassword('');
      await loadAll();
    } catch (err) {
      setError(err.message || '创建失败');
    } finally { setLoading(false); }
  };

  const handleDelete = async (username) => {
    const count = (scriptsByOwner[username] || []).length;
    const extra = count > 0 ? `\n⚠️ 该账号名下有 ${count} 部剧本，删除账号后这些剧本会保留但变成孤儿（建议先转移或删除剧本）。` : '';
    if (!confirm(`确定要删除账号 "${username}" 吗？${extra}`)) return;
    try {
      await api.deleteAccount(username);
      setSuccess('账号已删除');
      await loadAll();
    } catch (err) { setError(err.message || '删除失败'); }
  };

  const handlePromote = async (username) => {
    if (!confirm(`确定要将 "${username}" 提升为管理员吗？`)) return;
    try {
      await api.adminPromoteAccount(username);
      setSuccess(`"${username}" 已提升为管理员`);
      await loadAll();
    } catch (err) { setError(err.message || '提升失败'); }
  };

  const handleDemote = async (username) => {
    if (!confirm(`确定要取消 "${username}" 的管理员权限吗？`)) return;
    try {
      await api.adminDemoteAccount(username);
      setSuccess(`已取消 "${username}" 的管理员权限`);
      await loadAll();
    } catch (err) { setError(err.message || '操作失败'); }
  };

  const handleResetPwd = async (username) => {
    const pwd = prompt(`为 "${username}" 设置新密码（至少6位）：`);
    if (!pwd) return;
    if (pwd.length < 6) { setError('密码至少6位'); return; }
    try {
      await api.adminResetPassword(username, pwd);
      setSuccess(`"${username}" 密码已重置`);
    } catch (err) { setError(err.message || '重置失败'); }
  };

  return (
    <div className="space-y-6">
      <div className="card p-6">
        <h2 className="text-lg font-semibold text-ink-900 mb-4">创建新账号</h2>
        <form onSubmit={handleCreate} className="flex gap-4 items-end flex-wrap">
          <div className="flex-1 min-w-[180px]">
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
          <div className="flex-1 min-w-[180px]">
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
          <button type="submit" disabled={loading} className="btn btn-primary">
            {loading ? '创建中...' : '创建账号'}
          </button>
        </form>
      </div>

      <Banner type="error" message={error} onClose={() => setError('')} />
      <Banner type="success" message={success} onClose={() => setSuccess('')} />

      <div className="card overflow-hidden">
        <div className="px-6 py-4 border-b border-ink-100 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-ink-900">账号列表（{accounts.length}）</h2>
          <button onClick={loadAll} className="btn btn-ghost text-sm">刷新</button>
        </div>
        <div className="divide-y divide-ink-100">
          {accounts.map((account) => {
            const ownedScripts = scriptsByOwner[account.username] || [];
            return (
              <div key={account.id} className="px-6 py-4">
                <div className="flex items-center justify-between flex-wrap gap-2">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-ink-900 font-medium">{account.username}</span>
                      {account.is_admin && <span className="badge badge-brand">管理员</span>}
                      <span className="text-xs text-ink-400">
                        {ownedScripts.length} 部剧本
                      </span>
                    </div>
                    <div className="text-sm text-ink-400 mt-1">
                      创建时间：{account.created_at ? new Date(account.created_at).toLocaleString('zh-CN') : '-'}
                    </div>
                  </div>
                  <div className="flex items-center gap-1 flex-wrap">
                    <button
                      onClick={() =>
                        setExpanded(expanded === account.username ? null : account.username)
                      }
                      className="btn btn-ghost text-sm"
                    >
                      {expanded === account.username ? '收起剧本' : '查看剧本'}
                    </button>
                    <button onClick={() => handleResetPwd(account.username)} className="btn btn-ghost text-sm">
                      重置密码
                    </button>
                    {account.is_admin ? (
                      <button onClick={() => handleDemote(account.username)} className="btn btn-ghost text-sm text-amber-600">
                        取消管理员
                      </button>
                    ) : (
                      <button onClick={() => handlePromote(account.username)} className="btn btn-ghost text-sm text-brand-600">
                        设为管理员
                      </button>
                    )}
                    <button
                      onClick={() => handleDelete(account.username)}
                      className="btn btn-ghost text-sm text-red-500 hover:text-red-700"
                    >
                      删除账号
                    </button>
                  </div>
                </div>

                {expanded === account.username && (
                  <div className="mt-3 border-t border-ink-100 pt-3">
                    {ownedScripts.length === 0 ? (
                      <div className="text-sm text-ink-400">该账号暂无剧本</div>
                    ) : (
                      <ul className="space-y-1">
                        {ownedScripts.map((s) => (
                          <li key={s.id} className="flex items-center justify-between text-sm">
                            <span className="text-ink-700">
                              <span className="font-medium">{s.title || '(无标题)'}</span>
                              <span className="text-ink-400 ml-2">· {s.episode_count || 0}集 · {s.genre || '-'}</span>
                            </span>
                            <span className="text-xs text-ink-400">{s.id}</span>
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                )}
              </div>
            );
          })}
          {accounts.length === 0 && (
            <div className="px-6 py-8 text-center text-ink-400">暂无账号</div>
          )}
        </div>
      </div>
    </div>
  );
}

// ==================== Scripts Tab ====================

function ScriptsTab() {
  const [scripts, setScripts] = useState([]);
  const [accounts, setAccounts] = useState([]);
  const [filter, setFilter] = useState('');
  const [ownerFilter, setOwnerFilter] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  useEffect(() => { loadAll(); }, []);

  const loadAll = async () => {
    try {
      const [s, a] = await Promise.all([api.adminListAllScripts(), api.listAccounts()]);
      setScripts(s.items || []);
      setAccounts(a.accounts || []);
    } catch (err) {
      setError(err.message || '加载失败');
    }
  };

  const filtered = useMemo(() => {
    const q = filter.trim().toLowerCase();
    return scripts.filter((s) => {
      if (ownerFilter && s.owner !== ownerFilter) return false;
      if (!q) return true;
      return (
        (s.title || '').toLowerCase().includes(q) ||
        (s.genre || '').toLowerCase().includes(q) ||
        (s.id || '').toLowerCase().includes(q) ||
        (s.owner || '').toLowerCase().includes(q)
      );
    });
  }, [scripts, filter, ownerFilter]);

  const handleTransfer = async (s) => {
    const owner = prompt(`将剧本《${s.title}》转移到哪个账号？\n可用账号：${accounts.map(a => a.username).join(', ')}`, s.owner);
    if (!owner || owner === s.owner) return;
    try {
      await api.adminTransferScript(s.id, owner);
      setSuccess(`已将《${s.title}》转移给 ${owner}`);
      await loadAll();
    } catch (err) { setError(err.message || '转移失败'); }
  };

  const handleCopy = async (s) => {
    const target = prompt(`将剧本《${s.title}》复制到哪个账号？\n可用账号：${accounts.map(a => a.username).join(', ')}`, '');
    if (!target) return;
    const newTitle = prompt('新标题（留空保持原标题）：', s.title) || null;
    try {
      const res = await api.adminCopyScript(s.id, target, newTitle);
      setSuccess(`已复制给 ${target}（新ID：${res.new_id}）`);
      await loadAll();
    } catch (err) { setError(err.message || '复制失败'); }
  };

  const handleDelete = async (s) => {
    if (!confirm(`确定要删除《${s.title}》（所属：${s.owner}）吗？此操作不可恢复。`)) return;
    try {
      await api.adminDeleteScript(s.id);
      setSuccess(`已删除《${s.title}》`);
      await loadAll();
    } catch (err) { setError(err.message || '删除失败'); }
  };

  const handleBulkDeleteByTitle = async () => {
    const title = prompt('输入要批量删除的剧本标题（精确匹配，会删除所有账号下同名剧本）：');
    if (!title) return;
    if (!confirm(`确定要删除所有账号下标题为《${title}》的剧本吗？`)) return;
    try {
      const res = await api.adminBulkDeleteByTitle(title);
      setSuccess(`批量删除完成：共删除 ${res.count} 部`);
      await loadAll();
    } catch (err) { setError(err.message || '批量删除失败'); }
  };

  return (
    <div className="space-y-4">
      <div className="card p-4 flex flex-wrap gap-3 items-end">
        <div className="flex-1 min-w-[200px]">
          <label className="label">搜索</label>
          <input
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            placeholder="按标题 / 题材 / 所有者 / ID 搜索"
            className="input"
          />
        </div>
        <div className="min-w-[160px]">
          <label className="label">账号筛选</label>
          <select
            value={ownerFilter}
            onChange={(e) => setOwnerFilter(e.target.value)}
            className="input"
          >
            <option value="">全部</option>
            {accounts.map((a) => (
              <option key={a.username} value={a.username}>{a.username}</option>
            ))}
          </select>
        </div>
        <button onClick={loadAll} className="btn btn-ghost">刷新</button>
        <button onClick={handleBulkDeleteByTitle} className="btn btn-ghost text-red-500 hover:text-red-700">
          按标题批量删除
        </button>
      </div>

      <Banner type="error" message={error} onClose={() => setError('')} />
      <Banner type="success" message={success} onClose={() => setSuccess('')} />

      <div className="card overflow-hidden">
        <div className="px-6 py-4 border-b border-ink-100">
          <h2 className="text-lg font-semibold text-ink-900">剧本列表（{filtered.length} / {scripts.length}）</h2>
        </div>
        <div className="divide-y divide-ink-100">
          {filtered.map((s) => (
            <div key={s.id} className="px-6 py-4 flex items-center justify-between gap-3 flex-wrap">
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-ink-900 font-medium truncate">{s.title || '(无标题)'}</span>
                  {s.genre && <span className="badge badge-brand">{s.genre}</span>}
                  <span className="text-xs text-ink-400">{s.episode_count || 0}集</span>
                </div>
                <div className="text-sm text-ink-500 mt-1">
                  所属：<span className="font-medium">{s.owner}</span>
                  <span className="mx-2 text-ink-300">·</span>
                  ID: <code className="text-xs">{s.id}</code>
                  {s.created_at && (
                    <>
                      <span className="mx-2 text-ink-300">·</span>
                      {new Date(s.created_at).toLocaleString('zh-CN')}
                    </>
                  )}
                </div>
                {s.logline && (
                  <div className="text-xs text-ink-400 mt-1 truncate">{s.logline}</div>
                )}
              </div>
              <div className="flex items-center gap-1 flex-wrap">
                <Link to={`/scripts/${s.id}`} className="btn btn-ghost text-sm no-underline">查看</Link>
                <button onClick={() => handleTransfer(s)} className="btn btn-ghost text-sm">转移</button>
                <button onClick={() => handleCopy(s)} className="btn btn-ghost text-sm">复制</button>
                <button onClick={() => handleDelete(s)} className="btn btn-ghost text-sm text-red-500 hover:text-red-700">
                  删除
                </button>
              </div>
            </div>
          ))}
          {filtered.length === 0 && (
            <div className="px-6 py-8 text-center text-ink-400">没有匹配的剧本</div>
          )}
        </div>
      </div>
    </div>
  );
}

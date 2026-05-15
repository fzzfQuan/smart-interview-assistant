import { useState, type FormEvent } from "react";
import { useAuth } from "../contexts/AuthContext";

interface Props {
  onSwitchToLogin: () => void;
}

export default function RegisterPage({ onSwitchToLogin }: Props) {
  const { register } = useAuth();
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    if (password.length < 6) {
      setError("密码至少需要 6 个字符");
      return;
    }
    setBusy(true);
    try {
      await register({
        username: username.trim(),
        email: email.trim(),
        password,
        display_name: displayName.trim() || undefined,
      });
    } catch (err: any) {
      setError(err.message || "注册失败");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <h1 className="text-2xl font-bold text-indigo-600">智能面试助手</h1>
          <p className="text-sm text-gray-500 mt-1">创建你的账号</p>
        </div>

        <form
          onSubmit={handleSubmit}
          className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 space-y-4"
        >
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              用户名
            </label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              autoComplete="username"
              className="w-full rounded-lg border border-gray-200 px-3.5 py-2.5 text-sm outline-none
                focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100 transition-all"
              placeholder="3~100 个字符"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              邮箱
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoComplete="email"
              className="w-full rounded-lg border border-gray-200 px-3.5 py-2.5 text-sm outline-none
                focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100 transition-all"
              placeholder="请输入邮箱地址"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              密码
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              autoComplete="new-password"
              className="w-full rounded-lg border border-gray-200 px-3.5 py-2.5 text-sm outline-none
                focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100 transition-all"
              placeholder="至少 6 个字符"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              显示名称
              <span className="text-gray-400 font-normal ml-1">（可选）</span>
            </label>
            <input
              type="text"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              autoComplete="name"
              className="w-full rounded-lg border border-gray-200 px-3.5 py-2.5 text-sm outline-none
                focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100 transition-all"
              placeholder="如何称呼您？"
            />
          </div>

          {error && (
            <div className="bg-red-50 border border-red-200 rounded-lg px-4 py-3 text-sm text-red-600">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={busy}
            className="w-full py-2.5 px-4 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50
              text-white font-medium rounded-xl transition-colors text-sm"
          >
            {busy ? "注册中..." : "注册"}
          </button>

          <p className="text-center text-sm text-gray-500">
            已有账号？{" "}
            <button
              type="button"
              onClick={onSwitchToLogin}
              className="text-indigo-600 hover:text-indigo-800 font-medium"
            >
              去登录
            </button>
          </p>
        </form>
      </div>
    </div>
  );
}

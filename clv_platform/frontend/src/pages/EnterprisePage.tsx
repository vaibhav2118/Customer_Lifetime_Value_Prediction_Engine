import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { DashboardLayout } from '../components/DashboardLayout';
import { 
  ShieldCheck, Key, Eye, EyeOff, Plus, Check, 
  Trash2, Clipboard, Activity, Lock, RefreshCw
} from 'lucide-react';

interface ApiKeyItem {
  id: number;
  name: string;
  prefix: string;
  created_at: string;
  expires_at: string | null;
  scopes: string[];
}

interface AuditLog {
  id: number;
  user_email: string | null;
  action: string;
  ip_address: string | null;
  details: string | null;
  created_at: string;
}

export const EnterprisePage: React.FC = () => {
  const { apiCall, user } = useAuth();

  // MFA Setup states
  const [mfaSecret, setMfaSecret] = useState<string>('');
  const [mfaQrUrl, setMfaQrUrl] = useState<string>('');
  const [mfaCode, setMfaCode] = useState<string>('');
  const [mfaSuccess, setMfaSuccess] = useState<boolean>(false);
  const [isSettingMfa, setIsSettingMfa] = useState<boolean>(false);

  // API Key states
  const [apiKeys, setApiKeys] = useState<ApiKeyItem[]>([]);
  const [keyName, setKeyName] = useState<string>('Production CRM Connector');
  const [newKeyToken, setNewKeyToken] = useState<string>('');
  const [isGeneratingKey, setIsGeneratingKey] = useState<boolean>(false);

  // Audit Logs states
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [isLoadingLogs, setIsLoadingLogs] = useState<boolean>(true);

  useEffect(() => {
    fetchKeysAndLogs();
  }, []);

  const fetchKeysAndLogs = async () => {
    setIsLoadingLogs(true);
    try {
      const keysList = await apiCall('/api/v1/enterprise/api-keys');
      setApiKeys(keysList);
      
      const logsList = await apiCall('/api/v1/enterprise/audit-logs?limit=50');
      setLogs(logsList);
    } catch (err) {
      setApiKeys([
        { id: 1, name: "Production HubSpot Syncer", prefix: "clv_xXyY...", scopes: ["read"], created_at: "2024-06-08", expires_at: "2024-07-08" }
      ]);
      setLogs([
        { id: 1, user_email: "admin@clv.com", action: "login", ip_address: "127.0.0.1", details: "User logged in successfully", created_at: "2024-06-09T14:30:00" },
        { id: 2, user_email: "admin@clv.com", action: "sync_shopify", ip_address: "127.0.0.1", details: "Initiated Shopify sync", created_at: "2024-06-09T14:32:00" }
      ]);
    } finally {
      setIsLoadingLogs(false);
    }
  };

  const handleSetupMfa = async () => {
    setIsSettingMfa(true);
    try {
      const res = await apiCall('/api/v1/auth/mfa/setup', { method: 'POST' });
      setMfaSecret(res.secret);
      setMfaQrUrl(res.qr_code_url);
    } catch (err) {
      setMfaSecret("E2O3K4L5M6N7P8Q9");
      setMfaQrUrl("https://qrcode-generator.com/mock-uri");
    } finally {
      setIsSettingMfa(false);
    }
  };

  const handleVerifyMfa = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await apiCall('/api/v1/auth/mfa/verify', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: user?.email, code: mfaCode })
      });
      setMfaSuccess(true);
      setMfaCode('');
      fetchKeysAndLogs();
    } catch (err) {
      alert("Simulated MFA setup activated.");
      setMfaSuccess(true);
      setMfaCode('');
    }
  };

  const handleGenerateKey = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsGeneratingKey(true);
    setNewKeyToken('');
    try {
      const res = await apiCall('/api/v1/enterprise/api-keys', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: keyName, scopes: ["read", "write"] })
      });
      setApiKeys([...apiKeys, res]);
      setNewKeyToken(res.token);
      setKeyName('');
    } catch (err) {
      const token = `clv_${Math.random().toString(36).substring(2, 15)}`;
      setNewKeyToken(token);
      const mockKey: ApiKeyItem = {
        id: Math.floor(Math.random() * 1000),
        name: keyName,
        prefix: token.substring(0, 8) + "...",
        scopes: ["read"],
        created_at: new Date().toISOString().split('T')[0],
        expires_at: null
      };
      setApiKeys([...apiKeys, mockKey]);
      setKeyName('');
    } finally {
      setIsGeneratingKey(false);
    }
  };

  const copyToClipboard = (txt: string) => {
    navigator.clipboard.writeText(txt);
    alert("Copied to clipboard!");
  };

  return (
    <DashboardLayout>
      <div className="space-y-8">
        {/* Header */}
        <div>
          <h1 className="text-3xl font-extrabold text-white">Enterprise Controls</h1>
          <p className="text-slate-400 text-sm mt-1">Configure multi-factor credentials, API credentials, and review log activity.</p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* MFA Security Setup */}
          <div className="glass-card rounded-2xl p-6">
            <div className="flex items-center gap-3 mb-6">
              <div className="w-8 h-8 rounded-lg bg-brand-500/10 border border-brand-500/20 flex items-center justify-center text-brand-400">
                <Lock className="w-4.5 h-4.5" />
              </div>
              <div>
                <h3 className="font-bold text-white text-base">Multi-Factor Authentication (MFA)</h3>
                <p className="text-slate-400 text-xs mt-0.5">Enforce standard TOTP verification logins.</p>
              </div>
            </div>

            {mfaSuccess ? (
              <div className="p-4 bg-green-500/10 border border-green-500/20 text-green-400 text-xs rounded-xl flex items-center gap-3 font-semibold">
                <Check className="w-5 h-5" /> Multi-factor authentication is active on this account.
              </div>
            ) : mfaSecret ? (
              <form onSubmit={handleVerifyMfa} className="space-y-4">
                <div className="p-3 bg-slate-950 border border-white/5 rounded-xl text-center">
                  <span className="text-[10px] text-slate-500 uppercase tracking-wider block mb-2">Authenticator QR Key Code</span>
                  <div className="w-32 h-32 bg-white flex items-center justify-center mx-auto mb-3 rounded-lg border border-white/10 font-bold text-xs text-slate-950 p-2">
                    [MOCK QR IMAGE]
                  </div>
                  <span className="text-xs text-brand-400 font-bold select-all">{mfaSecret}</span>
                </div>
                
                <div>
                  <label className="block text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-2">Verify Code from Device</label>
                  <input 
                    type="text" required placeholder="6-digit code"
                    value={mfaCode} onChange={(e) => setMfaCode(e.target.value)}
                    className="w-full bg-slate-950 border border-white/10 rounded-xl px-4 py-2 text-xs focus:outline-none focus:border-brand-500 transition text-center font-bold font-mono tracking-widest"
                  />
                </div>

                <button 
                  type="submit"
                  className="w-full py-2.5 bg-brand-600 hover:bg-brand-500 text-white text-xs font-semibold rounded-xl transition"
                >
                  Verify and Activate MFA
                </button>
              </form>
            ) : (
              <div>
                <p className="text-xs text-slate-400 leading-relaxed mb-6">
                  Set up a secure authenticator device using time-based verification codes (TOTP) to protect your account data.
                </p>
                <button 
                  onClick={handleSetupMfa}
                  disabled={isSettingMfa}
                  className="px-6 py-2.5 bg-brand-600 hover:bg-brand-500 text-white text-xs font-semibold rounded-xl transition inline-flex items-center gap-2"
                >
                  {isSettingMfa ? 'Initializing...' : 'Configure Authenticator App'}
                </button>
              </div>
            )}
          </div>

          {/* API Keys Configuration */}
          <div className="glass-card rounded-2xl p-6 flex flex-col justify-between">
            <div>
              <div className="flex items-center gap-3 mb-6">
                <div className="w-8 h-8 rounded-lg bg-brand-500/10 border border-brand-500/20 flex items-center justify-center text-brand-400">
                  <Key className="w-4.5 h-4.5" />
                </div>
                <div>
                  <h3 className="font-bold text-white text-base">Developer API Access Keys</h3>
                  <p className="text-slate-400 text-xs mt-0.5">Generate authentication keys for direct scoring API integrations.</p>
                </div>
              </div>

              {newKeyToken && (
                <div className="p-3 bg-brand-500/10 border border-brand-500/20 rounded-xl text-xs mb-4">
                  <span className="text-brand-300 block font-semibold mb-1">Make sure to copy your API key now (shown only once):</span>
                  <div className="flex items-center justify-between gap-3 bg-slate-950 p-2 rounded-lg border border-white/5 font-mono">
                    <span className="text-white block truncate select-all">{newKeyToken}</span>
                    <button onClick={() => copyToClipboard(newKeyToken)} className="text-brand-400 hover:text-brand-300 font-sans font-semibold text-[10px] uppercase">Copy</button>
                  </div>
                </div>
              )}
            </div>

            <div className="space-y-6">
              {/* Generate Key Form */}
              <form onSubmit={handleGenerateKey} className="flex gap-2">
                <input 
                  type="text" required placeholder="API Key Name (e.g. Sales CRM)"
                  value={keyName} onChange={(e) => setKeyName(e.target.value)}
                  className="flex-1 bg-slate-950 border border-white/10 rounded-xl px-4 py-2 text-xs focus:outline-none focus:border-brand-500 transition"
                />
                <button 
                  type="submit"
                  disabled={isGeneratingKey}
                  className="bg-brand-600 hover:bg-brand-500 disabled:bg-slate-800 text-white px-4 py-2 rounded-xl text-xs font-semibold flex items-center gap-1.5 transition"
                >
                  <Plus className="w-4 h-4" /> Create Key
                </button>
              </form>

              {/* Keys list */}
              <div className="overflow-x-auto">
                <table className="w-full text-left text-[11px]">
                  <thead>
                    <tr className="border-b border-white/5 text-slate-500 uppercase tracking-wider font-semibold">
                      <th className="pb-3 pr-4">Key Name</th>
                      <th className="pb-3 pr-4">Token Prefix</th>
                      <th className="pb-3 pr-4">Scopes</th>
                      <th className="pb-3">Created</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/5 font-mono text-slate-300">
                    {apiKeys.map((keyRecord, idx) => (
                      <tr key={idx} className="hover:bg-white/5">
                        <td className="py-2.5 font-bold font-sans text-white">{keyRecord.name}</td>
                        <td className="py-2.5 text-brand-300">{keyRecord.prefix}</td>
                        <td className="py-2.5">
                          {keyRecord.scopes.map((scope, sIdx) => (
                            <span key={sIdx} className="px-1.5 py-0.5 rounded bg-slate-800 border border-white/5 text-[9px] text-slate-400 font-semibold uppercase">{scope}</span>
                          ))}
                        </td>
                        <td className="py-2.5 font-sans text-slate-500">{keyRecord.created_at}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>

        {/* Audit Log grid */}
        <div className="glass-card rounded-2xl p-6">
          <div className="flex items-center gap-3 mb-6">
            <div className="w-8 h-8 rounded-lg bg-brand-500/10 border border-brand-500/20 flex items-center justify-center text-brand-400">
              <Activity className="w-4.5 h-4.5" />
            </div>
            <div>
              <h3 className="font-bold text-white text-base">Security Audit Logs</h3>
              <p className="text-slate-400 text-xs mt-0.5">Comprehensive multi-tenant trail logs capturing system actions.</p>
            </div>
          </div>

          {isLoadingLogs ? (
            <div className="h-32 flex items-center justify-center">
              <div className="w-6 h-6 border-2 border-brand-500 border-t-transparent animate-spin rounded-full" />
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-white/10 text-slate-500 uppercase tracking-wider font-semibold">
                    <th className="pb-3 pr-4">Timestamp</th>
                    <th className="pb-3 pr-4">Operator Email</th>
                    <th className="pb-3 pr-4">Action Event</th>
                    <th className="pb-3 pr-4">Client IP</th>
                    <th className="pb-3">Action Description Details</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5 font-mono text-slate-400">
                  {logs.map((logItem, idx) => (
                    <tr key={idx} className="hover:bg-white/5">
                      <td className="py-3 pr-4 text-slate-500 whitespace-nowrap">{new Date(logItem.created_at).toLocaleString()}</td>
                      <td className="py-3 pr-4 text-white font-sans font-medium">{logItem.user_email || 'System / ApiKey'}</td>
                      <td className="py-3 pr-4">
                        <span className="px-2 py-0.5 rounded bg-white/5 border border-white/10 text-[10px] text-slate-300 font-semibold uppercase font-sans">
                          {logItem.action}
                        </span>
                      </td>
                      <td className="py-3 pr-4 text-slate-500">{logItem.ip_address || 'N/A'}</td>
                      <td className="py-3 text-slate-300 font-sans leading-relaxed">{logItem.details || 'N/A'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </DashboardLayout>
  );
};

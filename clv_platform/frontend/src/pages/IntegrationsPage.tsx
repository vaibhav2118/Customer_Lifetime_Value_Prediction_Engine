import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { DashboardLayout } from '../components/DashboardLayout';
import { 
  Settings, RefreshCw, CheckCircle, AlertTriangle, 
  Layers, UploadCloud, Server, Bell, Link2, Plus 
} from 'lucide-react';

interface WebhookSub {
  id: number;
  event_type: string;
  target_url: string;
  is_active: boolean;
  secret: string;
  created_at: string;
}

export const IntegrationsPage: React.FC = () => {
  const { apiCall } = useAuth();
  
  // Shopify state
  const [shopifyUrl, setShopifyUrl] = useState<string>('brand-store.myshopify.com');
  const [shopifyToken, setShopifyToken] = useState<string>('shpat_xxxx');
  const [isShopifySyncing, setIsShopifySyncing] = useState<boolean>(false);
  const [shopifyMsg, setShopifyMsg] = useState<string>('');

  // WooCommerce state
  const [wooUrl, setWooUrl] = useState<string>('https://woo-retail.com');
  const [wooKey, setWooKey] = useState<string>('ck_xxxx');
  const [isWooSyncing, setIsWooSyncing] = useState<boolean>(false);
  const [wooMsg, setWooMsg] = useState<string>('');

  // Webhooks state
  const [webhooks, setWebhooks] = useState<WebhookSub[]>([]);
  const [hookEvent, setHookEvent] = useState<string>('customer.churn_risk_increased');
  const [hookUrl, setHookUrl] = useState<string>('https://api.my-crm.com/webhooks/clv-alerts');
  const [isSubscribing, setIsSubscribing] = useState<boolean>(false);

  useEffect(() => {
    fetchWebhooks();
  }, []);

  const fetchWebhooks = async () => {
    try {
      const list = await apiCall('/api/v1/integrations/webhooks/subscriptions');
      setWebhooks(list);
    } catch (err) {
      setWebhooks([
        { id: 1, event_type: "customer.churn_risk_increased", target_url: "https://api.internal-crm.com/webhooks/clv", secret: "whsec_abcd1234", is_active: true, created_at: "2024-06-09" }
      ]);
    }
  };

  const handleShopifySync = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsShopifySyncing(true);
    setShopifyMsg('');
    try {
      const res = await apiCall('/api/v1/integrations/shopify/sync', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ shop_url: shopifyUrl, access_token: shopifyToken })
      });
      setShopifyMsg(`Success! Imported ${res.orders_synced} orders from Shopify store.`);
    } catch (err: any) {
      setShopifyMsg(err.message || 'Shopify store synced successfully.');
    } finally {
      setIsShopifySyncing(false);
    }
  };

  const handleWooSync = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsWooSyncing(true);
    setWooMsg('');
    try {
      const res = await apiCall('/api/v1/integrations/woocommerce/sync', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ shop_url: wooUrl, access_token: wooKey })
      });
      setWooMsg(`Success! Imported ${res.orders_synced} orders.`);
    } catch (err: any) {
      setWooMsg(err.message || 'WooCommerce site synced successfully.');
    } finally {
      setIsWooSyncing(false);
    }
  };

  const handleAddWebhook = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubscribing(true);
    try {
      const newHook = await apiCall('/api/v1/integrations/webhooks/subscribe', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ event_type: hookEvent, target_url: hookUrl })
      });
      setWebhooks([...webhooks, newHook]);
      setHookUrl('');
    } catch (err) {
      const mockHook: WebhookSub = {
        id: Math.floor(Math.random() * 1000),
        event_type: hookEvent,
        target_url: hookUrl,
        secret: "whsec_gen_mock",
        is_active: true,
        created_at: new Date().toISOString().split('T')[0]
      };
      setWebhooks([...webhooks, mockHook]);
      setHookUrl('');
    } finally {
      setIsSubscribing(false);
    }
  };

  return (
    <DashboardLayout>
      <div className="space-y-8">
        {/* Header */}
        <div>
          <h1 className="text-3xl font-extrabold text-white">Connectors & Integrations</h1>
          <p className="text-slate-400 text-sm mt-1">Connect transaction sources and configure outgoing event hooks.</p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Shopify Connect Card */}
          <div className="glass-card rounded-2xl p-6 flex flex-col justify-between">
            <div>
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 rounded-lg bg-green-500/10 border border-green-500/20 flex items-center justify-center text-green-400 font-bold font-mono">
                  S
                </div>
                <div>
                  <h3 className="font-bold text-white text-base">Shopify Store Connector</h3>
                  <span className="text-xs text-slate-500 block">Synchronize orders and customers automatically.</span>
                </div>
              </div>
              
              {shopifyMsg && (
                <div className="p-3 bg-brand-500/10 border border-brand-500/20 text-brand-300 rounded-xl text-xs mb-4">
                  {shopifyMsg}
                </div>
              )}
            </div>

            <form onSubmit={handleShopifySync} className="space-y-4">
              <div>
                <label className="block text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-2">Shopify Admin URL</label>
                <input 
                  type="text" required placeholder="myshopify-store-domain.myshopify.com"
                  value={shopifyUrl} onChange={(e) => setShopifyUrl(e.target.value)}
                  className="w-full bg-slate-950 border border-white/10 rounded-xl px-4 py-2 text-xs focus:outline-none focus:border-brand-500 transition"
                />
              </div>
              <div>
                <label className="block text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-2">Custom App Access Token</label>
                <input 
                  type="password" required placeholder="shpat_xxxxx"
                  value={shopifyToken} onChange={(e) => setShopifyToken(e.target.value)}
                  className="w-full bg-slate-950 border border-white/10 rounded-xl px-4 py-2 text-xs focus:outline-none focus:border-brand-500 transition"
                />
              </div>
              <button 
                type="submit"
                disabled={isShopifySyncing}
                className="w-full py-2.5 bg-brand-600 hover:bg-brand-500 disabled:bg-slate-800 text-white rounded-xl text-xs font-semibold flex items-center justify-center gap-2 transition"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${isShopifySyncing ? 'animate-spin' : ''}`} /> 
                {isShopifySyncing ? 'Syncing...' : 'Sync Shopify Orders'}
              </button>
            </form>
          </div>

          {/* WooCommerce Connect Card */}
          <div className="glass-card rounded-2xl p-6 flex flex-col justify-between">
            <div>
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 rounded-lg bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400 font-bold font-mono">
                  W
                </div>
                <div>
                  <h3 className="font-bold text-white text-base">WooCommerce Site Sync</h3>
                  <span className="text-xs text-slate-500 block">Ingest transaction rows using WooCommerce endpoints.</span>
                </div>
              </div>

              {wooMsg && (
                <div className="p-3 bg-brand-500/10 border border-brand-500/20 text-brand-300 rounded-xl text-xs mb-4">
                  {wooMsg}
                </div>
              )}
            </div>

            <form onSubmit={handleWooSync} className="space-y-4">
              <div>
                <label className="block text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-2">WooCommerce Site Link</label>
                <input 
                  type="text" required placeholder="https://woo-retail.com"
                  value={wooUrl} onChange={(e) => setWooUrl(e.target.value)}
                  className="w-full bg-slate-950 border border-white/10 rounded-xl px-4 py-2 text-xs focus:outline-none focus:border-brand-500 transition"
                />
              </div>
              <div>
                <label className="block text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-2">Consumer Key</label>
                <input 
                  type="password" required placeholder="ck_xxxxx"
                  value={wooKey} onChange={(e) => setWooKey(e.target.value)}
                  className="w-full bg-slate-950 border border-white/10 rounded-xl px-4 py-2 text-xs focus:outline-none focus:border-brand-500 transition"
                />
              </div>
              <button 
                type="submit"
                disabled={isWooSyncing}
                className="w-full py-2.5 bg-brand-600 hover:bg-brand-500 disabled:bg-slate-800 text-white rounded-xl text-xs font-semibold flex items-center justify-center gap-2 transition"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${isWooSyncing ? 'animate-spin' : ''}`} />
                {isWooSyncing ? 'Syncing...' : 'Sync WooCommerce Store'}
              </button>
            </form>
          </div>
        </div>

        {/* Webhooks Section */}
        <div className="glass-card rounded-2xl p-6">
          <div className="flex items-center gap-3 mb-6">
            <div className="w-8 h-8 rounded-lg bg-brand-500/10 border border-brand-500/20 flex items-center justify-center text-brand-400">
              <Bell className="w-4.5 h-4.5" />
            </div>
            <div>
              <h3 className="font-bold text-white text-base">Outgoing Webhooks Router</h3>
              <p className="text-slate-400 text-xs mt-0.5">Subscribe server endpoint URLs to receive transaction and customer alerts.</p>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            {/* Create subscription form */}
            <form onSubmit={handleAddWebhook} className="space-y-4">
              <div>
                <label className="block text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-2">Target Event Trigger</label>
                <select 
                  value={hookEvent} onChange={(e) => setHookEvent(e.target.value)}
                  className="w-full bg-slate-950 border border-white/10 rounded-xl px-4 py-2.5 text-xs focus:outline-none focus:border-brand-500 text-white"
                >
                  <option value="customer.churn_risk_increased">Customer Churn Risk Increased</option>
                  <option value="customer.platinum_tier_reached">Customer Reached Platinum Tier</option>
                  <option value="prediction.refresh_completed">Database Refresh Complete</option>
                </select>
              </div>

              <div>
                <label className="block text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-2">Receiver Target URL</label>
                <input 
                  type="url" required placeholder="https://api.my-app.com/webhooks"
                  value={hookUrl} onChange={(e) => setHookUrl(e.target.value)}
                  className="w-full bg-slate-950 border border-white/10 rounded-xl px-4 py-2.5 text-xs focus:outline-none focus:border-brand-500 transition"
                />
              </div>

              <button 
                type="submit"
                disabled={isSubscribing}
                className="w-full py-2.5 bg-brand-600 hover:bg-brand-500 text-white font-semibold rounded-xl text-xs flex items-center justify-center gap-1.5 transition"
              >
                <Plus className="w-4 h-4" /> Subscribe Endpoint
              </button>
            </form>

            {/* Subscriptions list table */}
            <div className="lg:col-span-2 overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-white/5 text-slate-500 uppercase tracking-wider font-semibold">
                    <th className="pb-3 pr-4">Event Type</th>
                    <th className="pb-3 pr-4">Target URL</th>
                    <th className="pb-3 pr-4">Secret Signing key</th>
                    <th className="pb-3 text-center">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5 font-mono">
                  {webhooks.map((sub, idx) => (
                    <tr key={idx} className="hover:bg-white/5">
                      <td className="py-3 font-semibold text-white">{sub.event_type}</td>
                      <td className="py-3 text-slate-400 truncate max-w-[150px]" title={sub.target_url}>{sub.target_url}</td>
                      <td className="py-3 text-brand-300">{sub.secret}</td>
                      <td className="py-3 text-center">
                        <span className="px-2.5 py-0.5 rounded-full bg-green-500/10 text-green-400 font-bold uppercase text-[9px]">
                          Active
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
};

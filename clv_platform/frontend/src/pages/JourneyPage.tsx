import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { DashboardLayout } from '../components/DashboardLayout';
import { 
  Search, User, ShoppingBag, Calendar, GitFork, 
  Sparkles, ShieldCheck, Heart, AlertTriangle, MessageSquareCode
} from 'lucide-react';

interface JourneyEvent {
  event_name: string;
  event_date: string;
  description: string;
  metric_delta?: number;
}

interface Transaction {
  invoice_no: string;
  stock_code: string;
  description: string;
  quantity: number;
  price: number;
  invoice_date: string;
  revenue: number;
}

interface CustomerProfile {
  customer_id: string;
  country: string;
  recency: number;
  frequency: number;
  monetary: number;
  predicted_clv_6months: number | null;
  churn_risk_score: number | null;
  churn_risk_tier: string | null;
  expected_purchases_6m: number | null;
  recommendation_tier: string | null;
  recommendation_details: string | null;
  transactions: Transaction[];
}

export const JourneyPage: React.FC = () => {
  const { apiCall } = useAuth();
  
  // States
  const [searchId, setSearchId] = useState<string>('18139');
  const [profile, setProfile] = useState<CustomerProfile | null>(null);
  const [journeyEvents, setJourneyEvents] = useState<JourneyEvent[]>([]);
  const [healthScore, setHealthScore] = useState<any>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string>('');

  useEffect(() => {
    if (searchId) {
      handleProfileSearch();
    }
  }, []);

  const handleProfileSearch = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    setIsLoading(true);
    setErrorMsg('');
    try {
      // Fetch details from REST backend
      const res = await apiCall(`/api/v1/customers/${searchId}`);
      setProfile(res);
      
      const journey = await apiCall(`/api/v1/analytics/customer/${searchId}/journey`);
      setJourneyEvents(journey.events);
      
      const health = await apiCall(`/api/v1/analytics/customer/${searchId}/health`);
      setHealthScore(health);
    } catch (err: any) {
      setErrorMsg(err.message || 'Customer ID not found');
      // Mock Fallbacks for offline testing
      setProfile({
        customer_id: searchId,
        country: "United Kingdom",
        recency: 25,
        frequency: 4,
        monetary: 155.40,
        predicted_clv_6months: 620.40,
        churn_risk_score: 0.18,
        churn_risk_tier: "Low",
        expected_purchases_6m: 8.5,
        recommendation_tier: "Platinum",
        recommendation_details: "⭐ Platinum Tier Growth Plan:\n- Assign dedicated VIP account manager (Priority Tier 1 Support).\n- Direct 25% loyal VIP discount valid for the next 180 days.\n- Recommend early-access collections.",
        transactions: [
          { invoice_no: "536365", stock_code: "85123A", description: "WHITE HANGING HEART T-LIGHT HOLDER", quantity: 6, price: 2.55, invoice_date: "2024-01-10T12:00:00", revenue: 15.30 },
          { invoice_no: "536365", stock_code: "71053", description: "WHITE METAL LANTERN", quantity: 6, price: 3.39, invoice_date: "2024-01-10T12:00:00", revenue: 20.34 },
          { invoice_no: "538120", stock_code: "22752", description: "SET 7 BABUSHKA NESTING BOXES", quantity: 2, price: 8.50, invoice_date: "2024-03-15T15:30:00", revenue: 17.00 }
        ]
      });
      setJourneyEvents([
        { event_name: "Acquisition", event_date: "2024-01-10", description: "Initial transaction made for stock item: WHITE METAL LANTERN", metric_delta: 35.64 },
        { event_name: "Repeat Purchase", event_date: "2024-03-15", description: "Returned for another purchase of: NESTING BOXES", metric_delta: 17.00 },
        { event_name: "Risk Evaluation", event_date: "2024-06-09", description: "Model evaluated a churn risk of 18.0%. Tier assigned: Platinum", metric_delta: 620.40 }
      ]);
      setHealthScore({
        health_score: 88.5,
        label: "Excellent",
        color: "#38A169",
        components: {
          retention_reliability: 32.8,
          purchase_frequency: 18.2,
          recency_activity: 18.5,
          clv_value_index: 19.0
        }
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <DashboardLayout>
      <div className="space-y-8">
        {/* Header and Search Form */}
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
          <div>
            <h1 className="text-3xl font-extrabold text-white">Customer Profile Explorer</h1>
            <p className="text-slate-400 text-sm mt-1">Search specific customer profiles, inspect journeys, and review recommendations.</p>
          </div>
          
          <form onSubmit={handleProfileSearch} className="flex gap-2 w-full md:w-auto">
            <div className="relative flex-1 md:w-64">
              <Search className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
              <input 
                type="text" required placeholder="Enter Customer ID..."
                value={searchId} onChange={(e) => setSearchId(e.target.value)}
                className="w-full bg-slate-900 border border-white/10 rounded-xl pl-9 pr-4 py-2 text-xs focus:outline-none focus:border-brand-500 transition"
              />
            </div>
            <button 
              type="submit"
              className="bg-brand-600 hover:bg-brand-500 text-white px-4 py-2 rounded-xl text-xs font-semibold transition"
            >
              Search Profile
            </button>
          </form>
        </div>

        {errorMsg && (
          <div className="p-4 bg-red-500/10 border border-red-500/20 text-red-400 text-xs rounded-xl text-center">
            {errorMsg}
          </div>
        )}

        {isLoading ? (
          <div className="h-64 flex items-center justify-center">
            <div className="w-10 h-10 border-2 border-brand-500 border-t-transparent animate-spin rounded-full" />
          </div>
        ) : profile && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            {/* Left side: Profile Summary Cards & Health score */}
            <div className="space-y-6">
              {/* Profile card */}
              <div className="glass-card rounded-2xl p-6 relative overflow-hidden">
                <div className="flex items-center gap-4 mb-6">
                  <div className="w-12 h-12 rounded-xl bg-brand-500/10 border border-brand-500/20 flex items-center justify-center text-brand-400">
                    <User className="w-6 h-6" />
                  </div>
                  <div>
                    <h2 className="font-extrabold text-lg text-white">Customer #{profile.customer_id}</h2>
                    <span className="text-xs text-slate-500 block uppercase tracking-wider font-semibold">{profile.country}</span>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4 text-xs">
                  <div className="p-3 bg-slate-950/40 border border-white/5 rounded-xl">
                    <span className="text-slate-500 block mb-1">Recency (days)</span>
                    <span className="font-bold text-white block">{profile.recency} days ago</span>
                  </div>
                  <div className="p-3 bg-slate-950/40 border border-white/5 rounded-xl">
                    <span className="text-slate-500 block mb-1">Frequency</span>
                    <span className="font-bold text-white block">{profile.frequency} repeats</span>
                  </div>
                  <div className="p-3 bg-slate-950/40 border border-white/5 rounded-xl">
                    <span className="text-slate-500 block mb-1">Monetary (AOV)</span>
                    <span className="font-bold text-white block">£{profile.monetary.toFixed(2)}</span>
                  </div>
                  <div className="p-3 bg-slate-950/40 border border-white/5 rounded-xl">
                    <span className="text-slate-500 block mb-1">CLV Tier</span>
                    <span className="font-bold text-brand-300 block uppercase tracking-wider">{profile.recommendation_tier || 'Silver'}</span>
                  </div>
                </div>
              </div>

              {/* Health Score panel */}
              {healthScore && (
                <div className="glass-card rounded-2xl p-6">
                  <h3 className="font-bold text-xs text-slate-500 uppercase tracking-wider mb-4">Unified Health Score</h3>
                  
                  <div className="flex items-center gap-4 mb-6">
                    <div 
                      className="w-14 h-14 rounded-full border-4 flex items-center justify-center font-black text-lg text-white"
                      style={{ borderColor: healthScore.color }}
                    >
                      {healthScore.health_score}
                    </div>
                    <div>
                      <span className="font-extrabold text-sm block" style={{ color: healthScore.color }}>{healthScore.label} State</span>
                      <span className="text-[10px] text-slate-500 block leading-relaxed">Composite value mapping recency, repeat buying, and churn margins.</span>
                    </div>
                  </div>

                  <div className="space-y-2 text-xs">
                    <div className="flex justify-between">
                      <span className="text-slate-500">Retention Reliability (40%):</span>
                      <span className="font-bold text-white">{healthScore.components.retention_reliability}/40</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-500">Purchase Frequency (20%):</span>
                      <span className="font-bold text-white">{healthScore.components.purchase_frequency}/20</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-500">Recency Activity (20%):</span>
                      <span className="font-bold text-white">{healthScore.components.recency_activity}/20</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-500">CLV Value Index (20%):</span>
                      <span className="font-bold text-white">{healthScore.components.clv_value_index}/20</span>
                    </div>
                  </div>
                </div>
              )}

              {/* Recommendations */}
              <div className="bg-brand-500/5 border border-brand-500/10 rounded-2xl p-6">
                <div className="flex items-center gap-2 text-brand-400 font-bold text-xs uppercase tracking-wider mb-4">
                  <Sparkles className="w-4 h-4" /> AI Marketing Recommendation
                </div>
                <pre className="text-xs text-slate-300 leading-relaxed font-sans whitespace-pre-wrap">
                  {profile.recommendation_details || "N/A"}
                </pre>
              </div>
            </div>

            {/* Right side: Journey event timeline & Transactions */}
            <div className="lg:col-span-2 space-y-6">
              {/* Journey Event Timeline */}
              <div className="glass-card rounded-2xl p-6">
                <h3 className="font-bold text-xs text-slate-500 uppercase tracking-wider mb-6 flex items-center gap-2">
                  <GitFork className="w-4 h-4 text-brand-400" /> Customer Journey Timeline
                </h3>
                
                <div className="relative border-l border-white/10 pl-6 ml-3 space-y-6">
                  {journeyEvents.map((evt, idx) => (
                    <div key={idx} className="relative">
                      {/* Timeline dot */}
                      <div className="absolute -left-[31px] top-0.5 w-4 h-4 rounded-full bg-slate-900 border-2 border-brand-500 flex items-center justify-center">
                        <div className="w-1.5 h-1.5 rounded-full bg-brand-500" />
                      </div>
                      
                      <div>
                        <div className="flex items-baseline justify-between gap-4 mb-1">
                          <span className="font-bold text-sm text-white">{evt.event_name}</span>
                          <span className="text-[10px] text-slate-500 font-mono font-bold uppercase">{evt.event_date}</span>
                        </div>
                        <p className="text-xs text-slate-400 leading-relaxed mb-1">{evt.description}</p>
                        {evt.metric_delta !== undefined && (
                          <span className="text-[10px] text-brand-300 font-semibold block">
                            Value Delta: £{evt.metric_delta.toFixed(2)}
                          </span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Transaction list */}
              <div className="glass-card rounded-2xl p-6">
                <h3 className="font-bold text-xs text-slate-500 uppercase tracking-wider mb-4 flex items-center gap-2">
                  <ShoppingBag className="w-4 h-4 text-brand-400" /> Transaction Ledger
                </h3>
                
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead>
                      <tr className="border-b border-white/5 text-slate-500 uppercase tracking-wider font-semibold">
                        <th className="pb-3 pr-4">Invoice No</th>
                        <th className="pb-3 pr-4">Stock Code</th>
                        <th className="pb-3 pr-4">Description</th>
                        <th className="pb-3 pr-4 text-center">Qty</th>
                        <th className="pb-3 pr-4 text-right">Price</th>
                        <th className="pb-3 text-right">Revenue</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-white/5 font-mono">
                      {profile.transactions.map((txn, idx) => (
                        <tr key={idx} className="hover:bg-white/5">
                          <td className="py-2.5 text-white font-bold">{txn.invoice_no}</td>
                          <td className="py-2.5 text-slate-400">{txn.stock_code}</td>
                          <td className="py-2.5 text-slate-300 font-sans truncate max-w-[150px]">{txn.description}</td>
                          <td className="py-2.5 text-center text-slate-400">{txn.quantity}</td>
                          <td className="py-2.5 text-right text-slate-400">£{parseFloat(txn.price.toString()).toFixed(2)}</td>
                          <td className="py-2.5 text-right text-brand-400 font-bold">£{parseFloat(txn.revenue.toString()).toFixed(2)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </DashboardLayout>
  );
};

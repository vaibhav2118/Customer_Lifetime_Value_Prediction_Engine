import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { 
  Calculator, Shield, Zap, TrendingUp, Users, BarChart3, 
  ArrowRight, Check, Play, FileSpreadsheet, RefreshCw, Layers, Sparkles
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export const LandingPage: React.FC = () => {
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();

  // CLV Calculator state
  const [monthlyCustomers, setMonthlyCustomers] = useState<number>(5000);
  const [aov, setAov] = useState<number>(85);
  const [frequency, setFrequency] = useState<number>(3);
  const [retention, setRetention] = useState<number>(70);

  // Compute calculated metrics
  const avgClv = aov * frequency * (retention / 100);
  const revenueOpportunity = monthlyCustomers * avgClv;
  const retentionGains = revenueOpportunity * 0.18; // 18% lift average
  const profitImpact = retentionGains * 0.45; // 45% margin average

  // FAQ state
  const [openFaq, setOpenFaq] = useState<number | null>(null);

  const faqs = [
    {
      q: "How does the CLV engine ensemble models?",
      a: "Our engine combines the probabilistic BG/NBD + Gamma-Gamma model (ideal for purchase frequency and lifecycle modeling) with supervised XGBoost ML regressions (capturing granular feature variations) in a 60/40 weighted blend."
    },
    {
      q: "Can I connect custom data tables?",
      a: "Yes. You can import raw transaction CSVs directly or link native Shopify/WooCommerce store plugins to automatically pull live customer order profiles."
    },
    {
      q: "Is role-based security supported?",
      a: "Yes. The platform maps access rules for Admin, Analyst, and Business User levels, ensuring secure data visibility and operational control."
    }
  ];

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 selection:bg-brand-500 selection:text-white">
      {/* Sticky Header */}
      <header className="sticky top-0 z-50 border-b border-white/5 bg-slate-950/80 backdrop-blur-md">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-brand-600 to-indigo-400 flex items-center justify-center shadow-lg shadow-brand-500/20">
              <BarChart3 className="w-5 h-5 text-white" />
            </div>
            <span className="font-bold text-xl tracking-tight bg-gradient-to-r from-white to-slate-300 bg-clip-text text-transparent">
              RetentionAI
            </span>
          </div>

          <nav className="hidden md:flex items-center gap-8 text-sm font-medium text-slate-400">
            <a href="#features" className="hover:text-white transition">Features</a>
            <a href="#calculator" className="hover:text-white transition">CLV Calculator</a>
            <a href="#integrations" className="hover:text-white transition">Integrations</a>
            <a href="#pricing" className="hover:text-white transition">Pricing</a>
            <a href="#faq" className="hover:text-white transition">FAQ</a>
          </nav>

          <div className="flex items-center gap-4">
            {isAuthenticated ? (
              <button 
                onClick={() => navigate('/dashboard')}
                className="bg-brand-600 hover:bg-brand-500 text-white text-sm font-semibold px-4 h-10 rounded-xl transition flex items-center gap-2"
              >
                Go to Dashboard <ArrowRight className="w-4 h-4" />
              </button>
            ) : (
              <>
                <Link to="/onboarding" className="text-sm font-semibold text-slate-300 hover:text-white transition">
                  Sign In
                </Link>
                <Link 
                  to="/onboarding"
                  className="bg-brand-600 hover:bg-brand-500 text-white text-sm font-semibold px-4 h-10 rounded-xl transition inline-flex items-center justify-center"
                >
                  Start Free Trial
                </Link>
              </>
            )}
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="relative pt-20 pb-24 overflow-hidden">
        {/* Background Gradients */}
        <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-brand-500/10 rounded-full blur-[120px] pointer-events-none" />
        <div className="absolute top-1/3 left-1/3 -translate-x-1/2 -translate-y-1/2 w-[400px] h-[400px] bg-indigo-500/10 rounded-full blur-[100px] pointer-events-none" />

        <div className="max-w-7xl mx-auto px-6 text-center">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-brand-500/10 border border-brand-500/20 text-brand-300 text-xs font-semibold mb-8">
            <Sparkles className="w-3.5 h-3.5" /> Next-Gen Customer Intelligence Platform
          </div>
          
          <h1 className="text-4xl md:text-6xl font-extrabold tracking-tight max-w-4xl mx-auto leading-[1.1] mb-6">
            Predict Your Most Valuable Customers <br />
            <span className="accent-gradient-text">Before Your Competitors Do</span>
          </h1>

          <p className="text-lg md:text-xl text-slate-400 max-w-2xl mx-auto mb-10 leading-relaxed">
            Use AI-powered Customer Lifetime Value prediction, churn forecasting, and customer intelligence to maximize retention and revenue growth.
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-16">
            <Link 
              to="/onboarding"
              className="w-full sm:w-auto bg-brand-600 hover:bg-brand-500 text-white font-semibold px-8 py-3.5 rounded-xl transition shadow-lg shadow-brand-600/20 inline-flex items-center justify-center gap-2"
            >
              Start Free Trial <ArrowRight className="w-4 h-4" />
            </Link>
            <a 
              href="#calculator"
              className="w-full sm:w-auto bg-white/5 hover:bg-white/10 text-white font-semibold px-8 py-3.5 border border-white/10 rounded-xl transition inline-flex items-center justify-center gap-2"
            >
              <Play className="w-4 h-4 text-brand-400 fill-brand-400" /> Watch Demo
            </a>
          </div>

          {/* Hero Visual Dashboard Preview */}
          <div className="max-w-5xl mx-auto rounded-2xl overflow-hidden border border-white/10 shadow-2xl bg-slate-900/60 p-4">
            <div className="flex items-center justify-between border-b border-white/5 pb-4 mb-4">
              <div className="flex items-center gap-1.5">
                <div className="w-3 h-3 rounded-full bg-red-500/80" />
                <div className="w-3 h-3 rounded-full bg-yellow-500/80" />
                <div className="w-3 h-3 rounded-full bg-green-500/80" />
              </div>
              <div className="px-4 py-1 rounded-md bg-slate-950 border border-white/5 text-xs text-slate-500 font-mono">
                https://app.retentionai.com/dashboard
              </div>
              <div className="w-10" />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
              {[
                { l: "Predicted Revenue Pool", v: "£424,500", c: "📈 +14.2%" },
                { l: "Average Customer Health", v: "82.4", c: "🟢 Healthy" },
                { l: "Platinum Tier Share", v: "18.5%", c: "💎 925 VIPs" },
                { l: "Average Churn Risk", v: "22.3%", c: "⚠️ Moderate" }
              ].map((kpi, idx) => (
                <div key={idx} className="bg-slate-950/60 border border-white/5 rounded-xl p-4 text-left">
                  <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider block mb-1">{kpi.l}</span>
                  <span className="text-2xl font-bold text-white block mb-1">{kpi.v}</span>
                  <span className="text-xs text-brand-400 font-semibold">{kpi.c}</span>
                </div>
              ))}
            </div>

            <div className="h-64 rounded-xl bg-slate-950/60 border border-white/5 flex items-center justify-center p-6">
              <div className="text-center">
                <BarChart3 className="w-12 h-12 text-brand-500/50 mx-auto mb-3" />
                <span className="text-sm text-slate-400 block font-medium">Interactive Multi-Cohort Lifecycle Matrix Loading...</span>
                <span className="text-xs text-slate-600 block mt-1">Predictions ensembled from BG/NBD and XGBoost algorithms</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Trust Section */}
      <section className="py-12 border-y border-white/5 bg-slate-900/20">
        <div className="max-w-7xl mx-auto px-6 text-center">
          <p className="text-xs uppercase font-semibold text-slate-500 tracking-wider mb-6">
            Natively Integrated with Your Favorite Platforms
          </p>
          <div className="flex flex-wrap items-center justify-center gap-12 opacity-40">
            {["Shopify", "WooCommerce", "HubSpot", "Salesforce", "Stripe", "Klaviyo"].map((logo) => (
              <span key={logo} className="font-bold text-xl tracking-tight text-white font-mono">{logo}</span>
            ))}
          </div>
        </div>
      </section>

      {/* Business Impact Metrics */}
      <section className="py-20 max-w-7xl mx-auto px-6">
        <div className="text-center max-w-3xl mx-auto mb-16">
          <h2 className="text-3xl md:text-4xl font-extrabold tracking-tight mb-4">
            Quantifiable Impact on Your Bottom Line
          </h2>
          <p className="text-slate-400">
            Automating customer lifetime analytics delivers direct returns across multiple growth domains.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-5 gap-6">
          {[
            { l: "Revenue Growth", v: "22%", d: "Increase in customer monthly purchase values" },
            { l: "Retention Lift", v: "18%", d: "Decline in high-value cohort dropoffs" },
            { l: "Churn Reduction", v: "30%", d: "Fewer churn events triggered for Platinum spenders" },
            { l: "Marketing ROI", v: "4.5x", d: "Increase in campaign profitability conversion" },
            { l: "CLV Accuracy", v: "94%", d: "Ensembled models forecast precision" }
          ].map((item, idx) => (
            <div key={idx} className="bg-slate-900/40 border border-white/5 rounded-2xl p-6 text-center">
              <span className="text-3xl md:text-4xl font-extrabold text-brand-400 block mb-2">{item.v}</span>
              <span className="text-sm font-bold text-white block mb-1">{item.l}</span>
              <span className="text-xs text-slate-500 block leading-relaxed">{item.d}</span>
            </div>
          ))}
        </div>
      </section>

      {/* Interactive CLV Calculator */}
      <section id="calculator" className="py-20 bg-slate-900/30 border-y border-white/5">
        <div className="max-w-7xl mx-auto px-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
            <div>
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-300 text-xs font-semibold mb-4">
                <Calculator className="w-3.5 h-3.5" /> CLV Estimator Tool
              </div>
              <h2 className="text-3xl md:text-4xl font-extrabold tracking-tight mb-6">
                Calculate the Value of <br />
                <span className="accent-gradient-text">Improved Customer Retention</span>
              </h2>
              <p className="text-slate-400 leading-relaxed mb-8">
                Tweak the sliders to match your current retail metrics and see estimated customer lifetimes values, projected revenue pipelines, and the estimated profits generated from an average 18% retention lift.
              </p>

              <div className="space-y-6">
                <div>
                  <div className="flex justify-between text-sm mb-2">
                    <span className="text-slate-400">Monthly Customers</span>
                    <span className="font-semibold text-white">{monthlyCustomers.toLocaleString()}</span>
                  </div>
                  <input 
                    type="range" min="500" max="50000" step="500"
                    value={monthlyCustomers} onChange={(e) => setMonthlyCustomers(Number(e.target.value))}
                    className="w-full accent-brand-500 h-1.5 bg-slate-800 rounded-lg cursor-pointer"
                  />
                </div>

                <div>
                  <div className="flex justify-between text-sm mb-2">
                    <span className="text-slate-400">Average Order Value (AOV)</span>
                    <span className="font-semibold text-white">£{aov}</span>
                  </div>
                  <input 
                    type="range" min="10" max="500" step="5"
                    value={aov} onChange={(e) => setAov(Number(e.target.value))}
                    className="w-full accent-brand-500 h-1.5 bg-slate-800 rounded-lg cursor-pointer"
                  />
                </div>

                <div>
                  <div className="flex justify-between text-sm mb-2">
                    <span className="text-slate-400">Purchase Frequency (per year)</span>
                    <span className="font-semibold text-white">{frequency}x</span>
                  </div>
                  <input 
                    type="range" min="1" max="24" step="1"
                    value={frequency} onChange={(e) => setFrequency(Number(e.target.value))}
                    className="w-full accent-brand-500 h-1.5 bg-slate-800 rounded-lg cursor-pointer"
                  />
                </div>

                <div>
                  <div className="flex justify-between text-sm mb-2">
                    <span className="text-slate-400">Target Retention Rate</span>
                    <span className="font-semibold text-white">{retention}%</span>
                  </div>
                  <input 
                    type="range" min="10" max="95" step="5"
                    value={retention} onChange={(e) => setRetention(Number(e.target.value))}
                    className="w-full accent-brand-500 h-1.5 bg-slate-800 rounded-lg cursor-pointer"
                  />
                </div>
              </div>
            </div>

            <div className="bg-slate-900 border border-white/10 rounded-2xl p-8 shadow-xl relative overflow-hidden">
              <div className="absolute top-0 right-0 w-32 h-32 bg-brand-500/10 rounded-full blur-2xl pointer-events-none" />
              
              <h3 className="font-bold text-lg mb-6">Financial Impact Forecast</h3>

              <div className="space-y-6">
                <div className="flex justify-between items-center pb-4 border-b border-white/5">
                  <span className="text-sm text-slate-400">Avg Customer Lifetime Value (CLV)</span>
                  <span className="text-xl font-bold text-brand-300">£{avgClv.toFixed(2)}</span>
                </div>
                
                <div className="flex justify-between items-center pb-4 border-b border-white/5">
                  <span className="text-sm text-slate-400">Predicted Revenue Opportunity</span>
                  <span className="text-xl font-bold text-white">£{revenueOpportunity.toLocaleString()}</span>
                </div>

                <div className="flex justify-between items-center pb-4 border-b border-white/5">
                  <div className="text-left">
                    <span className="text-sm text-slate-400 block">Retention Gains (18% Lift)</span>
                    <span className="text-[10px] text-brand-400 font-semibold">Average platform improvement</span>
                  </div>
                  <span className="text-xl font-bold text-green-400">£{retentionGains.toLocaleString(undefined, {maximumFractionDigits: 0})}</span>
                </div>

                <div className="flex justify-between items-center">
                  <span className="text-sm text-slate-400">Net Profit Impact</span>
                  <span className="text-2xl font-black text-brand-400">£{profitImpact.toLocaleString(undefined, {maximumFractionDigits: 0})}</span>
                </div>
              </div>

              <Link 
                to="/onboarding" 
                className="w-full mt-8 bg-brand-600 hover:bg-brand-500 text-white font-semibold py-3 rounded-xl transition flex items-center justify-center gap-2"
              >
                Claim This Profit Opportunity <ArrowRight className="w-4 h-4" />
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Product Features Grid */}
      <section id="features" className="py-20 max-w-7xl mx-auto px-6">
        <div className="text-center max-w-3xl mx-auto mb-16">
          <h2 className="text-3xl md:text-4xl font-extrabold tracking-tight mb-4">
            Built for Enterprise Customer Strategy
          </h2>
          <p className="text-slate-400">
            A comprehensive suite of predictive ML services to handle granular customer profiling.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          {[
            { t: "CLV Prediction Engine", d: "Ensembled models blend BG/NBD and XGBoost to project future customer spend horizons.", i: Zap },
            { t: "Churn Risk Forecasting", d: "Determine the exact probability of customer attrition based on recency gaps.", i: Shield },
            { t: "Automatic Segmentation", d: "K-Means models cluster accounts into Platinum, Gold, Silver, and Bronze tiers.", i: Layers },
            { t: "Cohort Spend Analytics", d: "Review month-on-month retention cohorts to measure loyalty value decays.", i: Users },
            { t: "Advanced Journey Maps", d: "Visualize historical touchpoints, risk markers, and auto-reactivations.", i: BarChart3 },
            { t: "API Integrations", d: "Connect uploader files, Shopify stores, and webhooks endpoints.", i: RefreshCw },
            { t: "Security and RBAC", d: "Configure multi-factor tokens, SAML SSO, and audit tracking logs.", i: Shield },
            { t: "AI Campaign Generator", d: "Deploy automated copy matching target purchase preferences.", i: Sparkles }
          ].map((feat, idx) => {
            const Icon = feat.i;
            return (
              <div key={idx} className="bg-slate-900/40 border border-white/5 rounded-2xl p-6 hover:border-brand-500/30 transition">
                <div className="w-10 h-10 rounded-lg bg-brand-500/10 border border-brand-500/20 flex items-center justify-center mb-4">
                  <Icon className="w-5 h-5 text-brand-400" />
                </div>
                <h3 className="font-bold text-white mb-2">{feat.t}</h3>
                <p className="text-xs text-slate-500 leading-relaxed">{feat.d}</p>
              </div>
            );
          })}
        </div>
      </section>

      {/* Workflow Section */}
      <section className="py-20 bg-slate-900/10 border-t border-white/5">
        <div className="max-w-7xl mx-auto px-6">
          <h2 className="text-3xl font-extrabold tracking-tight text-center mb-16">
            The Customer Intelligence Workflow
          </h2>
          <div className="flex flex-col md:flex-row items-center justify-between gap-4">
            {[
              { s: "1", t: "Ingest Data", d: "Sync Shopify / CSV" },
              { s: "2", t: "Engine Features", d: "Compute RFM indices" },
              { s: "3", t: "Ensemble Models", d: "Fit BG/NBD + XGBoost" },
              { s: "4", t: "Cluster Segments", d: "K-Means classifications" },
              { s: "5", t: "Deploy Campaigns", d: "Trigger webhooks & AI lists" }
            ].map((step, idx) => (
              <React.Fragment key={idx}>
                <div className="flex-1 w-full bg-slate-900/60 border border-white/5 rounded-xl p-5 text-center relative">
                  <div className="absolute -top-3 left-4 w-7 h-7 rounded-full bg-brand-600 flex items-center justify-center text-xs font-bold text-white">
                    {step.s}
                  </div>
                  <h3 className="font-bold text-sm text-white mb-1 mt-1">{step.t}</h3>
                  <span className="text-xs text-slate-500 block">{step.d}</span>
                </div>
                {idx < 4 && <ArrowRight className="hidden md:block w-5 h-5 text-slate-700" />}
              </React.Fragment>
            ))}
          </div>
        </div>
      </section>

      {/* Competitive Table */}
      <section className="py-20 max-w-7xl mx-auto px-6">
        <h2 className="text-3xl font-extrabold tracking-tight text-center mb-12">
          How We Compare
        </h2>
        <div className="overflow-x-auto rounded-2xl border border-white/10 bg-slate-900/30">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-slate-900 border-b border-white/10">
                <th className="p-4 text-xs font-semibold text-slate-400">Capabilities</th>
                <th className="p-4 text-xs font-bold text-brand-300">RetentionAI (Ours)</th>
                <th className="p-4 text-xs font-semibold text-slate-400">Optimove</th>
                <th className="p-4 text-xs font-semibold text-slate-400">Pecan AI</th>
                <th className="p-4 text-xs font-semibold text-slate-400">Klaviyo</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5 text-sm">
              {[
                { f: "Ensembled Probabilistic & ML Models", o: true, c1: false, c2: true, c3: false },
                { f: "Multi-Tenant Audit Logging", o: true, c1: true, c2: false, c3: false },
                { f: "Custom Webhook Trigger Framework", o: true, c1: true, c2: false, c3: true },
                { f: "On-the-fly Cohorts spend matrices", o: true, c1: false, c2: false, c3: false }
              ].map((row, idx) => (
                <tr key={idx} className="hover:bg-slate-900/20">
                  <td className="p-4 font-medium text-slate-300">{row.f}</td>
                  <td className="p-4"><Check className="w-5 h-5 text-green-400" /></td>
                  <td className="p-4">{row.c1 ? <Check className="w-4 h-4 text-slate-500" /> : <span className="text-slate-600">-</span>}</td>
                  <td className="p-4">{row.c2 ? <Check className="w-4 h-4 text-slate-500" /> : <span className="text-slate-600">-</span>}</td>
                  <td className="p-4">{row.c3 ? <Check className="w-4 h-4 text-slate-500" /> : <span className="text-slate-600">-</span>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Pricing Section */}
      <section id="pricing" className="py-20 bg-slate-900/30 border-y border-white/5">
        <div className="max-w-7xl mx-auto px-6">
          <div className="text-center max-w-3xl mx-auto mb-16">
            <h2 className="text-3xl md:text-4xl font-extrabold tracking-tight mb-4">
              Transparent, Value-Driven Pricing
            </h2>
            <p className="text-slate-400">
              Plans scaling directly with your customer base and processing volume.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-5xl mx-auto">
            {[
              { n: "Starter", p: "£49", f: ["1,000 profile score/mo", "Executive Dashboard", "Standard templates copy", "SQLite Fallback DB"], c: "Start Trial" },
              { n: "Growth", p: "£199", f: ["Unlimited file uploads", "Shopify Native Syncing", "Multi-sheet Excel Exports", "Asynchronous CSV worker"], c: "Go Growth", a: true },
              { n: "Enterprise", p: "Custom", f: ["SAML / OpenID SSO", "Dedicated ML weights adjust", "Full Audit trail logging", "High Availability SLAs"], c: "Contact Sales" }
            ].map((plan, idx) => (
              <div 
                key={idx} 
                className={`bg-slate-900 border rounded-2xl p-8 relative flex flex-col justify-between ${plan.a ? 'border-brand-500 shadow-lg shadow-brand-500/10' : 'border-white/10'}`}
              >
                {plan.a && (
                  <span className="absolute -top-3 left-1/2 -translate-x-1/2 bg-brand-600 text-white text-xs font-bold px-3 py-1 rounded-full uppercase tracking-wider">
                    Most Popular
                  </span>
                )}
                <div>
                  <span className="text-slate-400 font-bold block mb-2">{plan.n}</span>
                  <div className="flex items-baseline gap-1 mb-6">
                    <span className="text-4xl font-black text-white">{plan.p}</span>
                    {plan.p !== "Custom" && <span className="text-slate-500 text-sm">/mo</span>}
                  </div>
                  <ul className="space-y-3 mb-8">
                    {plan.f.map((f, fIdx) => (
                      <li key={fIdx} className="flex items-center gap-2.5 text-xs text-slate-300">
                        <Check className="w-4 h-4 text-brand-400 flex-shrink-0" /> {f}
                      </li>
                    ))}
                  </ul>
                </div>

                <Link 
                  to="/onboarding"
                  className={`w-full text-center py-2.5 rounded-xl font-semibold text-sm transition ${plan.a ? 'bg-brand-600 hover:bg-brand-500 text-white' : 'bg-white/5 hover:bg-white/10 text-white border border-white/10'}`}
                >
                  {plan.c}
                </Link>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* FAQ Section */}
      <section id="faq" className="py-20 max-w-4xl mx-auto px-6">
        <h2 className="text-3xl font-extrabold tracking-tight text-center mb-12">
          Frequently Asked Questions
        </h2>
        <div className="space-y-4">
          {faqs.map((faq, idx) => (
            <div key={idx} className="bg-slate-900/60 border border-white/5 rounded-xl overflow-hidden">
              <button 
                onClick={() => setOpenFaq(openFaq === idx ? null : idx)}
                className="w-full p-5 text-left font-bold flex justify-between items-center text-white"
              >
                {faq.q}
                <span className="text-brand-400 text-xl">{openFaq === idx ? '-' : '+'}</span>
              </button>
              {openFaq === idx && (
                <div className="p-5 pt-0 text-sm text-slate-400 border-t border-white/5 leading-relaxed">
                  {faq.a}
                </div>
              )}
            </div>
          ))}
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-white/5 py-12 bg-slate-950">
        <div className="max-w-7xl mx-auto px-6 flex flex-col md:flex-row items-center justify-between gap-6 text-sm text-slate-500">
          <div className="flex items-center gap-3">
            <div className="w-6 h-6 rounded-md bg-brand-600 flex items-center justify-center">
              <BarChart3 className="w-3.5 h-3.5 text-white" />
            </div>
            <span className="font-bold text-white">RetentionAI</span>
          </div>
          <span>&copy; 2026 RetentionAI Inc. All rights reserved.</span>
          <div className="flex gap-6">
            <a href="#" className="hover:text-white transition">Privacy Policy</a>
            <a href="#" className="hover:text-white transition">Terms of Service</a>
          </div>
        </div>
      </footer>
    </div>
  );
};

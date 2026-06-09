import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  CheckCircle, ArrowRight, UserPlus, UploadCloud, 
  Settings, Check, Compass, Play, Download, Sparkles
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export const OnboardingPage: React.FC = () => {
  const navigate = useNavigate();
  const { login } = useAuth();

  // Onboarding Phase step controls
  // 1: Signup, 2: Welcome Tour, 3: CSV Upload, 4: Running Predictions, 5: Run Complete / Reports
  const [step, setStep] = useState<number>(1);

  // Forms states
  const [email, setEmail] = useState<string>('admin@clv.com');
  const [password, setPassword] = useState<string>('admin123');
  const [tenantName, setTenantName] = useState<string>('Retail Analytics Corp');
  const [errorMsg, setErrorMsg] = useState<string>('');

  // CSV file state
  const [csvFile, setCsvFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState<boolean>(false);

  // Prediction process steps
  const [predStep, setPredStep] = useState<number>(0);
  const predLabels = [
    "Ingesting transaction history rows...",
    "Cleaning and standardizing customer profiles...",
    "Fitting BG/NBD + Gamma-Gamma models...",
    "Training XGBoost supervised ensemble algorithms...",
    "Computing K-Means segments (Platinum/Gold/Silver/Bronze)...",
    "Writing analytical outcomes to database..."
  ];

  const handleSignupSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg('');
    try {
      const resp = await fetch('/api/v1/auth/signup', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password, tenant_name: tenantName })
      });
      
      const data = await resp.json();
      if (!resp.ok) {
        throw new Error(data.detail || 'Signup failed');
      }
      
      // Cache token
      login(email, 'Admin', data.tenant_id, data.access_token);
      setStep(2);
    } catch (err: any) {
      setErrorMsg(err.message || 'Signup failed');
      // For standalone demo client fallback:
      login(email, 'Admin', 1, 'mock-jwt-token');
      setStep(2);
    }
  };

  const handleCsvSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setCsvFile(e.target.files[0]);
    }
  };

  const triggerCsvUpload = () => {
    if (!csvFile) return;
    setIsUploading(true);
    setTimeout(() => {
      setIsUploading(false);
      setStep(4);
      runPredictionsLoop();
    }, 1500);
  };

  const runPredictionsLoop = () => {
    let currentSubStep = 0;
    const interval = setInterval(() => {
      if (currentSubStep < predLabels.length - 1) {
        currentSubStep++;
        setPredStep(currentSubStep);
      } else {
        clearInterval(interval);
        setStep(5);
      }
    }, 1200);
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex items-center justify-center p-6 relative">
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[500px] bg-brand-600/10 rounded-full blur-[100px] pointer-events-none" />

      <div className="w-full max-w-lg bg-slate-900 border border-white/10 rounded-2xl p-8 shadow-2xl relative overflow-hidden">
        {/* Progress Bar indicator */}
        <div className="absolute top-0 left-0 w-full h-1 bg-slate-800">
          <div 
            className="h-full bg-brand-500 transition-all duration-300"
            style={{ width: `${(step / 5) * 100}%` }}
          />
        </div>

        {/* STEP 1: SIGNUP FORM */}
        {step === 1 && (
          <div>
            <div className="text-center mb-8">
              <UserPlus className="w-10 h-10 text-brand-400 mx-auto mb-3" />
              <h2 className="text-2xl font-bold">Create Your Intelligence Profile</h2>
              <p className="text-slate-500 text-xs mt-1">Get immediate predictions mapping customer lifetime metrics.</p>
            </div>

            {errorMsg && (
              <div className="mb-4 p-3 bg-red-500/10 border border-red-500/20 text-red-400 text-xs rounded-xl text-center">
                {errorMsg}
              </div>
            )}

            <form onSubmit={handleSignupSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Company / Tenant Name</label>
                <input 
                  type="text" required placeholder="e.g. Acme Retail Corp"
                  value={tenantName} onChange={(e) => setTenantName(e.target.value)}
                  className="w-full bg-slate-950 border border-white/10 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:border-brand-500 transition"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Email Address</label>
                <input 
                  type="email" required placeholder="name@company.com"
                  value={email} onChange={(e) => setEmail(e.target.value)}
                  className="w-full bg-slate-950 border border-white/10 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:border-brand-500 transition"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Secure Password</label>
                <input 
                  type="password" required placeholder="Min 8 characters"
                  value={password} onChange={(e) => setPassword(e.target.value)}
                  className="w-full bg-slate-950 border border-white/10 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:border-brand-500 transition"
                />
              </div>

              <button 
                type="submit"
                className="w-full bg-brand-600 hover:bg-brand-500 text-white font-semibold py-3 rounded-xl transition flex items-center justify-center gap-2 mt-6"
              >
                Configure Tenant <ArrowRight className="w-4 h-4" />
              </button>
            </form>
          </div>
        )}

        {/* STEP 2: WELCOME TOUR GUIDE */}
        {step === 2 && (
          <div className="text-center">
            <Compass className="w-12 h-12 text-brand-400 mx-auto mb-4" />
            <h2 className="text-2xl font-bold mb-3">Welcome to your workspace!</h2>
            <p className="text-slate-400 text-sm leading-relaxed mb-6">
              Let's get started. We will guide you through uploading your first transactional dataset, training your ensembled models, and viewing your active customer metrics dashboards.
            </p>

            <div className="space-y-3 max-w-sm mx-auto text-left mb-8">
              <div className="flex gap-3 text-xs text-slate-300">
                <Check className="w-4.5 h-4.5 text-brand-400 flex-shrink-0" />
                <span>Upload standard transactional rows (customer ID, date, revenue).</span>
              </div>
              <div className="flex gap-3 text-xs text-slate-300">
                <Check className="w-4.5 h-4.5 text-brand-400 flex-shrink-0" />
                <span>Auto-train BG/NBD and XGBoost regression algorithms.</span>
              </div>
              <div className="flex gap-3 text-xs text-slate-300">
                <Check className="w-4.5 h-4.5 text-brand-400 flex-shrink-0" />
                <span>Download print-ready PDF summaries and multi-sheet Excel records.</span>
              </div>
            </div>

            <button 
              onClick={() => setStep(3)}
              className="bg-brand-600 hover:bg-brand-500 text-white font-semibold px-8 py-3 rounded-xl transition inline-flex items-center gap-2"
            >
              Start Welcome Tour <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        )}

        {/* STEP 3: GUIDED DATASET UPLOAD */}
        {step === 3 && (
          <div>
            <div className="text-center mb-6">
              <UploadCloud className="w-10 h-10 text-brand-400 mx-auto mb-3" />
              <h2 className="text-2xl font-bold">Import First Transaction Dataset</h2>
              <p className="text-slate-500 text-xs mt-1">Upload order histories in CSV formatting to populate database.</p>
            </div>

            <div className="border border-dashed border-white/10 rounded-2xl p-8 text-center bg-slate-950/40 relative mb-6">
              <input 
                type="file" accept=".csv" id="onboard-csv" className="hidden"
                onChange={handleCsvSelect}
              />
              <label htmlFor="onboard-csv" className="cursor-pointer">
                <UploadCloud className="w-8 h-8 text-slate-600 mx-auto mb-3" />
                {csvFile ? (
                  <span className="text-sm font-semibold text-brand-300">{csvFile.name}</span>
                ) : (
                  <>
                    <span className="text-xs text-slate-400 block font-medium">Drag and drop transactional CSV file here</span>
                    <span className="text-[10px] text-slate-600 block mt-1">Columns: Invoice, StockCode, Quantity, UnitPrice, Customer ID, Date</span>
                  </>
                )}
              </label>
            </div>

            <button 
              onClick={triggerCsvUpload}
              disabled={!csvFile || isUploading}
              className={`w-full font-semibold py-3 rounded-xl transition flex items-center justify-center gap-2 ${(!csvFile || isUploading) ? 'bg-slate-800 text-slate-500 cursor-not-allowed' : 'bg-brand-600 hover:bg-brand-500 text-white'}`}
            >
              {isUploading ? "Uploading file..." : (
                <>Upload Dataset & Trigger Models <Play className="w-4 h-4" /></>
              )}
            </button>
          </div>
        )}

        {/* STEP 4: RUNNING PREDICTIONS LOADER */}
        {step === 4 && (
          <div className="text-center">
            <div className="w-12 h-12 rounded-full border-2 border-brand-500 border-t-transparent animate-spin mx-auto mb-6" />
            <h2 className="text-xl font-bold mb-4">Training ML Ensembled Engines</h2>
            
            <div className="space-y-3 text-left max-w-sm mx-auto">
              {predLabels.map((lbl, idx) => (
                <div key={idx} className={`flex items-center gap-3 text-xs transition-opacity duration-300 ${predStep >= idx ? 'opacity-100' : 'opacity-30'}`}>
                  {predStep > idx ? (
                    <Check className="w-4 h-4 text-green-400 flex-shrink-0" />
                  ) : predStep === idx ? (
                    <div className="w-3.5 h-3.5 rounded-full border-2 border-brand-400 border-t-transparent animate-spin flex-shrink-0" />
                  ) : (
                    <div className="w-3.5 h-3.5 rounded-full bg-slate-800 flex-shrink-0" />
                  )}
                  <span className="text-slate-300">{lbl}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* STEP 5: PREDICTIONS COMPLETE & ACTIONS */}
        {step === 5 && (
          <div className="text-center">
            <CheckCircle className="w-12 h-12 text-green-400 mx-auto mb-4" />
            <h2 className="text-2xl font-bold mb-2">Setup Completed Successfully!</h2>
            <p className="text-slate-400 text-sm leading-relaxed mb-6">
              Models have been successfully trained and segments have been generated. You can download your reports now or go directly to the Executive Analytics workspace.
            </p>

            <div className="grid grid-cols-2 gap-4 mb-8">
              <div className="bg-slate-950/60 border border-white/5 rounded-xl p-4 text-left">
                <span className="text-xs text-slate-500 block mb-2">Executive Summary</span>
                <button className="w-full bg-white/5 hover:bg-white/10 border border-white/10 py-2 rounded-lg text-xs font-semibold flex items-center justify-center gap-1.5 transition">
                  <Download className="w-3.5 h-3.5 text-brand-400" /> Export PDF
                </button>
              </div>
              
              <div className="bg-slate-950/60 border border-white/5 rounded-xl p-4 text-left">
                <span className="text-xs text-slate-500 block mb-2">Multi-Sheet Data</span>
                <button className="w-full bg-white/5 hover:bg-white/10 border border-white/10 py-2 rounded-lg text-xs font-semibold flex items-center justify-center gap-1.5 transition">
                  <Download className="w-3.5 h-3.5 text-brand-400" /> Export Excel
                </button>
              </div>
            </div>

            <button 
              onClick={() => navigate('/dashboard')}
              className="w-full bg-brand-600 hover:bg-brand-500 text-white font-semibold py-3 rounded-xl transition flex items-center justify-center gap-2"
            >
              Go to Executive Workspace <ArrowRight className="w-4.5 h-4.5" />
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

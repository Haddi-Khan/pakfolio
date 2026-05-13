import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { ArrowLeft, CheckCircle } from "lucide-react";
import { api } from "../api/client";
import { AuthLayout, AuthCard, AuthError } from "../components/ui/AuthLayout";
import { AnimatePresence } from "framer-motion";

export function ResetPassword() {
  const [searchParams] = useSearchParams();
  const rawToken = searchParams.get("token");
  const navigate = useNavigate();
  
  const [token, setToken] = useState(rawToken || "");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    if (password !== confirm) { 
        setError("Passwords do not match"); 
        return; 
    }
    if (password.length < 8) {
        setError("Password must be at least 8 characters");
        return;
    }
    
    setLoading(true); 
    setError(null);
    try {
      await api.auth.resetPassword(token, password);
      setSuccess(true);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <AuthLayout>
      <AnimatePresence mode="wait">
        {success ? (
          <AuthCard key="success" title="Password Reset Successful" subtitle="Your password has been changed successfully. You can now use your new password to sign in.">
            <div className="text-center py-4">
              <CheckCircle size={48} className="text-gain mx-auto mb-6 animate-slide-up" />
              <Link to="/login" className="btn-primary w-full inline-block text-center">
                Proceed to Sign In
              </Link>
            </div>
          </AuthCard>
        ) : (
          <AuthCard key="form" title="Set new password" subtitle="Enter your new secure password below">
            <form onSubmit={handleSubmit} className="space-y-4">
              {!rawToken && (
                 <div>
                   <label className="text-muted text-xs font-semibold uppercase tracking-widest mb-2 block">Reset Token</label>
                   <input type="text" value={token}
                     onChange={(e) => setToken(e.target.value)}
                     placeholder="Paste token from email"
                     className="input mono" required />
                 </div>
              )}

              <div>
                <label className="text-muted text-xs font-semibold uppercase tracking-widest mb-2 block">New Password</label>
                <input type="password" value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Min. 8 characters"
                  className="input" autoFocus required />
              </div>

              <div>
                <label className="text-muted text-xs font-semibold uppercase tracking-widest mb-2 block">Confirm New Password</label>
                <input type="password" value={confirm}
                  onChange={(e) => setConfirm(e.target.value)}
                  placeholder="Repeat password"
                  className="input" required />
              </div>

              <AuthError>{error}</AuthError>

              <button type="submit" disabled={loading} className="btn-primary w-full mt-2">
                {loading ? "Resetting..." : "Save New Password"}
              </button>
              
              <div className="pt-2">
                  <Link to="/login" className="flex items-center justify-center gap-2 text-muted hover:text-soft text-sm w-full">
                    <ArrowLeft size={13} /> Back to login
                  </Link>
              </div>
            </form>
          </AuthCard>
        )}
      </AnimatePresence>
    </AuthLayout>
  );
}

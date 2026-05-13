import { useState } from "react";
import { Link } from "react-router-dom";
import { ArrowLeft, Send } from "lucide-react";
import { api } from "../api/client";
import { AuthLayout, AuthCard, AuthError } from "../components/ui/AuthLayout";
import { AnimatePresence } from "framer-motion";

export function ForgotPassword() {
  const [email, setEmail] = useState("");
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    if (!email) { 
        setError("Please enter your email address"); 
        return; 
    }
    
    setLoading(true); 
    setError(null);
    try {
      await api.auth.forgotPassword(email);
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
          <AuthCard key="success" title="Check Your Email" subtitle={`If ${email} is registered, a password reset link has been sent to your inbox.`}>
            <div className="text-center py-4">
              <Send size={48} className="text-accent mx-auto mb-6 animate-slide-up" />
              <Link to="/login" className="btn-primary w-full inline-block text-center">
                Back to Sign In
              </Link>
            </div>
          </AuthCard>
        ) : (
          <AuthCard key="form" title="Reset password" subtitle="Enter your email to receive a reset link">
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="text-muted text-xs font-semibold uppercase tracking-widest mb-2 block">Email</label>
                <input type="email" value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@example.com"
                  className="input" autoFocus required />
              </div>

              <AuthError>{error}</AuthError>

              <button type="submit" disabled={loading} className="btn-primary w-full mt-2">
                {loading ? "Sending..." : "Send Reset Link"}
              </button>
              
              <div className="pt-2 flex justify-center w-full">
                  <Link to="/login" className="flex items-center gap-2 text-muted hover:text-soft text-sm">
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

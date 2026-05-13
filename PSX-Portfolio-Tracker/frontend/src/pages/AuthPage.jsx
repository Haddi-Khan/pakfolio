import { useState, useEffect, useRef } from "react";
import { Link } from "react-router-dom";
import { TrendingUp, Eye, EyeOff, ArrowLeft, Send } from "lucide-react";
import { api } from "../api/client";
import { useAuth } from "../context/AuthContext";
import { motion, AnimatePresence } from "framer-motion";
import { AuthLayout, AuthCard, AuthError } from "../components/ui/AuthLayout";

// Which view to show
const VIEW = { LOGIN: "login", REGISTER: "register", FORGOT: "forgot", RESET: "reset" };

export function AuthPage() {
  const [view, setView] = useState(VIEW.LOGIN);
  const [resetToken, setResetToken] = useState("");

  useEffect(() => {
    // Initialize Facebook SDK
    const initFB = () => {
      if (window.FB && !window.FB._initialized) {
        window.FB.init({
          appId      : import.meta.env.VITE_FACEBOOK_APP_ID,
          cookie     : true,
          xfbml      : true,
          version    : 'v19.0'
        });
        window.FB._initialized = true;
      }
    };

    if (window.FB) {
      initFB();
    } else {
      window.fbAsyncInit = initFB;
    }
  }, []);

  return (
    <AuthLayout>
      <AnimatePresence mode="wait">
        {view === VIEW.LOGIN && (
          <LoginForm key="login" onRegister={() => setView(VIEW.REGISTER)} onForgot={() => setView(VIEW.FORGOT)} />
        )}
        {view === VIEW.REGISTER && (
          <RegisterForm key="register" onLogin={() => setView(VIEW.LOGIN)} />
        )}
        {view === VIEW.FORGOT && (
          <ForgotForm
            key="forgot"
            onBack={() => setView(VIEW.LOGIN)}
            onResetSent={(token) => { setResetToken(token); setView(VIEW.RESET); }}
          />
        )}
        {view === VIEW.RESET && (
          <ResetForm
            key="reset"
            devToken={resetToken}
            onDone={() => setView(VIEW.LOGIN)}
          />
        )}
      </AnimatePresence>
    </AuthLayout>
  );
}


// ── Login ─────────────────────────────────────────────────────────────────────

function LoginForm({ onRegister, onForgot }) {
  const { login, loginSocial } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPw, setShowPw] = useState(false);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (window.google && window.google.accounts) {
      window.google.accounts.id.initialize({
        client_id: import.meta.env.VITE_GOOGLE_CLIENT_ID,
        callback: async (res) => {
          setLoading(true);
          try {
            await loginSocial("google", res.credential);
          } catch (err) {
            setError(err.message);
          } finally {
            setLoading(false);
          }
        }
      });
    }
  }, [loginSocial]);

  const handleGoogleLogin = () => {
    if (!window.google) return setError("Google SDK not loaded");
    window.google.accounts.id.prompt();
  };

  const handleFacebookLogin = () => {
    if (!window.FB) return setError("Facebook SDK not loaded");
    window.FB.login((res) => {
      if (res.authResponse) {
        setLoading(true);
        loginSocial("facebook", res.authResponse.accessToken)
          .catch(err => setError(err.message))
          .finally(() => setLoading(false));
      }
    }, { scope: 'email,public_profile' });
  };

  async function handleSubmit(e) {
    e.preventDefault();
    setLoading(true); setError(null);
    try {
      await login(email, password);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <AuthCard title="Welcome back" subtitle="Sign in to your portfolio">
      <form onSubmit={handleSubmit} className="space-y-4">
        <Field label="Email Address">
          <input
            autoFocus
            type="email" value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com"
            className="input"
          />
        </Field>

        <Field label="Password">
          <div className="relative">
            <input
              type={showPw ? "text" : "password"} value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              className="input pr-10"
            />
            <button type="button" onClick={() => setShowPw(!showPw)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-muted hover:text-soft">
              {showPw ? <EyeOff size={15} /> : <Eye size={15} />}
            </button>
          </div>
          <button type="button" onClick={onForgot}
            className="text-xs text-accent hover:underline mt-1 text-right w-full block">
            Forgot password?
          </button>
        </Field>

        {error && (
          <div className="space-y-2">
            <AuthError>{error}</AuthError>
            {error.toLowerCase().includes("verify your email") && (
              <ResendButton identifier={email} />
            )}
          </div>
        )}

        <button type="submit" disabled={loading} className="btn-primary w-full">
          {loading ? "Signing in..." : "Sign In"}
        </button>

        <div className="relative py-4">
          <div className="absolute inset-0 flex items-center"><div className="w-full border-t border-border"></div></div>
          <div className="relative flex justify-center text-xs uppercase"><span className="bg-surface px-2 text-muted">Or continue with</span></div>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <button type="button" onClick={handleGoogleLogin} className="btn-secondary py-2.5 flex items-center justify-center gap-2">
            <svg className="w-4 h-4" viewBox="0 0 24 24"><path fill="currentColor" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/><path fill="currentColor" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/><path fill="currentColor" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/><path fill="currentColor" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/></svg>
            Google
          </button>
          <button type="button" onClick={handleFacebookLogin} className="btn-secondary py-2.5 flex items-center justify-center gap-2">
            <svg className="w-4 h-4 text-[#1877F2]" fill="currentColor" viewBox="0 0 24 24"><path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"/></svg>
            Facebook
          </button>
        </div>

        <p className="text-center text-muted text-sm">
          Don't have an account?{" "}
          <button type="button" onClick={onRegister} className="text-soft hover:underline font-semibold">
            Create one
          </button>
        </p>

        <div className="pt-6 border-t border-border/50 flex items-center justify-center gap-4 text-[10px] text-muted uppercase tracking-widest font-bold">
          <Link to="/privacy" className="hover:text-accent transition-colors">Privacy Policy</Link>
          <div className="w-1 h-1 rounded-full bg-border" />
          <Link to="/terms" className="hover:text-accent transition-colors">Terms of Service</Link>
        </div>
      </form>
    </AuthCard>
  );
}


// ── Register ──────────────────────────────────────────────────────────────────

function RegisterForm({ onLogin }) {
  const { register, loginSocial } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [showPw, setShowPw] = useState(false);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (window.google && window.google.accounts) {
      window.google.accounts.id.initialize({
        client_id: import.meta.env.VITE_GOOGLE_CLIENT_ID,
        callback: async (res) => {
          setLoading(true);
          try {
            await loginSocial("google", res.credential);
          } catch (err) {
            setError(err.message);
          } finally {
            setLoading(false);
          }
        }
      });
    }
  }, [loginSocial]);

  const handleGoogleLogin = () => {
    if (!window.google) return setError("Google SDK not loaded");
    window.google.accounts.id.prompt();
  };

  const handleFacebookLogin = () => {
    if (!window.FB) return setError("Facebook SDK not loaded");
    window.FB.login((res) => {
      if (res.authResponse) {
        setLoading(true);
        loginSocial("facebook", res.authResponse.accessToken)
          .catch(err => setError(err.message))
          .finally(() => setLoading(false));
      }
    }, { scope: 'email,public_profile' });
  };

  const [success, setSuccess] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) { setError("Please enter a valid email address"); return; }
    if (password !== confirm) { setError("Passwords do not match"); return; }
    setLoading(true); setError(null);
    try {
      await register(email, password);
      setSuccess(true);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  if (success) {
    return (
      <AuthCard title="Check your email" subtitle="We sent a verification link">
        <div className="text-center py-6 text-muted">
          <p className="mb-6 text-sm">Please verify your email address to continue setting up your Pakfolio account.</p>
          
          <div className="space-y-4">
            <ResendButton identifier={email} />
            
            <button type="button" onClick={onLogin} className="btn-secondary w-full">
              Back to Sign In
            </button>
          </div>
        </div>
      </AuthCard>
    );
  }

  return (
    <AuthCard title="Create account" subtitle="Start tracking with Pakfolio">
      <form onSubmit={handleSubmit} className="space-y-4">
        <Field label="Email Address">
          <input type="email" value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com"
            className="input" autoFocus />
        </Field>


        <Field label="Password">
          <div className="relative">
            <input
              type={showPw ? "text" : "password"} value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Min. 8 characters"
              className="input pr-10" />
            <button type="button" onClick={() => setShowPw(!showPw)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-muted hover:text-soft">
              {showPw ? <EyeOff size={15} /> : <Eye size={15} />}
            </button>
          </div>
        </Field>

        <Field label="Confirm Password">
          <input
            type={showPw ? "text" : "password"} value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
            placeholder="Repeat password"
            className="input" />
        </Field>

        {error && <AuthError>{error}</AuthError>}

        <button type="submit" disabled={loading} className="btn-primary w-full">
          {loading ? "Creating account..." : "Create Account"}
        </button>

        <div className="relative py-4">
          <div className="absolute inset-0 flex items-center"><div className="w-full border-t border-border"></div></div>
          <div className="relative flex justify-center text-xs uppercase"><span className="bg-surface px-2 text-muted">Or continue with</span></div>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <button type="button" onClick={handleGoogleLogin} className="btn-secondary py-2.5 flex items-center justify-center gap-2">
            <svg className="w-4 h-4" viewBox="0 0 24 24"><path fill="currentColor" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/><path fill="currentColor" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/><path fill="currentColor" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/><path fill="currentColor" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/></svg>
            Google
          </button>
          <button type="button" onClick={handleFacebookLogin} className="btn-secondary py-2.5 flex items-center justify-center gap-2">
            <svg className="w-4 h-4 text-[#1877F2]" fill="currentColor" viewBox="0 0 24 24"><path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"/></svg>
            Facebook
          </button>
        </div>

        <p className="text-center text-muted text-sm">
          Already have an account?{" "}
          <button type="button" onClick={onLogin} className="text-soft hover:underline font-semibold">
            Sign in
          </button>
        </p>
        <div className="pt-6 border-t border-border/50 flex items-center justify-center gap-4 text-[10px] text-muted uppercase tracking-widest font-bold">
          <Link to="/privacy" className="hover:text-accent transition-colors">Privacy Policy</Link>
          <div className="w-1 h-1 rounded-full bg-border" />
          <Link to="/terms" className="hover:text-accent transition-colors">Terms of Service</Link>
        </div>
      </form>
    </AuthCard>
  );
}


// ── Forgot Password ───────────────────────────────────────────────────────────

function ForgotForm({ onBack, onResetSent }) {
  const { forgotPassword } = useAuth();
  const [email, setEmail] = useState("");
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setLoading(true); setError(null);
    try {
      const res = await forgotPassword(email);
      setSuccess(true);
      // dev_token is returned in development — in production only an email is sent
      if (res.dev_token) {
        setTimeout(() => onResetSent(res.dev_token), 1000);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <AuthCard title="Reset password" subtitle="Enter your email to receive a reset link">
      {success ? (
        <div className="text-center py-6">
          <p className="text-muted text-sm mb-6">If the email exists, a password reset link has been sent.</p>
          <button type="button" onClick={onBack} className="btn-primary w-full">
            Back to Sign In
          </button>
        </div>
      ) : (
      <form onSubmit={handleSubmit} className="space-y-4">
        <Field label="Email">
          <input type="email" value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com"
            className="input" autoFocus />
        </Field>

        {error && <AuthError>{error}</AuthError>}

        <button type="submit" disabled={loading} className="btn-primary w-full">
          {loading ? "Sending..." : "Send Reset Link"}
        </button>

        <button type="button" onClick={onBack}
          className="flex items-center gap-2 text-muted hover:text-soft text-sm mx-auto">
          <ArrowLeft size={13} /> Back to login
        </button>
      </form>
      )}
    </AuthCard>
  );
}


// ── Reset Password ────────────────────────────────────────────────────────────

function ResetForm({ devToken, onDone }) {
  const { resetPassword } = useAuth();
  const [token, setToken] = useState(devToken || "");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    if (password !== confirm) { setError("Passwords do not match"); return; }
    setLoading(true); setError(null);
    try {
      await resetPassword(token, password);
      setSuccess(true);
      setTimeout(onDone, 2000);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  if (success) {
    return (
      <AuthCard title="Password reset!" subtitle="Redirecting to login...">
        <div className="text-center py-4 text-gain font-semibold">Password changed successfully.</div>
      </AuthCard>
    );
  }

  return (
    <AuthCard title="Set new password" subtitle="Enter the reset token and your new password">
      <form onSubmit={handleSubmit} className="space-y-4">
        {!devToken && (
          <Field label="Reset Token">
            <input type="text" value={token}
              onChange={(e) => setToken(e.target.value)}
              placeholder="Paste token from email"
              className="input mono" />
          </Field>
        )}
        {devToken && (
          <div className="bg-surface-2 rounded-xl p-3 text-xs text-muted">
            <span className="text-warn font-semibold">Dev mode:</span> token auto-filled from API response
          </div>
        )}

        <Field label="New Password">
          <input type="password" value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Min. 8 characters"
            className="input" autoFocus />
        </Field>

        <Field label="Confirm New Password">
          <input type="password" value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
            placeholder="Repeat password"
            className="input" />
        </Field>

        {error && <AuthError>{error}</AuthError>}

        <button type="submit" disabled={loading} className="btn-primary w-full">
          {loading ? "Resetting..." : "Reset Password"}
        </button>
      </form>
    </AuthCard>
  );
}


// ── Shared UI helpers ─────────────────────────────────────────────────────────

function ResendButton({ identifier }) {
  const [cooldown, setCooldown] = useState(0);
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState(null); // { type: 'success'|'error', msg: string }
  const timerRef = useRef(null);

  useEffect(() => {
    if (cooldown > 0) {
      timerRef.current = setInterval(() => {
        setCooldown(prev => prev - 1);
      }, 1000);
    } else {
      clearInterval(timerRef.current);
    }
    return () => clearInterval(timerRef.current);
  }, [cooldown]);

  async function handleResend() {
    if (!identifier) {
      setStatus({ type: 'error', msg: 'Please enter your username first.' });
      return;
    }
    setLoading(true); setStatus(null);
    try {
      const res = await api.auth.resendVerification(identifier);
      setStatus({ type: 'success', msg: res.message || 'Verification email resent!' });
      setCooldown(120); // 2 minute cooldown
    } catch (err) {
      if (err.message.includes("wait")) {
        // Parse the seconds from "Please wait X seconds..."
        const match = err.message.match(/(\d+)/);
        if (match) setCooldown(parseInt(match[1]));
      }
      setStatus({ type: 'error', msg: err.message });
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-2">
      <button
        type="button"
        disabled={loading || cooldown > 0}
        onClick={handleResend}
        className={`w-full flex items-center justify-center gap-2 py-2 px-4 rounded-xl text-xs font-bold transition-all border
          ${cooldown > 0 
            ? 'bg-surface-2 border-transparent text-muted cursor-not-allowed' 
            : 'bg-accent/10 border-accent/20 text-accent hover:bg-accent/20'}`}
      >
        <Send size={14} className={loading ? 'animate-pulse' : ''} />
        {loading ? 'Sending...' : cooldown > 0 ? `Resend in ${cooldown}s` : 'Resend Verification Link'}
      </button>
      
      {status && (
        <p className={`text-[10px] text-center font-medium ${status.type === 'success' ? 'text-gain' : 'text-loss'}`}>
          {status.msg}
        </p>
      )}
    </div>
  );
}

function Field({ label, children }) {
  return (
    <div>
      <label className="text-muted text-xs font-semibold uppercase tracking-widest mb-2 block">{label}</label>
      {children}
    </div>
  );
}


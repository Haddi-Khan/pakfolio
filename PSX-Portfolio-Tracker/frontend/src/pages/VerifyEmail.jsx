import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { CheckCircle, XCircle } from "lucide-react";
import { api } from "../api/client";

export function VerifyEmail() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token");
  
  const [status, setStatus] = useState("loading"); // loading, success, error
  const [message, setMessage] = useState("Verifying your email address...");

  useEffect(() => {
    if (!token) {
      setStatus("error");
      setMessage("No verification token provided in the URL.");
      return;
    }

    api.auth.verify(token)
      .then((res) => {
        setStatus("success");
        setMessage(res.message || "Email verified successfully! You can now log in.");
      })
      .catch((err) => {
        setStatus("error");
        setMessage(err.message || "Invalid or expired verification link.");
      });
  }, [token]);

  return (
    <div className="min-h-screen bg-bg flex items-center justify-center p-4">
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-[600px] h-[400px] bg-accent/5 rounded-full blur-3xl" />
      </div>

      <div className="w-full max-w-md relative bg-surface border border-border rounded-2xl p-10 shadow-2xl text-center fade-in">
        {status === "loading" && (
          <div className="flex flex-col items-center justify-center">
            <div className="w-12 h-12 border-4 border-accent border-t-transparent rounded-full animate-spin mb-6" />
            <h2 className="text-white font-bold text-xl mb-2">Verifying Email</h2>
            <p className="text-muted text-sm">{message}</p>
          </div>
        )}

        {status === "success" && (
          <div className="flex flex-col items-center justify-center">
            <CheckCircle size={56} className="text-gain mb-6 animate-slide-up" />
            <h2 className="text-white font-bold text-xl mb-2">Account Verified!</h2>
            <p className="text-muted text-sm mb-8">{message}</p>
            <Link to="/login" className="btn-primary w-full inline-block">
              Sign In to Pakfolio
            </Link>
          </div>
        )}

        {status === "error" && (
          <div className="flex flex-col items-center justify-center">
            <XCircle size={56} className="text-loss mb-6 animate-slide-up" />
            <h2 className="text-white font-bold text-xl mb-2">Verification Failed</h2>
            <p className="text-muted text-sm mb-8">{message}</p>
            <Link to="/login" className="btn-primary w-full inline-block">
              Return to Login
            </Link>
          </div>
        )}
      </div>
    </div>
  );
}

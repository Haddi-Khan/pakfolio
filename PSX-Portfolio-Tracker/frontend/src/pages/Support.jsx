import { Link } from "react-router-dom";
import { Mail, Shield, BookOpen } from "lucide-react";

export function Support() {
  return (
    <div className="max-w-4xl mx-auto space-y-6 fade-in p-2 md:p-6 lg:p-8">
      <div className="bg-surface border border-border rounded-2xl p-8 flex flex-col md:flex-row items-center md:items-start gap-8">
        <div className="w-24 h-24 rounded-full bg-accent/10 border border-accent/20 flex items-center justify-center shrink-0">
          <Mail size={40} className="text-accent" />
        </div>
        <div>
          <h1 className="text-white font-bold text-3xl mb-2 text-center md:text-left">Need Help?</h1>
          <p className="text-muted text-lg text-center md:text-left mb-6">
            We're here to assist you with any questions or issues you might have regarding Pakfolio. 
            Send us an email directly, and our support team will get back to you as soon as possible.
          </p>
          
          <div className="flex flex-col sm:flex-row items-center gap-4 text-center md:text-left">
            <a 
              href="mailto:help@pakfolio.pk" 
              className="btn-primary flex items-center gap-2"
            >
              <Mail size={18} />
              Email help@pakfolio.pk
            </a>
            <span className="text-muted text-sm">Response time: Usually within 24 hours</span>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
         <div className="bg-surface border border-border rounded-2xl p-6">
            <div className="w-10 h-10 rounded-xl bg-white/5 flex items-center justify-center mb-4">
               <Shield size={20} className="text-white" />
            </div>
            <h3 className="text-white font-bold text-lg mb-2">Account Security</h3>
            <p className="text-muted text-sm">
              If you believe your account has been compromised or you've experienced a security issue, please contact us immediately so we can lock your account and investigate.
            </p>
         </div>
         <div className="bg-surface border border-border rounded-2xl p-6">
            <div className="w-10 h-10 rounded-xl bg-white/5 flex items-center justify-center mb-4">
               <BookOpen size={20} className="text-white" />
            </div>
            <h3 className="text-white font-bold text-lg mb-2">Feature Requests</h3>
            <p className="text-muted text-sm">
              Have an idea for how we can improve Pakfolio? We are constantly looking to add new features that help you track the PSX. Send us your feedback!
            </p>
         </div>
      </div>
    </div>
  );
}

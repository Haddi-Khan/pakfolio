import { Link } from "react-router-dom";

export function Footer() {
  const currentYear = new Date().getFullYear();

  return (
    <footer className="w-full bg-bg border-t border-border mt-auto">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 flex flex-col md:flex-row items-center justify-between gap-4">
        <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded-lg bg-white/5 border border-white/10 flex items-center justify-center p-0.5">
               <img src="/logo.png" alt="Pakfolio" className="w-full h-full object-contain" />
            </div>
            <span className="text-white font-bold text-sm tracking-wide">Pakfolio</span>
        </div>
        
        <nav className="flex gap-6 text-sm text-muted">
          <Link to="/" className="hover:text-soft transition-colors">Home</Link>
          <Link to="/tools/sip" className="hover:text-soft transition-colors">Tools</Link>
          <Link to="/support" className="hover:text-soft transition-colors">Support</Link>
          <Link to="/privacy" className="hover:text-soft transition-colors">Privacy Policy</Link>
          <Link to="/terms" className="hover:text-soft transition-colors">Terms & Conditions</Link>
        </nav>

        <div className="text-xs text-muted/50">
          &copy; {currentYear} Pakfolio.pk. All rights reserved.
        </div>
      </div>
    </footer>
  );
}

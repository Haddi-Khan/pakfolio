import { BrowserRouter, Routes, Route, Navigate, useLocation } from "react-router-dom";
import { AuthProvider, useAuth } from "./context/AuthContext";
import { PortfolioProvider } from "./context/PortfolioContext";
import { ThemeProvider } from "./context/ThemeContext";
import { Dashboard } from "./pages/Dashboard";
import { AuthPage } from "./pages/AuthPage";
import { VerifyEmail } from "./pages/VerifyEmail";
import { ForgotPassword } from "./pages/ForgotPassword";
import { ResetPassword } from "./pages/ResetPassword";
import { Landing } from "./pages/Landing";
import { Home } from "./pages/Home";
import { StockDetail } from "./pages/StockDetail";
import { Tools } from "./pages/Tools";
import { Markets } from "./pages/Markets";
import { Support } from "./pages/Support";
import { Terms } from "./pages/Terms";
import { Privacy } from "./pages/Privacy";
import { Footer } from "./components/Footer";
import { Navbar } from "./components/Navbar";

// Pages that have their own full-screen layout (no shared Navbar/Footer)
const NO_CHROME_PATHS = ["/login", "/verify", "/forgot-password", "/reset-password"];

function Layout({ children }) {
  const location = useLocation();
  const showChrome = !NO_CHROME_PATHS.some((p) => location.pathname.startsWith(p));
  return (
    <div className="flex flex-col min-h-screen relative">
      {showChrome && <Navbar />}
      <div className="flex-1 flex flex-col">{children}</div>
      {showChrome && <Footer />}
    </div>
  );
}

function AppInner() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen bg-bg flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-accent border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <Layout>
      <Routes>
        {/* Auth pages — full screen, no chrome */}
        <Route path="/login" element={user ? <Navigate to="/dashboard" replace /> : <AuthPage />} />
        <Route path="/verify" element={<VerifyEmail />} />
        <Route path="/forgot-password" element={user ? <Navigate to="/dashboard" replace /> : <ForgotPassword />} />
        <Route path="/reset-password" element={user ? <Navigate to="/dashboard" replace /> : <ResetPassword />} />

        {/* Public landing */}
        <Route path="/" element={<Landing />} />

        {/* Public market pages */}
        <Route path="/markets/:type" element={<Markets />} />
        <Route path="/markets" element={<Navigate to="/markets/stocks" replace />} />
        <Route path="/stocks/:symbol" element={<StockDetail />} />
        <Route path="/mutual-funds/:symbol" element={<StockDetail />} />
        <Route path="/stock/:symbol" element={<Navigate to="/stocks/:symbol" replace />} />

        {/* Public tool pages */}
        <Route path="/tools/:toolId" element={<Tools />} />
        <Route path="/tools" element={<Navigate to="/tools/sip" replace />} />

        {/* Static pages */}
        <Route path="/support" element={<Support />} />
        <Route path="/terms" element={<Terms />} />
        <Route path="/privacy" element={<Privacy />} />

        {/* Portfolio pages — require auth */}
        <Route
          path="/dashboard"
          element={
            user ? (
              <PortfolioProvider>
                <Home />
              </PortfolioProvider>
            ) : (
              <Navigate to="/login" replace />
            )
          }
        />
        <Route
          path="/portfolio/:pid"
          element={
            user ? (
              <PortfolioProvider>
                <Dashboard />
              </PortfolioProvider>
            ) : (
              <Navigate to="/login" replace />
            )
          }
        />

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Layout>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <ThemeProvider>
        <AuthProvider>
          <AppInner />
        </AuthProvider>
      </ThemeProvider>
    </BrowserRouter>
  );
}

export function Terms() {
  return (
    <div className="max-w-4xl mx-auto space-y-6 fade-in p-2 md:p-6 lg:p-8">
      <div className="bg-surface border border-border rounded-2xl p-8">
        <h1 className="text-white font-bold text-3xl mb-8">Terms and Conditions</h1>
        
        <div className="space-y-8 text-muted">
            <section>
                <h2 className="text-white font-semibold text-xl mb-3">1. Acceptance of Terms</h2>
                <p className="text-sm leading-relaxed">
                  By accessing and using Pakfolio.pk ("the Service"), you accept and agree to be bound by the terms and provision of this agreement.
                </p>
            </section>

            <section>
                <h2 className="text-white font-semibold text-xl mb-3">2. Description of Service</h2>
                <p className="text-sm leading-relaxed">
                  Pakfolio provides a personal portfolio tracking application for educational and informational purposes only. The data provided on the Service, including stock prices, mutual fund net asset values, and historical charts, is sourced from third-party APIs and is not guaranteed to be accurate, complete, or timely.
                </p>
            </section>

            <section>
                <h2 className="text-white font-semibold text-xl mb-3">3. Not Financial Advice</h2>
                <div className="bg-accent/10 border border-accent/20 rounded-xl p-4 text-accent text-sm mb-4">
                   The information provided on Pakfolio does not constitute investment advice, financial advice, trading advice, or any other sort of advice, and you should not treat any of the website's content as such.
                </div>
                <p className="text-sm leading-relaxed">
                  Pakfolio does not recommend that any stock or mutual fund should be bought, sold, or held by you. Conduct your own due diligence and consult your financial advisor before making any investment decisions.
                </p>
            </section>

            <section>
                <h2 className="text-white font-semibold text-xl mb-3">4. User Accounts</h2>
                <p className="text-sm leading-relaxed">
                  To use certain features of the Service, you must create an account. You are responsible for maintaining the confidentiality of your account password. You are also responsible for all activities that occur in connection with your account. You agree to notify us immediately of any unauthorized use of your account.
                </p>
            </section>

            <section>
                <h2 className="text-white font-semibold text-xl mb-3">5. Disclaimer of Warranties</h2>
                <p className="text-sm leading-relaxed">
                  The Service is provided on an "as is" and "as available" basis without any warranties of any kind. We do not guarantee that the Service will always be safe, secure, or error-free, or that the Service will function without disruptions, delays, or imperfections.
                </p>
            </section>
            
            <section>
                <h2 className="text-white font-semibold text-xl mb-3">6. Contact Information</h2>
                <p className="text-sm leading-relaxed">
                  If you have any questions about these Terms, please contact us at <a href="mailto:help@pakfolio.pk" className="text-accent hover:underline">help@pakfolio.pk</a>.
                </p>
            </section>
        </div>
      </div>
    </div>
  );
}

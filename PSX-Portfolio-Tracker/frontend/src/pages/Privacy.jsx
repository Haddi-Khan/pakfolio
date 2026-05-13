export function Privacy() {
  return (
    <div className="max-w-4xl mx-auto space-y-6 fade-in p-2 md:p-6 lg:p-8">
      <div className="bg-surface border border-border rounded-2xl p-8">
        <h1 className="text-white font-bold text-3xl mb-8">Privacy Policy</h1>
        
        <div className="space-y-8 text-muted">
            <section>
                <h2 className="text-white font-semibold text-xl mb-3">1. Information We Collect</h2>
                <p className="text-sm leading-relaxed">
                  We collect information you provide directly to us when you create an account, such as your email address. If you use social login features, we may collect information from the respective social providers as permitted by their terms.
                </p>
            </section>
Prefix
            <section>
                <h2 className="text-white font-semibold text-xl mb-3">2. How We Use Your Information</h2>
                <p className="text-sm leading-relaxed">
                  We use the information we collect to provide, maintain, and improve our services, including to personalize your experience and to communicate with you about your account.
                </p>
            </section>

            <section>
                <h2 className="text-white font-semibold text-xl mb-3">3. Data Security</h2>
                <div className="bg-accent/10 border border-accent/20 rounded-xl p-4 text-accent text-sm mb-4">
                   We take reasonable measures to help protect information about you from loss, theft, misuse, and unauthorized access.
                </div>
                <p className="text-sm leading-relaxed">
                  However, no method of transmission over the Internet or electronic storage is 100% secure, and we cannot guarantee absolute security.
                </p>
            </section>

            <section>
                <h2 className="text-white font-semibold text-xl mb-3">4. Cookies</h2>
                <p className="text-sm leading-relaxed">
                  We use cookies and similar tracking technologies to track the activity on our Service and hold certain information to improve your experience.
                </p>
            </section>

            <section>
                <h2 className="text-white font-semibold text-xl mb-3">5. Third-Party Services</h2>
                <p className="text-sm leading-relaxed">
                  Our Service may contain links to other sites that are not operated by us. If you click on a third-party link, you will be directed to that third party's site. We strongly advise you to review the Privacy Policy of every site you visit.
                </p>
            </section>
            
            <section>
                <h2 className="text-white font-semibold text-xl mb-3">6. Contact Us</h2>
                <p className="text-sm leading-relaxed">
                  If you have any questions about this Privacy Policy, please contact us at <a href="mailto:help@pakfolio.pk" className="text-accent hover:underline">help@pakfolio.pk</a>.
                </p>
            </section>
        </div>
      </div>
    </div>
  );
}

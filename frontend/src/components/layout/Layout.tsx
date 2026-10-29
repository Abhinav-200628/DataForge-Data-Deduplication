import React, { useState, useEffect } from 'react';
import { Outlet } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { Header } from './Header';
import { api } from '../../services/api';
import { HealthStatus, PipelineRun } from '../../types';

export const Layout: React.FC = () => {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [latestRun, setLatestRun] = useState<PipelineRun | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const fetchGlobalTelemetry = async () => {
    setIsLoading(true);
    try {
      const [h, summary] = await Promise.all([
        api.getHealth().catch(() => null),
        api.getDashboardSummary().catch(() => null),
      ]);
      setHealth(h);
      if (summary?.latest_run) {
        setLatestRun(summary.latest_run as unknown as PipelineRun);
      }
    } catch {
      // ignore global telemetry poll error
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchGlobalTelemetry();
    const interval = setInterval(fetchGlobalTelemetry, 15000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="min-h-screen bg-[#080D18] flex text-slate-100">
      {/* Desktop Sidebar */}
      <div className="hidden lg:block w-64 flex-shrink-0">
        <Sidebar />
      </div>

      {/* Mobile Drawer */}
      {mobileMenuOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <div
            className="fixed inset-0 bg-black/80 backdrop-blur-sm"
            onClick={() => setMobileMenuOpen(false)}
          />
          <div className="fixed inset-y-0 left-0 w-64 z-50 shadow-2xl">
            <Sidebar onCloseMobile={() => setMobileMenuOpen(false)} />
          </div>
        </div>
      )}

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0">
        <Header
          onToggleMobileMenu={() => setMobileMenuOpen(!mobileMenuOpen)}
          health={health}
          latestRun={latestRun}
          isLoading={isLoading}
          onRefresh={fetchGlobalTelemetry}
        />
        <main className="flex-1 p-6 lg:p-8 max-w-7xl w-full mx-auto">
          <Outlet context={{ refreshGlobal: fetchGlobalTelemetry }} />
        </main>
      </div>
    </div>
  );
};


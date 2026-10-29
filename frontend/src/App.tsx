import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Layout } from './components/layout/Layout';
import { OverviewPage } from './pages/OverviewPage';
import { PipelineRunsPage } from './pages/PipelineRunsPage';
import { CustomerDeduplicationPage } from './pages/CustomerDeduplicationPage';
import { ProductDeduplicationPage } from './pages/ProductDeduplicationPage';
import { ReviewQueuePage } from './pages/ReviewQueuePage';
import { DataQualityPage } from './pages/DataQualityPage';
import { ReportsPage } from './pages/ReportsPage';
import { SettingsPage } from './pages/SettingsPage';

export const App: React.FC = () => {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<OverviewPage />} />
          <Route path="runs" element={<PipelineRunsPage />} />
          <Route path="customers" element={<CustomerDeduplicationPage />} />
          <Route path="products" element={<ProductDeduplicationPage />} />
          <Route path="review-queue" element={<ReviewQueuePage />} />
          <Route path="data-quality" element={<DataQualityPage />} />
          <Route path="reports" element={<ReportsPage />} />
          <Route path="settings" element={<SettingsPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
};

export default App;

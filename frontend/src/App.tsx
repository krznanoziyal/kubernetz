import React, { Suspense, lazy } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';

const HomePage = lazy(() =>
  import('./pages/HomePage').then((m) => ({ default: m.HomePage }))
);
const EditorPage = lazy(() =>
  import('./pages/EditorPage').then((m) => ({ default: m.EditorPage }))
);
const GeneratePage = lazy(() =>
  import('./pages/GeneratePage').then((m) => ({ default: m.GeneratePage }))
);

const LoadingFallback: React.FC = () => (
  <div className="flex items-center justify-center h-screen bg-gray-950">
    <div className="flex flex-col items-center gap-3">
      <div className="h-10 w-10 border-3 border-blue-500 border-t-transparent rounded-full animate-spin" />
      <p className="text-gray-400 text-sm">Loading KubeBlueprint…</p>
    </div>
  </div>
);

const App: React.FC = () => {
  return (
    <Suspense fallback={<LoadingFallback />}>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/editor" element={<EditorPage />} />
        <Route path="/generate" element={<GeneratePage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Suspense>
  );
};

export default App;

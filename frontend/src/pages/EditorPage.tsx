import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Upload,
  Code2,
  CheckCheck,
  Wand2,
  Box,
  ChevronRight,
  AlertCircle,
  Loader2,
} from 'lucide-react';
import { clsx } from 'clsx';
import { DiagramUploader } from '../components/DiagramUploader';
import { MermaidInput } from '../components/MermaidInput';
import { ArchitectureGraph } from '../components/ArchitectureGraph';
import { Button } from '../components/ui/Button';
import { useArchitectureStore } from '../stores/architectureStore';
import { useGeneration } from '../hooks/useGeneration';

type InputTab = 'upload' | 'mermaid';

export const EditorPage: React.FC = () => {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<InputTab>('upload');

  const {
    platform,
    hasParsed,
    isParsing,
    diagramPlatformType,
    updatePlatform,
  } = useArchitectureStore();

  const {
    validate,
    generate,
    isValidating,
    isGenerating,
    validationReport,
    validationError,
    generationError,
  } = useGeneration();

  const handleValidate = async () => {
    await validate();
  };

  const handleGenerate = async () => {
    const result = await generate();
    if (result) {
      navigate('/generate');
    }
  };

  const handleValidateAndGenerate = async () => {
    await validate();
    const result = await generate();
    if (result) {
      navigate('/generate');
    }
  };

  const workloadCount = platform.clusters.reduce(
    (acc, c) =>
      acc + c.namespaces.reduce((a, n) => a + n.workloads.length, 0),
    0
  );
  const nsCount = platform.clusters.reduce(
    (acc, c) => acc + c.namespaces.length,
    0
  );

  return (
    <div className="flex flex-col h-screen bg-gray-950 text-gray-100 overflow-hidden">
      {/* Top Bar */}
      <header className="flex items-center justify-between px-5 py-3 border-b border-gray-800 flex-shrink-0 bg-gray-900/80">
        <div className="flex items-center gap-3">
          <div className="h-7 w-7 rounded-lg bg-blue-600 flex items-center justify-center">
            <Box className="h-4 w-4 text-white" />
          </div>
          <span className="font-bold tracking-tight">KubeBlueprint</span>
          <ChevronRight className="h-4 w-4 text-gray-600" />
          <span className="text-gray-400 text-sm">Editor</span>
        </div>

        {/* Platform Summary */}
        {hasParsed && (
          <div className="hidden md:flex items-center gap-4 text-xs text-gray-500">
            <span>
              <span className="text-gray-300 font-medium">
                {platform.clusters.length}
              </span>{' '}
              cluster{platform.clusters.length !== 1 ? 's' : ''}
            </span>
            <span>
              <span className="text-gray-300 font-medium">{nsCount}</span>{' '}
              namespace{nsCount !== 1 ? 's' : ''}
            </span>
            <span>
              <span className="text-gray-300 font-medium">{workloadCount}</span>{' '}
              workload{workloadCount !== 1 ? 's' : ''}
            </span>
            {diagramPlatformType && (
              <span className="px-2 py-0.5 bg-gray-800 border border-gray-700 rounded text-gray-400">
                {diagramPlatformType}
              </span>
            )}
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            leftIcon={
              isValidating ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <CheckCheck className="h-4 w-4" />
              )
            }
            onClick={handleValidate}
            disabled={!hasParsed || isValidating || isGenerating}
            loading={isValidating}
          >
            Validate
          </Button>
          <Button
            variant="primary"
            size="sm"
            leftIcon={
              isGenerating ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Wand2 className="h-4 w-4" />
              )
            }
            onClick={handleGenerate}
            disabled={!hasParsed || isGenerating || isValidating}
            loading={isGenerating}
          >
            Generate
          </Button>
        </div>
      </header>

      {/* Error Banner */}
      {(validationError || generationError) && (
        <div className="flex items-center gap-2 px-5 py-2.5 bg-red-900/30 border-b border-red-800/50 flex-shrink-0">
          <AlertCircle className="h-4 w-4 text-red-400 flex-shrink-0" />
          <span className="text-red-300 text-sm">
            {validationError || generationError}
          </span>
        </div>
      )}

      {/* Validation Summary Banner */}
      {validationReport && !validationError && (
        <div
          className={clsx(
            'flex items-center gap-3 px-5 py-2 border-b flex-shrink-0',
            validationReport.passed
              ? 'bg-green-900/20 border-green-800/50'
              : 'bg-red-900/20 border-red-800/50'
          )}
        >
          <CheckCheck
            className={clsx(
              'h-4 w-4 flex-shrink-0',
              validationReport.passed ? 'text-green-400' : 'text-red-400'
            )}
          />
          <span
            className={clsx(
              'text-sm font-medium',
              validationReport.passed ? 'text-green-300' : 'text-red-300'
            )}
          >
            {validationReport.passed
              ? 'Validation passed'
              : `Validation failed — ${validationReport.errors.length} error${validationReport.errors.length !== 1 ? 's' : ''}`}
          </span>
          {!validationReport.passed && (
            <Button
              variant="primary"
              size="sm"
              onClick={handleValidateAndGenerate}
              className="ml-auto"
              disabled={isGenerating}
              loading={isGenerating}
            >
              Generate Anyway
            </Button>
          )}
          {validationReport.passed && (
            <Button
              variant="primary"
              size="sm"
              leftIcon={<Wand2 className="h-4 w-4" />}
              onClick={handleGenerate}
              className="ml-auto"
              disabled={isGenerating}
              loading={isGenerating}
            >
              Proceed to Generate
            </Button>
          )}
        </div>
      )}

      {/* Main Content */}
      <div className="flex flex-1 min-h-0 overflow-hidden">
        {/* Left Panel — Input */}
        <div className="w-80 flex-shrink-0 flex flex-col border-r border-gray-800 bg-gray-900/50">
          {/* Tab Switcher */}
          <div className="flex border-b border-gray-800 flex-shrink-0">
            <button
              onClick={() => setActiveTab('upload')}
              className={clsx(
                'flex-1 flex items-center justify-center gap-2 py-3 text-sm font-medium transition-colors',
                activeTab === 'upload'
                  ? 'text-blue-400 border-b-2 border-blue-500 bg-blue-950/20'
                  : 'text-gray-500 hover:text-gray-300'
              )}
              type="button"
            >
              <Upload className="h-4 w-4" />
              Upload
            </button>
            <button
              onClick={() => setActiveTab('mermaid')}
              className={clsx(
                'flex-1 flex items-center justify-center gap-2 py-3 text-sm font-medium transition-colors',
                activeTab === 'mermaid'
                  ? 'text-blue-400 border-b-2 border-blue-500 bg-blue-950/20'
                  : 'text-gray-500 hover:text-gray-300'
              )}
              type="button"
            >
              <Code2 className="h-4 w-4" />
              Mermaid
            </button>
          </div>

          {/* Input Content */}
          <div className="flex-1 overflow-y-auto p-4">
            {activeTab === 'upload' ? (
              <DiagramUploader />
            ) : (
              <MermaidInput />
            )}
          </div>

          {/* Platform Name Edit */}
          {hasParsed && (
            <div className="flex-shrink-0 border-t border-gray-800 p-4">
              <label className="text-xs text-gray-500 font-medium block mb-1.5">
                Platform name
              </label>
              <input
                type="text"
                value={platform.name}
                onChange={(e) => updatePlatform({ name: e.target.value })}
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500/30"
              />
            </div>
          )}
        </div>

        {/* Right Panel — Graph */}
        <div className="flex-1 relative overflow-hidden">
          {isParsing && (
            <div className="absolute inset-0 z-10 flex flex-col items-center justify-center bg-gray-950/60 backdrop-blur-sm">
              <Loader2 className="h-10 w-10 animate-spin text-blue-400 mb-3" />
              <p className="text-gray-300 font-medium">Parsing diagram…</p>
              <p className="text-gray-500 text-sm mt-1">
                Extracting Kubernetes components
              </p>
            </div>
          )}
          <ArchitectureGraph />
        </div>
      </div>
    </div>
  );
};

import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Wand2,
  Settings2,
  ShieldCheck,
  FileCode2,
  Download,
  ArrowLeft,
  Box,
  ChevronRight,
  Loader2,
  AlertCircle,
  Info,
} from 'lucide-react';
import { clsx } from 'clsx';
import { GenerationOptions } from '../components/GenerationOptions';
import { ValidationReport } from '../components/ValidationReport';
import { FilePreview } from '../components/FilePreview';
import { ExportPanel } from '../components/ExportPanel';
import { Button } from '../components/ui/Button';
import { useGeneration } from '../hooks/useGeneration';
import { useArchitectureStore } from '../stores/architectureStore';

type ActivePanel = 'options' | 'validation' | 'files' | 'export';

interface TabButtonProps {
  id: ActivePanel;
  label: string;
  icon: React.ReactNode;
  badge?: number;
  active: boolean;
  onClick: () => void;
}

const TabButton: React.FC<TabButtonProps> = ({
  id: _id,
  label,
  icon,
  badge,
  active,
  onClick,
}) => (
  <button
    onClick={onClick}
    type="button"
    className={clsx(
      'flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors whitespace-nowrap',
      active
        ? 'text-blue-400 border-blue-500 bg-blue-950/20'
        : 'text-gray-500 border-transparent hover:text-gray-300 hover:border-gray-600'
    )}
  >
    {icon}
    {label}
    {badge !== undefined && badge > 0 && (
      <span
        className={clsx(
          'px-1.5 py-0.5 rounded-full text-xs font-bold',
          active ? 'bg-blue-700 text-white' : 'bg-gray-700 text-gray-300'
        )}
      >
        {badge}
      </span>
    )}
  </button>
);

export const GeneratePage: React.FC = () => {
  const navigate = useNavigate();
  const [activePanel, setActivePanel] = useState<ActivePanel>('options');

  const {
    platform,
    isGenerating,
    isValidating,
    generationResult,
    generationError,
    validationReport,
    validationError,
    validateAndGenerate,
    generate,
    validate,
  } = useGeneration();

  const { hasParsed } = useArchitectureStore();

  const handleGenerate = async () => {
    const result = await generate();
    if (result) {
      setActivePanel('files');
    }
  };

  const handleValidateAndGenerate = async () => {
    const result = await validateAndGenerate();
    if (result) {
      setActivePanel('files');
    }
  };

  const errorCount = validationReport?.errors.length ?? 0;
  const warningCount = validationReport?.warnings.length ?? 0;
  const fileCount = generationResult?.files.length ?? 0;

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
          <span className="text-gray-400 text-sm">Generate</span>
          {platform.name && (
            <>
              <ChevronRight className="h-4 w-4 text-gray-600" />
              <span className="text-gray-300 text-sm font-medium truncate max-w-[200px]">
                {platform.name}
              </span>
            </>
          )}
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="sm"
            leftIcon={<ArrowLeft className="h-4 w-4" />}
            onClick={() => navigate('/editor')}
          >
            Back to Editor
          </Button>
          <Button
            variant="outline"
            size="sm"
            leftIcon={
              isValidating ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <ShieldCheck className="h-4 w-4" />
              )
            }
            onClick={() => {
              validate();
              setActivePanel('validation');
            }}
            disabled={isValidating || isGenerating}
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
            disabled={isGenerating || isValidating}
            loading={isGenerating}
          >
            Generate
          </Button>
        </div>
      </header>

      {/* Error Banner */}
      {(generationError || validationError) && (
        <div className="flex items-center gap-2 px-5 py-2.5 bg-red-900/30 border-b border-red-800/50 flex-shrink-0">
          <AlertCircle className="h-4 w-4 text-red-400 flex-shrink-0" />
          <span className="text-red-300 text-sm">
            {generationError || validationError}
          </span>
          {generationError && (
            <Button
              variant="ghost"
              size="sm"
              onClick={handleValidateAndGenerate}
              className="ml-auto text-red-300"
            >
              Try validate + generate
            </Button>
          )}
        </div>
      )}

      {/* No Diagram Warning */}
      {!hasParsed && (
        <div className="flex items-center gap-2 px-5 py-2.5 bg-yellow-900/20 border-b border-yellow-800/50 flex-shrink-0">
          <Info className="h-4 w-4 text-yellow-400 flex-shrink-0" />
          <span className="text-yellow-300 text-sm">
            No diagram parsed yet. Generation will use the default empty platform.
            <button
              onClick={() => navigate('/editor')}
              className="ml-2 text-yellow-200 underline"
              type="button"
            >
              Go to Editor
            </button>
          </span>
        </div>
      )}

      {/* Main Layout */}
      <div className="flex flex-1 min-h-0 overflow-hidden">
        {/* Left Sidebar — Options */}
        <div className="w-72 flex-shrink-0 flex flex-col border-r border-gray-800 bg-gray-900/40 overflow-y-auto">
          <div className="flex items-center gap-2 px-4 py-3 border-b border-gray-800">
            <Settings2 className="h-4 w-4 text-gray-400" />
            <span className="text-sm font-semibold text-gray-200">
              Generation Options
            </span>
          </div>
          <div className="flex-1 p-4">
            <GenerationOptions />
          </div>

          {/* Validate + Generate CTA */}
          <div className="flex-shrink-0 p-4 border-t border-gray-800 space-y-2">
            <Button
              className="w-full"
              variant="primary"
              leftIcon={
                isGenerating ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Wand2 className="h-4 w-4" />
                )
              }
              onClick={handleGenerate}
              loading={isGenerating}
              disabled={isGenerating || isValidating}
            >
              {isGenerating ? 'Generating…' : 'Generate Now'}
            </Button>
            <Button
              className="w-full"
              variant="outline"
              leftIcon={
                isValidating ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <ShieldCheck className="h-4 w-4" />
                )
              }
              onClick={handleValidateAndGenerate}
              loading={isValidating}
              disabled={isValidating || isGenerating}
            >
              {isValidating ? 'Validating…' : 'Validate + Generate'}
            </Button>
          </div>
        </div>

        {/* Right Panel — Tabs */}
        <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
          {/* Tab Bar */}
          <div className="flex border-b border-gray-800 overflow-x-auto flex-shrink-0 bg-gray-900/30">
            <TabButton
              id="options"
              label="Overview"
              icon={<Settings2 className="h-4 w-4" />}
              active={activePanel === 'options'}
              onClick={() => setActivePanel('options')}
            />
            <TabButton
              id="validation"
              label="Validation"
              icon={<ShieldCheck className="h-4 w-4" />}
              badge={errorCount + warningCount}
              active={activePanel === 'validation'}
              onClick={() => setActivePanel('validation')}
            />
            <TabButton
              id="files"
              label="Generated Files"
              icon={<FileCode2 className="h-4 w-4" />}
              badge={fileCount}
              active={activePanel === 'files'}
              onClick={() => setActivePanel('files')}
            />
            <TabButton
              id="export"
              label="Export"
              icon={<Download className="h-4 w-4" />}
              active={activePanel === 'export'}
              onClick={() => setActivePanel('export')}
            />
          </div>

          {/* Panel Content */}
          <div className="flex-1 overflow-auto">
            {/* Overview Panel */}
            {activePanel === 'options' && (
              <div className="p-6 max-w-2xl">
                <h2 className="text-lg font-semibold text-gray-100 mb-1">
                  Platform Overview
                </h2>
                <p className="text-gray-400 text-sm mb-6">
                  Review your parsed architecture and configure generation
                  settings.
                </p>

                <div className="grid grid-cols-2 gap-3 mb-6">
                  {[
                    { label: 'Platform', value: platform.name },
                    {
                      label: 'Clusters',
                      value: platform.clusters.length,
                    },
                    {
                      label: 'Environments',
                      value: platform.environments.join(', ') || '—',
                    },
                    {
                      label: 'GitOps',
                      value: platform.gitops_tool || '—',
                    },
                    {
                      label: 'External deps',
                      value: platform.external_dependencies.length,
                    },
                    {
                      label: 'Cloud resources',
                      value: platform.cloud_resources.length,
                    },
                  ].map((item) => (
                    <div
                      key={item.label}
                      className="bg-gray-800/50 border border-gray-700 rounded-lg p-3"
                    >
                      <p className="text-xs text-gray-500 mb-0.5">
                        {item.label}
                      </p>
                      <p className="text-sm font-medium text-gray-200 truncate">
                        {String(item.value)}
                      </p>
                    </div>
                  ))}
                </div>

                {platform.assumptions.length > 0 && (
                  <div>
                    <h3 className="text-sm font-semibold text-gray-300 mb-2">
                      Parser assumptions
                    </h3>
                    <ul className="space-y-1.5">
                      {platform.assumptions.map((a, i) => (
                        <li
                          key={i}
                          className="text-xs text-gray-400 flex items-start gap-2"
                        >
                          <span className="text-yellow-500 mt-0.5 flex-shrink-0">
                            ◆
                          </span>
                          {a}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {!generationResult && (
                  <div className="mt-8 p-5 bg-blue-900/10 border border-blue-800/30 rounded-xl text-center">
                    <Wand2 className="h-8 w-8 text-blue-500 mx-auto mb-2" />
                    <p className="text-blue-300 font-medium mb-1">
                      Ready to generate
                    </p>
                    <p className="text-blue-400/70 text-sm">
                      Click "Generate Now" to create your project scaffold
                    </p>
                  </div>
                )}
              </div>
            )}

            {/* Validation Panel */}
            {activePanel === 'validation' && (
              <div className="p-6">
                {validationReport ? (
                  <ValidationReport report={validationReport} />
                ) : (
                  <div className="flex flex-col items-center justify-center py-16 text-center">
                    <ShieldCheck className="h-12 w-12 text-gray-600 mb-4" />
                    <p className="text-gray-400 font-medium mb-1">
                      No validation report yet
                    </p>
                    <p className="text-gray-600 text-sm mb-4">
                      Run validation to check your architecture
                    </p>
                    <Button
                      variant="outline"
                      leftIcon={<ShieldCheck className="h-4 w-4" />}
                      onClick={() => validate()}
                      loading={isValidating}
                    >
                      Run Validation
                    </Button>
                  </div>
                )}
              </div>
            )}

            {/* Files Panel */}
            {activePanel === 'files' && (
              <div className="h-full p-4">
                {generationResult ? (
                  <FilePreview files={generationResult.files} />
                ) : (
                  <div className="flex flex-col items-center justify-center h-full py-16 text-center">
                    <FileCode2 className="h-12 w-12 text-gray-600 mb-4" />
                    <p className="text-gray-400 font-medium mb-1">
                      No files generated yet
                    </p>
                    <p className="text-gray-600 text-sm mb-4">
                      Generate your scaffold to preview the output files
                    </p>
                    <Button
                      variant="primary"
                      leftIcon={<Wand2 className="h-4 w-4" />}
                      onClick={handleGenerate}
                      loading={isGenerating}
                    >
                      Generate Now
                    </Button>
                  </div>
                )}
              </div>
            )}

            {/* Export Panel */}
            {activePanel === 'export' && (
              <div className="p-6 max-w-lg">
                <h2 className="text-lg font-semibold text-gray-100 mb-1">
                  Export Scaffold
                </h2>
                <p className="text-gray-400 text-sm mb-6">
                  Download your complete project scaffold as a ZIP archive.
                </p>
                {generationResult ? (
                  <ExportPanel generationResult={generationResult} />
                ) : (
                  <div
                    className={clsx(
                      'flex flex-col items-center justify-center py-12 text-center',
                      'border-2 border-dashed border-gray-700 rounded-xl'
                    )}
                  >
                    <Download className="h-10 w-10 text-gray-600 mb-3" />
                    <p className="text-gray-400 font-medium mb-1">
                      Nothing to export yet
                    </p>
                    <p className="text-gray-600 text-sm mb-4">
                      Generate your scaffold first
                    </p>
                    <Button
                      variant="primary"
                      leftIcon={<Wand2 className="h-4 w-4" />}
                      onClick={handleGenerate}
                      loading={isGenerating}
                    >
                      Generate
                    </Button>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

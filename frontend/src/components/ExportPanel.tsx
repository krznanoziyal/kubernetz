import React, { useState } from 'react';
import { Download, FileArchive, Loader2, AlertCircle, CheckCircle2 } from 'lucide-react';
import { clsx } from 'clsx';
import { useGeneration } from '../hooks/useGeneration';
import { Button } from './ui/Button';
import type { GenerationResult } from '../types/platform';

interface ExportPanelProps {
  generationResult: GenerationResult;
}

export const ExportPanel: React.FC<ExportPanelProps> = ({
  generationResult,
}) => {
  const { downloadZip, platform } = useGeneration();
  const [isDownloading, setIsDownloading] = useState(false);
  const [downloadError, setDownloadError] = useState<string | null>(null);
  const [downloaded, setDownloaded] = useState(false);

  const files = generationResult.files;
  const filesByType: Record<string, number> = {};

  files.forEach((f) => {
    const ext = f.path.split('.').pop()?.toLowerCase() ?? 'other';
    filesByType[ext] = (filesByType[ext] ?? 0) + 1;
  });

  const handleDownload = async () => {
    setIsDownloading(true);
    setDownloadError(null);
    try {
      await downloadZip();
      setDownloaded(true);
    } catch (err) {
      setDownloadError(
        err instanceof Error ? err.message : 'Download failed'
      );
    } finally {
      setIsDownloading(false);
    }
  };

  const totalSize = files.reduce((acc, f) => acc + f.content.length, 0);
  const sizeStr =
    totalSize > 1024 * 1024
      ? `${(totalSize / 1024 / 1024).toFixed(1)} MB`
      : `${Math.round(totalSize / 1024)} KB`;

  return (
    <div className="flex flex-col gap-4">
      {/* Stats Row */}
      <div className="grid grid-cols-3 gap-3">
        <div className="bg-gray-800/60 border border-gray-700 rounded-xl p-3 text-center">
          <div className="text-2xl font-bold text-white">{files.length}</div>
          <div className="text-xs text-gray-400 mt-0.5">Files</div>
        </div>
        <div className="bg-gray-800/60 border border-gray-700 rounded-xl p-3 text-center">
          <div className="text-2xl font-bold text-white">{sizeStr}</div>
          <div className="text-xs text-gray-400 mt-0.5">Total size</div>
        </div>
        <div className="bg-gray-800/60 border border-gray-700 rounded-xl p-3 text-center">
          <div className="text-2xl font-bold text-white">
            {generationResult.assumptions.length}
          </div>
          <div className="text-xs text-gray-400 mt-0.5">Assumptions</div>
        </div>
      </div>

      {/* File Type Breakdown */}
      <div className="flex flex-wrap gap-2">
        {Object.entries(filesByType).map(([ext, count]) => (
          <div
            key={ext}
            className="flex items-center gap-1.5 px-2.5 py-1 bg-gray-700/50 rounded-lg"
          >
            <span className="text-xs font-mono text-gray-300">.{ext}</span>
            <span className="text-xs text-gray-500">×{count}</span>
          </div>
        ))}
      </div>

      {/* Warnings */}
      {generationResult.warnings.length > 0 && (
        <div className="rounded-lg bg-yellow-900/20 border border-yellow-800/50 p-3">
          <p className="text-yellow-300 text-xs font-semibold mb-1.5">
            Generation warnings
          </p>
          <ul className="space-y-1">
            {generationResult.warnings.map((w, i) => (
              <li key={i} className="text-yellow-400/80 text-xs">
                • {w}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Download Button */}
      <div className="flex flex-col gap-2">
        <Button
          variant="primary"
          size="lg"
          leftIcon={
            isDownloading ? (
              <Loader2 className="h-5 w-5 animate-spin" />
            ) : downloaded ? (
              <CheckCircle2 className="h-5 w-5" />
            ) : (
              <Download className="h-5 w-5" />
            )
          }
          onClick={handleDownload}
          loading={isDownloading}
          disabled={isDownloading}
          className={clsx(
            'w-full',
            downloaded && !isDownloading && 'bg-green-700 hover:bg-green-600'
          )}
        >
          {isDownloading
            ? 'Preparing ZIP…'
            : downloaded
            ? 'Downloaded!'
            : 'Download ZIP'}
        </Button>

        {downloadError && (
          <div className="flex items-start gap-2 p-2.5 bg-red-900/20 border border-red-700/50 rounded-lg">
            <AlertCircle className="h-4 w-4 text-red-400 flex-shrink-0 mt-0.5" />
            <p className="text-red-300 text-xs">{downloadError}</p>
          </div>
        )}

        <p className="text-xs text-gray-500 text-center">
          <FileArchive className="h-3.5 w-3.5 inline mr-1" />
          {platform.name} scaffold — ready to deploy
        </p>
      </div>
    </div>
  );
};

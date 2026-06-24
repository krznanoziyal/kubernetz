import React, { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload, FileType, AlertCircle, CheckCircle2 } from 'lucide-react';
import { clsx } from 'clsx';
import { useArchitectureStore } from '../stores/architectureStore';
import apiClient from '../api/client';

const ACCEPTED_FORMATS = [
  { ext: '.xml', label: 'draw.io XML', mime: 'text/xml' },
  { ext: '.drawio', label: 'draw.io', mime: 'application/xml' },
  { ext: '.json', label: 'Excalidraw JSON', mime: 'application/json' },
  { ext: '.png', label: 'PNG Image', mime: 'image/png' },
  { ext: '.jpg', label: 'JPEG Image', mime: 'image/jpeg' },
  { ext: '.jpeg', label: 'JPEG Image', mime: 'image/jpeg' },
];

const ACCEPT_MAP = {
  'text/xml': ['.xml', '.drawio'],
  'application/xml': ['.drawio'],
  'application/json': ['.json'],
  'image/png': ['.png'],
  'image/jpeg': ['.jpg', '.jpeg'],
};

export const DiagramUploader: React.FC = () => {
  const {
    isParsing,
    parseError,
    hasParsed,
    diagramFile,
    setDiagramFile,
    setIsParsing,
    setParseError,
    setParsedPlatform,
  } = useArchitectureStore();

  const [uploadSuccess, setUploadSuccess] = useState(false);

  const onDrop = useCallback(
    async (acceptedFiles: File[]) => {
      const file = acceptedFiles[0];
      if (!file) return;

      setDiagramFile(file);
      setIsParsing(true);
      setParseError(null);
      setUploadSuccess(false);

      try {
        const result = await apiClient.parseDiagram(file);
        setParsedPlatform(result.parsed, result.platform);
        setUploadSuccess(true);
      } catch (err) {
        const message =
          err instanceof Error ? err.message : 'Failed to parse diagram';
        setParseError(message);
        setDiagramFile(null);
      } finally {
        setIsParsing(false);
      }
    },
    [setDiagramFile, setIsParsing, setParseError, setParsedPlatform]
  );

  const { getRootProps, getInputProps, isDragActive, isDragReject } =
    useDropzone({
      onDrop,
      accept: ACCEPT_MAP,
      maxFiles: 1,
      maxSize: 20 * 1024 * 1024, // 20 MB
      disabled: isParsing,
    });

  const borderColor = isDragReject
    ? 'border-red-500'
    : isDragActive
    ? 'border-blue-400'
    : uploadSuccess && hasParsed
    ? 'border-green-600'
    : 'border-gray-600 hover:border-gray-400';

  return (
    <div className="space-y-3">
      <div
        {...getRootProps()}
        className={clsx(
          'relative flex flex-col items-center justify-center',
          'border-2 border-dashed rounded-xl p-8 cursor-pointer',
          'transition-all duration-200 bg-gray-800/50',
          borderColor,
          isDragActive && 'bg-blue-900/20',
          isDragReject && 'bg-red-900/20',
          isParsing && 'opacity-60 cursor-not-allowed'
        )}
      >
        <input {...getInputProps()} />

        {isParsing ? (
          <div className="flex flex-col items-center gap-3">
            <div className="animate-spin h-10 w-10 border-3 border-blue-500 border-t-transparent rounded-full" />
            <p className="text-gray-300 text-sm font-medium">Parsing diagram…</p>
            <p className="text-gray-500 text-xs">
              Extracting architecture components
            </p>
          </div>
        ) : uploadSuccess && hasParsed && diagramFile ? (
          <div className="flex flex-col items-center gap-3">
            <CheckCircle2 className="h-10 w-10 text-green-400" />
            <p className="text-green-300 font-medium text-sm">
              {diagramFile.name}
            </p>
            <p className="text-gray-400 text-xs">
              Successfully parsed — drop a new file to replace
            </p>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-3">
            <div
              className={clsx(
                'p-3 rounded-full',
                isDragActive ? 'bg-blue-800' : 'bg-gray-700'
              )}
            >
              <Upload
                className={clsx(
                  'h-7 w-7',
                  isDragActive ? 'text-blue-300' : 'text-gray-400'
                )}
              />
            </div>
            {isDragActive ? (
              <p className="text-blue-300 font-medium text-sm">
                Drop the file here…
              </p>
            ) : (
              <>
                <div className="text-center">
                  <p className="text-gray-200 font-medium text-sm">
                    Drop your diagram here
                  </p>
                  <p className="text-gray-400 text-xs mt-1">
                    or{' '}
                    <span className="text-blue-400 underline">
                      click to browse
                    </span>
                  </p>
                </div>
              </>
            )}
          </div>
        )}
      </div>

      {/* Accepted Formats */}
      <div className="flex flex-wrap gap-1.5">
        {ACCEPTED_FORMATS.map((fmt) => (
          <span
            key={fmt.ext}
            className="inline-flex items-center gap-1 px-2 py-0.5 bg-gray-700/50 rounded text-xs text-gray-400"
          >
            <FileType className="h-3 w-3" />
            {fmt.ext}
          </span>
        ))}
        <span className="text-xs text-gray-500 self-center ml-1">
          Max 20 MB
        </span>
      </div>

      {/* Error Message */}
      {parseError && (
        <div className="flex items-start gap-2 p-3 bg-red-900/20 border border-red-700/50 rounded-lg">
          <AlertCircle className="h-4 w-4 text-red-400 mt-0.5 flex-shrink-0" />
          <div>
            <p className="text-red-300 text-sm font-medium">Parse Error</p>
            <p className="text-red-400 text-xs mt-0.5">{parseError}</p>
          </div>
        </div>
      )}
    </div>
  );
};

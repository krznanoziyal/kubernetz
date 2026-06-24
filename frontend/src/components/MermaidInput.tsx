import React, { useState } from 'react';
import { Code2, Play, AlertCircle, RotateCcw } from 'lucide-react';
import { useArchitectureStore } from '../stores/architectureStore';
import apiClient from '../api/client';
import { Button } from './ui/Button';

const PLACEHOLDER = `graph TD
  subgraph cluster-prod["Production Cluster"]
    subgraph ns-app["namespace: app"]
      D1[web-api\\nDeployment x3]
      D2[worker\\nDeployment x2]
      SVC1[web-api-svc\\nService:ClusterIP]
      ING[ingress\\nIngress]
    end
    subgraph ns-data["namespace: data"]
      SS1[postgres\\nStatefulSet x1]
      SS2[redis\\nStatefulSet x3]
    end
  end
  ING --> SVC1 --> D1 --> SS1
  D1 --> SS2
  D2 --> SS1`;

export const MermaidInput: React.FC = () => {
  const {
    diagramText,
    setDiagramText,
    isParsing,
    parseError,
    setIsParsing,
    setParseError,
    setParsedPlatform,
  } = useArchitectureStore();

  const [diagramName, setDiagramName] = useState('my-architecture');
  const [parseSuccess, setParseSuccess] = useState(false);

  const handleParse = async () => {
    if (!diagramText.trim()) {
      setParseError('Please enter Mermaid diagram text');
      return;
    }

    setIsParsing(true);
    setParseError(null);
    setParseSuccess(false);

    try {
      const result = await apiClient.parseMermaid(diagramText, diagramName);
      setParsedPlatform(result.parsed, result.platform);
      setParseSuccess(true);
    } catch (err) {
      const message =
        err instanceof Error ? err.message : 'Failed to parse Mermaid diagram';
      setParseError(message);
    } finally {
      setIsParsing(false);
    }
  };

  const handleReset = () => {
    setDiagramText('');
    setParseError(null);
    setParseSuccess(false);
  };

  const handleLoadExample = () => {
    setDiagramText(PLACEHOLDER);
    setParseError(null);
    setParseSuccess(false);
  };

  return (
    <div className="flex flex-col gap-3">
      {/* Name Input */}
      <div className="flex gap-2 items-center">
        <label className="text-xs text-gray-400 font-medium whitespace-nowrap">
          Diagram name:
        </label>
        <input
          type="text"
          value={diagramName}
          onChange={(e) => setDiagramName(e.target.value)}
          className="flex-1 bg-gray-700/50 border border-gray-600 rounded-lg px-3 py-1.5 text-sm text-gray-200 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500/30"
          placeholder="my-architecture"
        />
      </div>

      {/* Textarea */}
      <div className="relative">
        <div className="absolute top-2 right-2 z-10">
          <span className="text-xs text-gray-500 bg-gray-800 px-2 py-0.5 rounded font-mono">
            Mermaid
          </span>
        </div>
        <textarea
          value={diagramText}
          onChange={(e) => {
            setDiagramText(e.target.value);
            if (parseSuccess) setParseSuccess(false);
          }}
          className={`
            w-full h-56 bg-gray-900/80 border rounded-xl px-4 py-3 pr-16
            font-mono text-xs text-gray-200 resize-none
            focus:outline-none focus:ring-1 transition-colors
            placeholder:text-gray-600
            ${
              parseSuccess
                ? 'border-green-600 focus:border-green-500 focus:ring-green-500/30'
                : 'border-gray-700 focus:border-blue-500 focus:ring-blue-500/30'
            }
          `}
          placeholder={PLACEHOLDER}
          spellCheck={false}
          disabled={isParsing}
        />
      </div>

      {/* Action row */}
      <div className="flex gap-2 items-center justify-between">
        <button
          onClick={handleLoadExample}
          className="flex items-center gap-1.5 text-xs text-gray-400 hover:text-gray-200 transition-colors"
          type="button"
        >
          <Code2 className="h-3.5 w-3.5" />
          Load example
        </button>

        <div className="flex gap-2">
          {(diagramText || parseSuccess) && (
            <Button
              variant="ghost"
              size="sm"
              leftIcon={<RotateCcw className="h-3.5 w-3.5" />}
              onClick={handleReset}
              type="button"
            >
              Clear
            </Button>
          )}
          <Button
            variant="primary"
            size="sm"
            leftIcon={<Play className="h-3.5 w-3.5" />}
            onClick={handleParse}
            loading={isParsing}
            disabled={!diagramText.trim()}
            type="button"
          >
            {isParsing ? 'Parsing…' : 'Parse'}
          </Button>
        </div>
      </div>

      {/* Error */}
      {parseError && (
        <div className="flex items-start gap-2 p-3 bg-red-900/20 border border-red-700/50 rounded-lg">
          <AlertCircle className="h-4 w-4 text-red-400 mt-0.5 flex-shrink-0" />
          <div>
            <p className="text-red-300 text-sm font-medium">Parse Error</p>
            <p className="text-red-400 text-xs mt-0.5">{parseError}</p>
          </div>
        </div>
      )}

      {/* Success */}
      {parseSuccess && !parseError && (
        <div className="p-2.5 bg-green-900/20 border border-green-700/50 rounded-lg">
          <p className="text-green-300 text-xs font-medium">
            Architecture parsed successfully
          </p>
        </div>
      )}
    </div>
  );
};

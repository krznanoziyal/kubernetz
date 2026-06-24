import { useCallback } from 'react';
import { useArchitectureStore } from '../stores/architectureStore';
import apiClient from '../api/client';
import type { GenerationRequest } from '../types/platform';

export function useGeneration() {
  const {
    platform,
    generationOptions,
    isGenerating,
    generationResult,
    generationError,
    setIsGenerating,
    setGenerationResult,
    setGenerationError,
    validationReport,
    isValidating,
    validationError,
    setIsValidating,
    setValidationReport,
    setValidationError,
  } = useArchitectureStore();

  const buildRequest = useCallback((): GenerationRequest => ({
    platform,
    options: generationOptions,
  }), [platform, generationOptions]);

  const validate = useCallback(async () => {
    setIsValidating(true);
    setValidationError(null);
    try {
      const report = await apiClient.validateArchitecture(platform);
      setValidationReport(report);
      return report;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Validation failed';
      setValidationError(message);
      return null;
    } finally {
      setIsValidating(false);
    }
  }, [platform, setIsValidating, setValidationError, setValidationReport]);

  const generate = useCallback(async () => {
    setIsGenerating(true);
    setGenerationError(null);
    try {
      const request = buildRequest();
      const result = await apiClient.generate(request);
      setGenerationResult(result);
      return result;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Generation failed';
      setGenerationError(message);
      return null;
    } finally {
      setIsGenerating(false);
    }
  }, [buildRequest, setIsGenerating, setGenerationError, setGenerationResult]);

  const validateAndGenerate = useCallback(async () => {
    const report = await validate();
    if (!report) return null;
    if (!report.passed && report.errors.length > 0) {
      setGenerationError(
        `Validation failed with ${report.errors.length} error(s). Fix errors before generating.`
      );
      return null;
    }
    return generate();
  }, [validate, generate, setGenerationError]);

  const downloadZip = useCallback(async () => {
    try {
      const request = buildRequest();
      const blob = await apiClient.exportZip(request);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${platform.name.replace(/\s+/g, '-').toLowerCase()}-scaffold.zip`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Export failed';
      setGenerationError(message);
    }
  }, [buildRequest, platform.name, setGenerationError]);

  return {
    platform,
    generationOptions,
    isGenerating,
    generationResult,
    generationError,
    isValidating,
    validationReport,
    validationError,
    validate,
    generate,
    validateAndGenerate,
    downloadZip,
  };
}

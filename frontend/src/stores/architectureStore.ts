import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import type {
  Platform,
  ValidationReport,
  GenerationResult,
  GenerationOptions,
} from '../types/platform';

// ─── Default Values ────────────────────────────────────────────────────────────

const defaultPlatform: Platform = {
  id: 'default',
  name: 'Untitled Architecture',
  description: '',
  clusters: [],
  external_dependencies: [],
  cloud_resources: [],
  terraform_resources: [],
  edges: [],
  environments: ['dev', 'staging', 'prod'],
  gitops_tool: 'argocd',
  assumptions: [],
  metadata: {},
};

const defaultOptions: GenerationOptions = {
  generate_helm: true,
  generate_argocd: true,
  generate_terraform: false,
  generate_observability: false,
  generate_policies: false,
  environments: ['dev', 'staging', 'prod'],
  gitops_tool: 'argocd',
  terraform_backend: 's3',
};

// ─── Store State ───────────────────────────────────────────────────────────────

export interface ArchitectureState {
  // Diagram
  diagramFile: File | null;
  diagramText: string;
  diagramPlatformType: string;

  // Platform model
  platform: Platform;
  hasParsed: boolean;

  // Validation
  validationReport: ValidationReport | null;
  isValidating: boolean;
  validationError: string | null;

  // Generation
  generationResult: GenerationResult | null;
  isGenerating: boolean;
  generationError: string | null;

  // Options
  generationOptions: GenerationOptions;

  // UI
  isParsing: boolean;
  parseError: string | null;
  selectedFile: string | null;

  // Actions
  setDiagramFile: (file: File | null) => void;
  setDiagramText: (text: string) => void;
  setParsedPlatform: (platform: Platform, platformType: string) => void;
  updatePlatform: (updates: Partial<Platform>) => void;
  resetPlatform: () => void;

  setValidationReport: (report: ValidationReport | null) => void;
  setIsValidating: (v: boolean) => void;
  setValidationError: (err: string | null) => void;

  setGenerationResult: (result: GenerationResult | null) => void;
  setIsGenerating: (v: boolean) => void;
  setGenerationError: (err: string | null) => void;

  setIsParsing: (v: boolean) => void;
  setParseError: (err: string | null) => void;

  updateGenerationOptions: (opts: Partial<GenerationOptions>) => void;
  setSelectedFile: (path: string | null) => void;

  reset: () => void;
}

// ─── Store Implementation ─────────────────────────────────────────────────────

export const useArchitectureStore = create<ArchitectureState>()(
  devtools(
    (set) => ({
      // Initial state
      diagramFile: null,
      diagramText: '',
      diagramPlatformType: '',
      platform: defaultPlatform,
      hasParsed: false,
      validationReport: null,
      isValidating: false,
      validationError: null,
      generationResult: null,
      isGenerating: false,
      generationError: null,
      generationOptions: defaultOptions,
      isParsing: false,
      parseError: null,
      selectedFile: null,

      // Diagram actions
      setDiagramFile: (file) => set({ diagramFile: file, parseError: null }),
      setDiagramText: (text) => set({ diagramText: text }),

      setParsedPlatform: (platform, platformType) =>
        set({
          platform,
          diagramPlatformType: platformType,
          hasParsed: true,
          parseError: null,
          validationReport: null,
          generationResult: null,
        }),

      updatePlatform: (updates) =>
        set((state) => ({ platform: { ...state.platform, ...updates } })),

      resetPlatform: () =>
        set({
          platform: defaultPlatform,
          hasParsed: false,
          validationReport: null,
          generationResult: null,
        }),

      // Validation actions
      setValidationReport: (report) => set({ validationReport: report }),
      setIsValidating: (v) => set({ isValidating: v }),
      setValidationError: (err) => set({ validationError: err }),

      // Generation actions
      setGenerationResult: (result) => set({ generationResult: result }),
      setIsGenerating: (v) => set({ isGenerating: v }),
      setGenerationError: (err) => set({ generationError: err }),

      // UI actions
      setIsParsing: (v) => set({ isParsing: v }),
      setParseError: (err) => set({ parseError: err }),
      updateGenerationOptions: (opts) =>
        set((state) => ({
          generationOptions: { ...state.generationOptions, ...opts },
        })),
      setSelectedFile: (path) => set({ selectedFile: path }),

      // Full reset
      reset: () =>
        set({
          diagramFile: null,
          diagramText: '',
          diagramPlatformType: '',
          platform: defaultPlatform,
          hasParsed: false,
          validationReport: null,
          isValidating: false,
          validationError: null,
          generationResult: null,
          isGenerating: false,
          generationError: null,
          generationOptions: defaultOptions,
          isParsing: false,
          parseError: null,
          selectedFile: null,
        }),
    }),
    { name: 'architecture-store' }
  )
);

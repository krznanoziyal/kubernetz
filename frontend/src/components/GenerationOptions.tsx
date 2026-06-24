import React from 'react';
import { Settings2, Globe, Server, GitBranch } from 'lucide-react';
import { clsx } from 'clsx';
import { useArchitectureStore } from '../stores/architectureStore';

interface ToggleProps {
  label: string;
  description?: string;
  checked: boolean;
  onChange: (v: boolean) => void;
  disabled?: boolean;
}

const Toggle: React.FC<ToggleProps> = ({
  label,
  description,
  checked,
  onChange,
  disabled = false,
}) => (
  <label
    className={clsx(
      'flex items-center justify-between p-3 rounded-lg border cursor-pointer transition-colors',
      checked
        ? 'border-blue-700/60 bg-blue-900/20'
        : 'border-gray-700 bg-gray-800/50 hover:border-gray-600',
      disabled && 'opacity-50 cursor-not-allowed'
    )}
  >
    <div>
      <p className="text-sm font-medium text-gray-200">{label}</p>
      {description && (
        <p className="text-xs text-gray-500 mt-0.5">{description}</p>
      )}
    </div>
    <div
      className={clsx(
        'relative inline-flex h-5 w-9 items-center rounded-full transition-colors flex-shrink-0 ml-3',
        checked ? 'bg-blue-600' : 'bg-gray-600'
      )}
    >
      <input
        type="checkbox"
        className="sr-only"
        checked={checked}
        onChange={(e) => !disabled && onChange(e.target.checked)}
        disabled={disabled}
      />
      <span
        className={clsx(
          'inline-block h-3.5 w-3.5 transform rounded-full bg-white shadow transition-transform',
          checked ? 'translate-x-[18px]' : 'translate-x-[3px]'
        )}
      />
    </div>
  </label>
);

const ENVIRONMENTS = ['dev', 'staging', 'prod', 'test', 'qa'] as const;

const GITOPS_TOOLS = [
  { value: 'argocd', label: 'Argo CD' },
  { value: 'flux', label: 'Flux CD' },
  { value: 'none', label: 'None' },
];

const TERRAFORM_BACKENDS = [
  { value: 's3', label: 'AWS S3' },
  { value: 'gcs', label: 'Google GCS' },
  { value: 'azurerm', label: 'Azure Blob' },
  { value: 'local', label: 'Local' },
];

export const GenerationOptions: React.FC = () => {
  const { generationOptions, updateGenerationOptions } = useArchitectureStore();

  const toggleEnv = (env: string) => {
    const current = generationOptions.environments;
    const next = current.includes(env)
      ? current.filter((e) => e !== env)
      : [...current, env];
    updateGenerationOptions({ environments: next });
  };

  return (
    <div className="flex flex-col gap-5">
      {/* Feature Toggles */}
      <div>
        <div className="flex items-center gap-2 mb-3">
          <Settings2 className="h-4 w-4 text-gray-400" />
          <h3 className="text-sm font-semibold text-gray-200">
            Generate Components
          </h3>
        </div>
        <div className="flex flex-col gap-2">
          <Toggle
            label="Helm Charts"
            description="Kubernetes manifests packaged as Helm charts"
            checked={generationOptions.generate_helm}
            onChange={(v) => updateGenerationOptions({ generate_helm: v })}
          />
          <Toggle
            label="Argo CD / GitOps"
            description="Application manifests and ApplicationSets"
            checked={generationOptions.generate_argocd}
            onChange={(v) => updateGenerationOptions({ generate_argocd: v })}
          />
          <Toggle
            label="Terraform"
            description="Infrastructure as Code for cloud resources"
            checked={generationOptions.generate_terraform}
            onChange={(v) => updateGenerationOptions({ generate_terraform: v })}
          />
          <Toggle
            label="Observability"
            description="Prometheus, Grafana, and alerting configs"
            checked={generationOptions.generate_observability}
            onChange={(v) =>
              updateGenerationOptions({ generate_observability: v })
            }
          />
          <Toggle
            label="Network Policies"
            description="Kubernetes NetworkPolicy resources"
            checked={generationOptions.generate_policies}
            onChange={(v) => updateGenerationOptions({ generate_policies: v })}
          />
        </div>
      </div>

      {/* Environments */}
      <div>
        <div className="flex items-center gap-2 mb-3">
          <Globe className="h-4 w-4 text-gray-400" />
          <h3 className="text-sm font-semibold text-gray-200">Environments</h3>
        </div>
        <div className="flex flex-wrap gap-2">
          {ENVIRONMENTS.map((env) => {
            const active = generationOptions.environments.includes(env);
            return (
              <button
                key={env}
                onClick={() => toggleEnv(env)}
                type="button"
                className={clsx(
                  'px-3 py-1.5 rounded-lg text-sm font-medium border transition-all',
                  active
                    ? 'bg-blue-600/30 border-blue-600/70 text-blue-200'
                    : 'bg-gray-800 border-gray-700 text-gray-400 hover:border-gray-500 hover:text-gray-200'
                )}
              >
                {env}
              </button>
            );
          })}
        </div>
      </div>

      {/* GitOps Tool */}
      <div>
        <div className="flex items-center gap-2 mb-3">
          <GitBranch className="h-4 w-4 text-gray-400" />
          <h3 className="text-sm font-semibold text-gray-200">GitOps Tool</h3>
        </div>
        <select
          value={generationOptions.gitops_tool}
          onChange={(e) =>
            updateGenerationOptions({ gitops_tool: e.target.value })
          }
          className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500/30"
        >
          {GITOPS_TOOLS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>

      {/* Terraform Backend */}
      {generationOptions.generate_terraform && (
        <div>
          <div className="flex items-center gap-2 mb-3">
            <Server className="h-4 w-4 text-gray-400" />
            <h3 className="text-sm font-semibold text-gray-200">
              Terraform Backend
            </h3>
          </div>
          <select
            value={generationOptions.terraform_backend}
            onChange={(e) =>
              updateGenerationOptions({ terraform_backend: e.target.value })
            }
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500/30"
          >
            {TERRAFORM_BACKENDS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>
      )}
    </div>
  );
};

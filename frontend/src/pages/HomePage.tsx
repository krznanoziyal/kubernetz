import React from 'react';
import { Link } from 'react-router-dom';
import {
  ArrowRight,
  Box,
  GitBranch,
  Shield,
  Zap,
  Upload,
  Eye,
  Download,
  CheckCircle,
} from 'lucide-react';
import { Button } from '../components/ui/Button';

const FEATURES = [
  {
    icon: <Upload className="h-5 w-5" />,
    title: 'Multi-format Input',
    description:
      'Upload draw.io XML, Excalidraw JSON, Mermaid diagrams, or PNG/JPG screenshots of your architecture.',
    color: 'text-blue-400',
    bg: 'bg-blue-900/20 border-blue-800/50',
  },
  {
    icon: <Eye className="h-5 w-5" />,
    title: 'Live Architecture Graph',
    description:
      'Instantly visualize your parsed Kubernetes architecture as an interactive node graph with cluster/namespace hierarchy.',
    color: 'text-cyan-400',
    bg: 'bg-cyan-900/20 border-cyan-800/50',
  },
  {
    icon: <Shield className="h-5 w-5" />,
    title: 'Validation Engine',
    description:
      'Catch misconfigurations before deployment. Errors, warnings, and intelligent assumptions are surfaced clearly.',
    color: 'text-green-400',
    bg: 'bg-green-900/20 border-green-800/50',
  },
  {
    icon: <Box className="h-5 w-5" />,
    title: 'Helm Chart Generation',
    description:
      'Generate production-ready Helm charts with values files for each environment (dev / staging / prod).',
    color: 'text-purple-400',
    bg: 'bg-purple-900/20 border-purple-800/50',
  },
  {
    icon: <GitBranch className="h-5 w-5" />,
    title: 'GitOps Ready',
    description:
      'Outputs Argo CD Applications, Flux Kustomizations, and full GitOps repository structure out of the box.',
    color: 'text-orange-400',
    bg: 'bg-orange-900/20 border-orange-800/50',
  },
  {
    icon: <Zap className="h-5 w-5" />,
    title: 'Terraform IaC',
    description:
      'Optionally generate Terraform modules for cloud resources: VPCs, EKS/GKE clusters, RDS, S3, and more.',
    color: 'text-yellow-400',
    bg: 'bg-yellow-900/20 border-yellow-800/50',
  },
];

const STEPS = [
  {
    n: '01',
    title: 'Upload or Paste',
    desc: 'Drop your diagram file or paste Mermaid text',
  },
  {
    n: '02',
    title: 'Inspect Graph',
    desc: 'Review the parsed Kubernetes architecture visually',
  },
  {
    n: '03',
    title: 'Configure & Validate',
    desc: 'Choose environments, tooling, and fix any issues',
  },
  {
    n: '04',
    title: 'Generate & Export',
    desc: 'Download the complete project scaffold as a ZIP',
  },
];

export const HomePage: React.FC = () => {
  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      {/* Navbar */}
      <nav className="fixed top-0 left-0 right-0 z-50 border-b border-gray-800/60 bg-gray-950/80 backdrop-blur-sm">
        <div className="max-w-6xl mx-auto px-6 h-14 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="h-7 w-7 rounded-lg bg-blue-600 flex items-center justify-center">
              <Box className="h-4 w-4 text-white" />
            </div>
            <span className="font-bold text-lg tracking-tight">
              KubeBlueprint
            </span>
          </div>
          <Link to="/editor">
            <Button variant="primary" size="sm" rightIcon={<ArrowRight className="h-4 w-4" />}>
              Get Started
            </Button>
          </Link>
        </div>
      </nav>

      {/* Hero */}
      <section className="relative pt-32 pb-24 px-6 overflow-hidden">
        {/* Background gradient blobs */}
        <div className="absolute inset-0 overflow-hidden pointer-events-none">
          <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-blue-600/10 rounded-full blur-3xl" />
          <div className="absolute top-1/3 right-1/4 w-80 h-80 bg-purple-600/10 rounded-full blur-3xl" />
        </div>

        <div className="relative max-w-4xl mx-auto text-center">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-blue-900/40 border border-blue-700/50 text-blue-300 text-xs font-medium mb-6">
            <Zap className="h-3.5 w-3.5" />
            Diagram → Production scaffold in seconds
          </div>

          <h1 className="text-5xl md:text-6xl font-bold tracking-tight leading-tight mb-6">
            Convert Kubernetes
            <br />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-cyan-400">
              Diagrams to Code
            </span>
          </h1>

          <p className="text-lg text-gray-400 max-w-2xl mx-auto mb-10 leading-relaxed">
            KubeBlueprint parses your architecture diagrams and generates
            validated Helm charts, Argo CD manifests, Terraform modules, and
            full GitOps project scaffolds — ready to commit and deploy.
          </p>

          <div className="flex items-center justify-center gap-4 flex-wrap">
            <Link to="/editor">
              <Button
                size="lg"
                rightIcon={<ArrowRight className="h-5 w-5" />}
                className="shadow-lg shadow-blue-900/30"
              >
                Start Building
              </Button>
            </Link>
            <Link to="/generate">
              <Button variant="outline" size="lg">
                Generate from Scratch
              </Button>
            </Link>
          </div>

          {/* Quick stats */}
          <div className="flex items-center justify-center gap-8 mt-12 flex-wrap">
            {['draw.io', 'Excalidraw', 'Mermaid', 'PNG / JPG'].map((fmt) => (
              <div key={fmt} className="flex items-center gap-1.5 text-sm text-gray-500">
                <CheckCircle className="h-4 w-4 text-green-500" />
                {fmt}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* How It Works */}
      <section className="py-16 px-6 border-t border-gray-800/60">
        <div className="max-w-5xl mx-auto">
          <h2 className="text-2xl font-bold text-center mb-10 text-gray-100">
            How it works
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 relative">
            <div className="hidden md:block absolute top-8 left-[12.5%] right-[12.5%] h-px bg-gradient-to-r from-transparent via-gray-700 to-transparent" />
            {STEPS.map((step, i) => (
              <div key={i} className="flex flex-col items-center text-center gap-3">
                <div className="relative z-10 flex items-center justify-center h-14 w-14 rounded-full border-2 border-blue-600/60 bg-gray-900 text-blue-400 font-bold text-sm">
                  {step.n}
                </div>
                <div>
                  <h3 className="font-semibold text-gray-100 text-sm">
                    {step.title}
                  </h3>
                  <p className="text-gray-500 text-xs mt-1">{step.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="py-16 px-6">
        <div className="max-w-6xl mx-auto">
          <h2 className="text-2xl font-bold text-center mb-2 text-gray-100">
            Everything you need
          </h2>
          <p className="text-gray-500 text-center mb-10 text-sm">
            From diagram upload to a production-ready GitOps repository
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {FEATURES.map((f, i) => (
              <div
                key={i}
                className={`rounded-xl border p-5 ${f.bg} transition-transform hover:-translate-y-0.5`}
              >
                <div className={`${f.color} mb-3`}>{f.icon}</div>
                <h3 className="font-semibold text-gray-100 mb-1.5">{f.title}</h3>
                <p className="text-gray-400 text-sm leading-relaxed">
                  {f.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-20 px-6 border-t border-gray-800/60">
        <div className="max-w-2xl mx-auto text-center">
          <h2 className="text-3xl font-bold mb-4">
            Ready to blueprint your cluster?
          </h2>
          <p className="text-gray-400 mb-8">
            Upload your first diagram in seconds. No signup required.
          </p>
          <Link to="/editor">
            <Button
              size="lg"
              rightIcon={<ArrowRight className="h-5 w-5" />}
              className="shadow-xl shadow-blue-900/30"
            >
              Open Editor
            </Button>
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-gray-800/60 py-8 px-6">
        <div className="max-w-6xl mx-auto flex items-center justify-between text-sm text-gray-600">
          <div className="flex items-center gap-2">
            <Box className="h-4 w-4" />
            <span>KubeBlueprint</span>
          </div>
          <div className="flex items-center gap-2">
            <Download className="h-3.5 w-3.5" />
            <span>Export your scaffold anytime</span>
          </div>
        </div>
      </footer>
    </div>
  );
};

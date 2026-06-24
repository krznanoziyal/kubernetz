import React, { useState } from 'react';
import {
  AlertCircle,
  AlertTriangle,
  Info,
  Lightbulb,
  ChevronDown,
  ChevronRight,
  CheckCircle2,
  XCircle,
} from 'lucide-react';
import { clsx } from 'clsx';
import type { ValidationReport as VReport, ValidationIssue } from '../types/platform';
import { Badge } from './ui/Badge';

interface SectionProps {
  title: string;
  issues: ValidationIssue[];
  icon: React.ReactNode;
  colorClass: string;
  bgClass: string;
  borderClass: string;
  defaultOpen?: boolean;
}

const IssueSection: React.FC<SectionProps> = ({
  title,
  issues,
  icon,
  colorClass,
  bgClass,
  borderClass,
  defaultOpen = false,
}) => {
  const [open, setOpen] = useState(defaultOpen);

  if (issues.length === 0) return null;

  return (
    <div className={clsx('rounded-lg border overflow-hidden', borderClass)}>
      <button
        onClick={() => setOpen((o) => !o)}
        className={clsx(
          'w-full flex items-center justify-between px-4 py-2.5',
          'transition-colors hover:brightness-110',
          bgClass
        )}
        type="button"
      >
        <div className="flex items-center gap-2">
          <span className={colorClass}>{icon}</span>
          <span className={clsx('text-sm font-semibold', colorClass)}>
            {title}
          </span>
          <Badge
            variant={
              title === 'Errors'
                ? 'error'
                : title === 'Warnings'
                ? 'warning'
                : title === 'Info'
                ? 'info'
                : 'gray'
            }
          >
            {issues.length}
          </Badge>
        </div>
        {open ? (
          <ChevronDown className={clsx('h-4 w-4', colorClass)} />
        ) : (
          <ChevronRight className={clsx('h-4 w-4', colorClass)} />
        )}
      </button>

      {open && (
        <ul className="divide-y divide-gray-800">
          {issues.map((issue, idx) => (
            <li key={idx} className="px-4 py-3 bg-gray-900/40">
              <div className="flex items-start gap-2">
                <span className={clsx('mt-0.5 flex-shrink-0', colorClass)}>
                  {icon}
                </span>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-gray-200 text-sm font-medium">
                      {issue.message}
                    </span>
                    {issue.code && (
                      <code className="text-[10px] px-1.5 py-0.5 bg-gray-800 rounded text-gray-400 font-mono">
                        {issue.code}
                      </code>
                    )}
                  </div>
                  {issue.component_name && (
                    <p className="text-xs text-gray-400 mt-0.5">
                      Component:{' '}
                      <span className="text-gray-300 font-mono">
                        {issue.component_name}
                      </span>
                    </p>
                  )}
                  {issue.suggestion && (
                    <p className="text-xs text-gray-400 mt-1 italic">
                      Suggestion: {issue.suggestion}
                    </p>
                  )}
                </div>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};

interface ValidationReportProps {
  report: VReport;
}

export const ValidationReport: React.FC<ValidationReportProps> = ({
  report,
}) => {
  const totalIssues =
    report.errors.length +
    report.warnings.length +
    report.info.length +
    report.assumptions.length;

  return (
    <div className="flex flex-col gap-3">
      {/* Header / Pass Badge */}
      <div
        className={clsx(
          'flex items-center justify-between p-3 rounded-xl border',
          report.passed
            ? 'bg-green-900/20 border-green-700/50'
            : 'bg-red-900/20 border-red-700/50'
        )}
      >
        <div className="flex items-center gap-2">
          {report.passed ? (
            <CheckCircle2 className="h-5 w-5 text-green-400" />
          ) : (
            <XCircle className="h-5 w-5 text-red-400" />
          )}
          <span
            className={clsx(
              'font-semibold text-sm',
              report.passed ? 'text-green-300' : 'text-red-300'
            )}
          >
            {report.passed ? 'Validation Passed' : 'Validation Failed'}
          </span>
        </div>
        <div className="flex items-center gap-1.5 flex-wrap justify-end">
          {report.errors.length > 0 && (
            <Badge variant="error">{report.errors.length} error{report.errors.length !== 1 ? 's' : ''}</Badge>
          )}
          {report.warnings.length > 0 && (
            <Badge variant="warning">{report.warnings.length} warning{report.warnings.length !== 1 ? 's' : ''}</Badge>
          )}
          {report.info.length > 0 && (
            <Badge variant="info">{report.info.length} info</Badge>
          )}
          {report.assumptions.length > 0 && (
            <Badge variant="gray">{report.assumptions.length} assumption{report.assumptions.length !== 1 ? 's' : ''}</Badge>
          )}
          {totalIssues === 0 && (
            <Badge variant="success">No issues</Badge>
          )}
        </div>
      </div>

      {/* Issue Sections */}
      <IssueSection
        title="Errors"
        issues={report.errors}
        icon={<AlertCircle className="h-4 w-4" />}
        colorClass="text-red-400"
        bgClass="bg-red-900/20"
        borderClass="border-red-800/50"
        defaultOpen={true}
      />
      <IssueSection
        title="Warnings"
        issues={report.warnings}
        icon={<AlertTriangle className="h-4 w-4" />}
        colorClass="text-yellow-400"
        bgClass="bg-yellow-900/20"
        borderClass="border-yellow-800/50"
        defaultOpen={true}
      />
      <IssueSection
        title="Info"
        issues={report.info}
        icon={<Info className="h-4 w-4" />}
        colorClass="text-blue-400"
        bgClass="bg-blue-900/20"
        borderClass="border-blue-800/50"
      />
      <IssueSection
        title="Assumptions"
        issues={report.assumptions}
        icon={<Lightbulb className="h-4 w-4" />}
        colorClass="text-gray-400"
        bgClass="bg-gray-700/30"
        borderClass="border-gray-700/50"
      />

      {totalIssues === 0 && (
        <div className="text-center py-4 text-gray-500 text-sm">
          No issues found.
        </div>
      )}
    </div>
  );
};

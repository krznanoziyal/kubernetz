import React, { useMemo } from 'react';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import {
  FileCode,
  FolderOpen,
  Folder,
  ChevronRight,
  ChevronDown,
  File,
} from 'lucide-react';
import { clsx } from 'clsx';
import type { GeneratedFile } from '../types/platform';
import { useArchitectureStore } from '../stores/architectureStore';

// ─── File Tree Logic ───────────────────────────────────────────────────────────

interface TreeNode {
  name: string;
  path: string;
  type: 'file' | 'dir';
  children?: TreeNode[];
  file?: GeneratedFile;
}

function buildFileTree(files: GeneratedFile[]): TreeNode[] {
  const root: TreeNode = { name: '', path: '', type: 'dir', children: [] };

  for (const file of files) {
    const parts = file.path.split('/').filter(Boolean);
    let current = root;

    for (let i = 0; i < parts.length; i++) {
      const part = parts[i];
      const isLast = i === parts.length - 1;
      const existingChild = current.children?.find((c) => c.name === part);

      if (isLast) {
        current.children?.push({
          name: part,
          path: file.path,
          type: 'file',
          file,
        });
      } else {
        if (existingChild) {
          current = existingChild;
        } else {
          const newDir: TreeNode = {
            name: part,
            path: parts.slice(0, i + 1).join('/'),
            type: 'dir',
            children: [],
          };
          current.children?.push(newDir);
          current = newDir;
        }
      }
    }
  }

  return root.children ?? [];
}

function getLang(filename: string): string {
  const ext = filename.split('.').pop()?.toLowerCase() ?? '';
  const map: Record<string, string> = {
    yaml: 'yaml',
    yml: 'yaml',
    json: 'json',
    ts: 'typescript',
    tsx: 'tsx',
    js: 'javascript',
    jsx: 'jsx',
    sh: 'bash',
    dockerfile: 'docker',
    tf: 'hcl',
    hcl: 'hcl',
    md: 'markdown',
    toml: 'toml',
    py: 'python',
    go: 'go',
    rs: 'rust',
  };
  return map[ext] ?? 'text';
}

// ─── Tree Node Component ───────────────────────────────────────────────────────

interface TreeNodeProps {
  node: TreeNode;
  depth: number;
  selectedPath: string | null;
  onSelect: (file: GeneratedFile) => void;
  expandedDirs: Set<string>;
  toggleDir: (path: string) => void;
}

const TreeItem: React.FC<TreeNodeProps> = ({
  node,
  depth,
  selectedPath,
  onSelect,
  expandedDirs,
  toggleDir,
}) => {
  const isExpanded = expandedDirs.has(node.path);
  const isSelected = node.path === selectedPath;

  if (node.type === 'dir') {
    return (
      <div>
        <button
          onClick={() => toggleDir(node.path)}
          className="w-full flex items-center gap-1.5 px-2 py-1 hover:bg-gray-700/50 rounded text-left transition-colors"
          style={{ paddingLeft: `${(depth + 1) * 12}px` }}
          type="button"
        >
          {isExpanded ? (
            <ChevronDown className="h-3.5 w-3.5 text-gray-400 flex-shrink-0" />
          ) : (
            <ChevronRight className="h-3.5 w-3.5 text-gray-400 flex-shrink-0" />
          )}
          {isExpanded ? (
            <FolderOpen className="h-3.5 w-3.5 text-yellow-400 flex-shrink-0" />
          ) : (
            <Folder className="h-3.5 w-3.5 text-yellow-500 flex-shrink-0" />
          )}
          <span className="text-xs text-gray-300 truncate">{node.name}</span>
        </button>
        {isExpanded && node.children && (
          <div>
            {node.children.map((child) => (
              <TreeItem
                key={child.path}
                node={child}
                depth={depth + 1}
                selectedPath={selectedPath}
                onSelect={onSelect}
                expandedDirs={expandedDirs}
                toggleDir={toggleDir}
              />
            ))}
          </div>
        )}
      </div>
    );
  }

  return (
    <button
      onClick={() => node.file && onSelect(node.file)}
      className={clsx(
        'w-full flex items-center gap-1.5 px-2 py-1 rounded text-left transition-colors',
        isSelected
          ? 'bg-blue-600/30 text-blue-200'
          : 'hover:bg-gray-700/40 text-gray-400 hover:text-gray-200'
      )}
      style={{ paddingLeft: `${(depth + 1) * 12 + 14}px` }}
      type="button"
    >
      <File className="h-3.5 w-3.5 flex-shrink-0 opacity-70" />
      <span className="text-xs truncate">{node.name}</span>
    </button>
  );
};

// ─── Main Component ────────────────────────────────────────────────────────────

interface FilePreviewProps {
  files: GeneratedFile[];
}

export const FilePreview: React.FC<FilePreviewProps> = ({ files }) => {
  const { selectedFile, setSelectedFile } = useArchitectureStore();

  const tree = useMemo(() => buildFileTree(files), [files]);

  const [expandedDirs, setExpandedDirs] = React.useState<Set<string>>(() => {
    const dirs = new Set<string>();
    // Auto-expand top-level dirs
    files.forEach((f) => {
      const parts = f.path.split('/').filter(Boolean);
      if (parts.length > 1) dirs.add(parts[0]);
    });
    return dirs;
  });

  const toggleDir = (path: string) => {
    setExpandedDirs((prev) => {
      const next = new Set(prev);
      if (next.has(path)) next.delete(path);
      else next.add(path);
      return next;
    });
  };

  const selectedFileObj = useMemo(
    () => files.find((f) => f.path === selectedFile) ?? null,
    [files, selectedFile]
  );

  if (files.length === 0) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-500 text-sm">
        No files generated yet.
      </div>
    );
  }

  return (
    <div className="flex h-full min-h-0 border border-gray-700 rounded-xl overflow-hidden bg-gray-900">
      {/* File Tree Sidebar */}
      <div className="w-56 flex-shrink-0 border-r border-gray-700 overflow-y-auto bg-gray-850">
        <div className="px-3 py-2 border-b border-gray-700 flex items-center gap-2">
          <FileCode className="h-4 w-4 text-gray-400" />
          <span className="text-xs font-medium text-gray-300">
            {files.length} files
          </span>
        </div>
        <div className="py-1">
          {tree.map((node) => (
            <TreeItem
              key={node.path}
              node={node}
              depth={0}
              selectedPath={selectedFile}
              onSelect={(f) => setSelectedFile(f.path)}
              expandedDirs={expandedDirs}
              toggleDir={toggleDir}
            />
          ))}
        </div>
      </div>

      {/* Content Panel */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {selectedFileObj ? (
          <>
            <div className="px-4 py-2 border-b border-gray-700 flex items-center gap-2 bg-gray-800/60 flex-shrink-0">
              <File className="h-4 w-4 text-gray-400" />
              <span className="text-xs font-mono text-gray-300 truncate">
                {selectedFileObj.path}
              </span>
            </div>
            {selectedFileObj.description && (
              <div className="px-4 py-1.5 border-b border-gray-700/50 bg-gray-800/30 flex-shrink-0">
                <p className="text-xs text-gray-400 italic">
                  {selectedFileObj.description}
                </p>
              </div>
            )}
            <div className="flex-1 overflow-auto">
              <SyntaxHighlighter
                language={getLang(selectedFileObj.path)}
                style={vscDarkPlus}
                customStyle={{
                  margin: 0,
                  borderRadius: 0,
                  background: 'transparent',
                  fontSize: '12px',
                  lineHeight: '1.6',
                  minHeight: '100%',
                }}
                showLineNumbers
                lineNumberStyle={{ color: '#4b5563', minWidth: '2.5em' }}
              >
                {selectedFileObj.content}
              </SyntaxHighlighter>
            </div>
          </>
        ) : (
          <div className="flex flex-col items-center justify-center h-full text-center p-8">
            <FileCode className="h-10 w-10 text-gray-600 mb-3" />
            <p className="text-gray-400 text-sm font-medium">
              Select a file to preview
            </p>
            <p className="text-gray-600 text-xs mt-1">
              Click any file in the tree on the left
            </p>
          </div>
        )}
      </div>
    </div>
  );
};

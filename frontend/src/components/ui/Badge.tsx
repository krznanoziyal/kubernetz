import React from 'react';
import { clsx } from 'clsx';

type BadgeVariant =
  | 'default'
  | 'success'
  | 'error'
  | 'warning'
  | 'info'
  | 'gray'
  | 'blue'
  | 'purple';

interface BadgeProps {
  variant?: BadgeVariant;
  children: React.ReactNode;
  className?: string;
  size?: 'sm' | 'md';
}

const variantClasses: Record<BadgeVariant, string> = {
  default: 'bg-gray-700 text-gray-200',
  success: 'bg-green-900/60 text-green-300 border border-green-700/50',
  error: 'bg-red-900/60 text-red-300 border border-red-700/50',
  warning: 'bg-yellow-900/60 text-yellow-300 border border-yellow-700/50',
  info: 'bg-blue-900/60 text-blue-300 border border-blue-700/50',
  gray: 'bg-gray-700/60 text-gray-300 border border-gray-600/50',
  blue: 'bg-blue-800/60 text-blue-200 border border-blue-700/50',
  purple: 'bg-purple-900/60 text-purple-300 border border-purple-700/50',
};

export const Badge: React.FC<BadgeProps> = ({
  variant = 'default',
  children,
  className,
  size = 'sm',
}) => {
  return (
    <span
      className={clsx(
        'inline-flex items-center font-medium rounded-full',
        size === 'sm' ? 'px-2 py-0.5 text-xs' : 'px-3 py-1 text-sm',
        variantClasses[variant],
        className
      )}
    >
      {children}
    </span>
  );
};

import React from 'react';
import { clsx } from 'clsx';

interface CardProps {
  children: React.ReactNode;
  className?: string;
  padding?: 'none' | 'sm' | 'md' | 'lg';
  border?: boolean;
}

interface CardHeaderProps {
  children: React.ReactNode;
  className?: string;
}

interface CardBodyProps {
  children: React.ReactNode;
  className?: string;
}

const paddingClasses = {
  none: '',
  sm: 'p-3',
  md: 'p-4',
  lg: 'p-6',
};

export const Card: React.FC<CardProps> & {
  Header: React.FC<CardHeaderProps>;
  Body: React.FC<CardBodyProps>;
} = ({ children, className, padding = 'md', border = true }) => {
  return (
    <div
      className={clsx(
        'bg-gray-800 rounded-xl',
        border && 'border border-gray-700',
        paddingClasses[padding],
        className
      )}
    >
      {children}
    </div>
  );
};

const CardHeader: React.FC<CardHeaderProps> = ({ children, className }) => (
  <div
    className={clsx(
      'flex items-center justify-between px-4 py-3 border-b border-gray-700',
      className
    )}
  >
    {children}
  </div>
);

const CardBody: React.FC<CardBodyProps> = ({ children, className }) => (
  <div className={clsx('p-4', className)}>{children}</div>
);

Card.Header = CardHeader;
Card.Body = CardBody;

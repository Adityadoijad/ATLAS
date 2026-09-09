import React from 'react';
import { LoaderIcon } from 'lucide-react';
import { cn } from '../../utils/format';

type ButtonVariant = 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger' | 'accent';
type ButtonSize = 'sm' | 'md' | 'lg';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
  icon?: React.ReactNode;
}

const variants: Record<ButtonVariant, string> = {
  primary: 'bg-brand text-white hover:bg-blue-700 shadow-sm',
  secondary: 'bg-surface text-ink border border-line hover:bg-subtle',
  outline: 'border border-line bg-transparent text-ink hover:bg-subtle',
  ghost: 'text-muted hover:text-ink hover:bg-subtle',
  danger: 'bg-danger/10 text-danger border border-danger/25 hover:bg-danger/15',
  accent: 'bg-accent text-white hover:brightness-95'
};

const sizes: Record<ButtonSize, string> = {
  sm: 'h-9 px-3.5 text-[13px] rounded-lg gap-1.5',
  md: 'h-11 px-5 text-sm rounded-xl gap-2',
  lg: 'h-13 px-7 text-[15px] rounded-xl gap-2 py-3.5'
};

export function Button({
  variant = 'primary',
  size = 'md',
  loading,
  icon,
  className,
  children,
  disabled,
  ...props
}: ButtonProps) {
  return (
    <button
      className={cn(
        'inline-flex items-center justify-center font-medium transition-all duration-200 disabled:opacity-50 disabled:pointer-events-none active:scale-[0.98]',
        variants[variant],
        sizes[size],
        className
      )}
      disabled={disabled || loading}
      {...props}>
      
      {loading ? <LoaderIcon className="h-4 w-4 animate-spin" aria-hidden /> : icon}
      {children}
    </button>);

}

export function Card({
  className,
  children,
  as: Tag = 'div',
  ...props
}: React.HTMLAttributes<HTMLElement> & {as?: React.ElementType;}) {
  return (
    <Tag className={cn('bg-surface border border-line rounded-2xl shadow-card', className)} {...props}>
      {children}
    </Tag>);

}

export function Badge({
  children,
  tone = 'neutral',
  className




}: {children: React.ReactNode;tone?: 'neutral' | 'brand' | 'success' | 'warning' | 'danger' | 'accent';className?: string;}) {
  const tones = {
    neutral: 'bg-subtle text-muted',
    brand: 'bg-brand/10 text-brand',
    success: 'bg-success/10 text-success',
    warning: 'bg-warning/10 text-[#B45309] dark:text-warning',
    danger: 'bg-danger/10 text-danger',
    accent: 'bg-accent/10 text-[#0E7490] dark:text-accent'
  };
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-[11px] font-semibold tracking-wide',
        tones[tone],
        className
      )}>
      
      {children}
    </span>);

}

export function Pill({
  active,
  children,
  className,
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & {active?: boolean;}) {
  return (
    <button
      type="button"
      aria-pressed={active}
      className={cn(
        'shrink-0 rounded-full border px-4 py-2 text-[13px] font-medium transition-colors',
        active ?
        'border-brand bg-brand text-white' :
        'border-line bg-surface text-muted hover:text-ink hover:border-ink/20',
        className
      )}
      {...props}>
      
      {children}
    </button>);

}

export function SectionHeading({
  title,
  subtitle,
  action,
  className





}: {title: string;subtitle?: string;action?: React.ReactNode;className?: string;}) {
  return (
    <div className={cn('flex items-end justify-between gap-4', className)}>
      <div>
        <h2 className="text-[22px] sm:text-2xl font-bold text-ink">{title}</h2>
        {subtitle && <p className="mt-1 text-sm text-muted">{subtitle}</p>}
      </div>
      {action}
    </div>);

}

export function Field({
  label,
  hint,
  error,
  children,
  htmlFor






}: {label: string;hint?: string;error?: string;children: React.ReactNode;htmlFor?: string;}) {
  return (
    <div className="space-y-1.5">
      <label htmlFor={htmlFor} className="block text-[13px] font-semibold text-ink">
        {label}
      </label>
      {children}
      {error ?
      <p className="text-xs text-danger">{error}</p> :
      hint ?
      <p className="text-xs text-muted">{hint}</p> :
      null}
    </div>);

}

export const inputClass =
'w-full h-11 rounded-xl border border-line bg-surface px-3.5 text-sm text-ink placeholder:text-muted/70 transition-shadow focus:border-brand focus:shadow-focus focus:outline-none';

export function Input(props: React.InputHTMLAttributes<HTMLInputElement>) {
  return <input {...props} className={cn(inputClass, props.className)} />;
}

export function Textarea(props: React.TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <textarea
      {...props}
      className={cn(inputClass, 'h-auto py-3 leading-relaxed resize-none', props.className)} />);


}

export function Select(props: React.SelectHTMLAttributes<HTMLSelectElement>) {
  return <select {...props} className={cn(inputClass, 'pr-8', props.className)} />;
}

export function Skeleton({ className }: {className?: string;}) {
  return <div className={cn('relative overflow-hidden rounded-xl bg-subtle', className)} aria-hidden />;
}

export function EmptyState({
  icon,
  title,
  description,
  action





}: {icon: React.ReactNode;title: string;description: string;action?: React.ReactNode;}) {
  return (
    <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-line bg-surface px-6 py-16 text-center">
      <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-brand/10 text-brand">{icon}</div>
      <h3 className="text-base font-semibold text-ink">{title}</h3>
      <p className="mt-1 max-w-sm text-sm text-muted">{description}</p>
      {action && <div className="mt-5">{action}</div>}
    </div>);

}

export function ErrorState({ message, onRetry }: {message: string;onRetry?: () => void;}) {
  return (
    <div className="rounded-2xl border border-danger/20 bg-danger/5 p-6 text-center">
      <p className="text-sm font-medium text-danger">{message}</p>
      {onRetry &&
      <Button variant="secondary" size="sm" className="mt-4" onClick={onRetry}>
          Try again
        </Button>
      }
    </div>);

}

export function Tabs({
  tabs,
  value,
  onChange,
  className





}: {tabs: {id: string;label: string;count?: number;}[];value: string;onChange: (id: string) => void;className?: string;}) {
  return (
    <div
      role="tablist"
      aria-label="Filter"
      className={cn('inline-flex items-center gap-1 rounded-xl border border-line bg-surface p-1', className)}>
      
      {tabs.map((tab) => {
        const active = tab.id === value;
        return (
          <button
            key={tab.id}
            role="tab"
            aria-selected={active}
            onClick={() => onChange(tab.id)}
            className={cn(
              'rounded-lg px-3.5 py-2 text-[13px] font-medium transition-colors',
              active ? 'bg-brand text-white' : 'text-muted hover:text-ink'
            )}>
            
            {tab.label}
            {typeof tab.count === 'number' &&
            <span className={cn('ml-1.5 text-[11px]', active ? 'text-white/80' : 'text-muted/70')}>{tab.count}</span>
            }
          </button>);

      })}
    </div>);

}

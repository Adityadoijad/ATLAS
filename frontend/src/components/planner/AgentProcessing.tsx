import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { CheckIcon, LoaderIcon, SparklesIcon } from 'lucide-react';
import { agents } from '../../data/content';
import { AgentPhase } from '../../types';
import { cn } from '../../utils/format';

export function AgentProcessing({ onComplete }: {onComplete: () => void;}) {
  const [index, setIndex] = useState(0);

  useEffect(() => {
    if (index >= agents.length) {
      const done = window.setTimeout(onComplete, 700);
      return () => window.clearTimeout(done);
    }
    const timer = window.setTimeout(() => setIndex((i) => i + 1), 620);
    return () => window.clearTimeout(timer);
  }, [index, onComplete]);

  const progress = Math.round(Math.min(index, agents.length) / agents.length * 100);

  return (
    <div className="mx-auto max-w-3xl py-8">
      <div className="text-center">
        <span className="inline-flex items-center gap-1.5 rounded-full bg-brand/10 px-3 py-1.5 text-[12px] font-semibold text-brand">
          <SparklesIcon className="h-3.5 w-3.5" />
          Multi-agent pipeline running
        </span>
        <h1 className="mt-5 font-display text-3xl font-bold text-ink sm:text-4xl">ATLAS is planning your trip...</h1>
        <p className="mt-2 text-[15px] text-muted">
          Agents are working in parallel on transport, stays, food, weather, routes and budget.
        </p>

        <div className="mx-auto mt-7 max-w-md">
          <div className="h-2 overflow-hidden rounded-full bg-subtle">
            <motion.div className="h-full rounded-full bg-brand" animate={{ width: `${progress}%` }} transition={{ ease: 'easeOut' }} />
          </div>
          <p className="mt-2 text-[12.5px] text-muted">{progress}% complete</p>
        </div>
      </div>

      <ul className="mt-10 grid gap-3 sm:grid-cols-2">
        {agents.map((agent, i) => {
          const phase: AgentPhase = i < index ? 'done' : i === index ? 'running' : 'queued';
          return (
            <motion.li
              key={agent.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.04 }}
              className={cn(
                'flex items-center gap-3 rounded-2xl border bg-surface p-4 transition-colors',
                phase === 'running' ? 'border-brand shadow-card' : 'border-line',
                phase === 'queued' && 'opacity-60'
              )}>
              
              <span
                className={cn(
                  'flex h-9 w-9 shrink-0 items-center justify-center rounded-xl',
                  phase === 'done' ? 'bg-success/10 text-success' : phase === 'running' ? 'bg-brand/10 text-brand' : 'bg-subtle text-muted'
                )}>
                
                {phase === 'done' ?
                <CheckIcon className="h-4.5 w-4.5" /> :
                phase === 'running' ?
                <LoaderIcon className="h-4.5 w-4.5 animate-spin" /> :

                <span className="h-2 w-2 rounded-full bg-current" />
                }
              </span>
              <div className="min-w-0">
                <p className="text-[14px] font-semibold text-ink">{agent.name}</p>
                <p className="truncate text-[12.5px] text-muted">
                  {phase === 'done' ? 'Completed' : agent.task}
                </p>
              </div>
            </motion.li>);

        })}
      </ul>
    </div>);

}

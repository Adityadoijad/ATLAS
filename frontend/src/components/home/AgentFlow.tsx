import { motion } from 'framer-motion';
import { ArrowDownIcon } from 'lucide-react';
import { agents, pipeline } from '../../data/content';
import { Card } from '../ui/Primitives';

export function AgentFlow() {
  return (
    <section className="mx-auto max-w-shell px-5 py-16 lg:px-8">
      <div className="overflow-hidden rounded-3xl border border-line bg-surface p-6 sm:p-10 lg:p-14">
        <div className="mx-auto max-w-2xl text-center">
          <span className="inline-flex rounded-full bg-brand/10 px-3 py-1.5 text-[12px] font-semibold text-brand">
            How ATLAS works
          </span>
          <h2 className="mt-4 font-display text-3xl font-bold text-ink sm:text-4xl">
            One request. Nine specialists. One plan.
          </h2>
          <p className="mt-3 text-[15px] leading-relaxed text-muted">
            You describe the trip. ATLAS breaks it into tasks, runs them across specialised agents, then resolves
            everything into a single itinerary that respects your budget, time and preferences.
          </p>
        </div>

        <div className="mt-12 space-y-3">
          {pipeline.map((step, index) => {
            const isAgentRow = step.label === 'Specialised Agents';
            return (
              <div key={step.label}>
                <motion.div
                  initial={{ opacity: 0, y: 14 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true, margin: '-60px' }}
                  transition={{ duration: 0.35, delay: index * 0.04 }}>
                  
                  {isAgentRow ?
                  <div className="rounded-2xl border border-brand/20 bg-brand/[0.04] p-4 sm:p-5">
                      <p className="text-center text-[13px] font-semibold text-brand">Specialised agents work in parallel</p>
                      <div className="mt-4 grid gap-2.5 sm:grid-cols-2 lg:grid-cols-4">
                        {agents.slice(1, 8).map((agent) =>
                      <div key={agent.id} className="rounded-xl border border-line bg-surface px-3.5 py-3">
                            <p className="text-[13px] font-semibold text-ink">{agent.name}</p>
                            <p className="mt-0.5 text-[12px] leading-snug text-muted">{agent.task}</p>
                          </div>
                      )}
                      </div>
                    </div> :

                  <Card className="mx-auto flex max-w-xl flex-col items-center px-5 py-4 text-center shadow-none">
                      <p className="text-[15px] font-bold text-ink">{step.label}</p>
                      <p className="mt-0.5 text-[13px] text-muted">{step.detail}</p>
                    </Card>
                  }
                </motion.div>
                {index < pipeline.length - 1 &&
                <div className="flex justify-center py-1.5" aria-hidden>
                    <ArrowDownIcon className="h-4 w-4 text-brand/50" />
                  </div>
                }
              </div>);

          })}
        </div>
      </div>
    </section>);

}

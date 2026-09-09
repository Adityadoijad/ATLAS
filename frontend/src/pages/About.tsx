import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { ArrowRightIcon, CpuIcon, DatabaseIcon, GlobeIcon, SparklesIcon, UsersIcon } from 'lucide-react';
import { AgentFlow } from '../components/home/AgentFlow';
import { Card } from '../components/ui/Primitives';
import { IMAGES } from '../data/destinations';

const stack = [
{ label: 'Frontend', value: 'React · TypeScript · Tailwind CSS · Framer Motion' },
{ label: 'Planned backend', value: 'FastAPI service layer with typed endpoints' },
{ label: 'Data', value: 'Supabase PostgreSQL for trips, bookings and community reports' },
{ label: 'Intelligence', value: 'Gemini API for reasoning and natural-language planning' },
{ label: 'Context APIs', value: 'Maps, Weather and traveller review sources' }];


const pillars = [
{
  icon: SparklesIcon,
  title: 'AI-powered travel planning',
  body: 'ATLAS reads a plain-language brief and turns it into a structured, day-by-day plan with times, costs and distances.'
},
{
  icon: CpuIcon,
  title: 'Multi-agent architecture',
  body: 'Rather than one model answering everything, nine specialised agents each own a domain and report back to a planner.'
},
{
  icon: UsersIcon,
  title: 'Community intelligence',
  body: 'Traveller reviews and community reports are summarised into positives, concerns and crowd-level signals.'
},
{
  icon: GlobeIcon,
  title: 'Multilingual by design',
  body: 'Nine Indian languages at launch, with a localisation-ready interface layer throughout the product.'
}];


export function AboutPage() {
  return (
    <div className="pb-10">
      <section className="mx-auto max-w-shell px-5 pt-12 lg:px-8">
        <div className="grid items-center gap-10 lg:grid-cols-2">
          <div>
            <span className="inline-flex rounded-full bg-brand/10 px-3 py-1.5 text-[12px] font-semibold text-brand">
              About ATLAS
            </span>
            <h1 className="mt-5 font-display text-4xl font-extrabold leading-tight text-ink sm:text-5xl">
              Travel decisions, made with evidence.
            </h1>
            <p className="mt-5 text-[16px] leading-relaxed text-muted">
              ATLAS is an AI-powered multi-agent travel planning and decision support platform. It is not a booking
              site and not a chatbot — it is a system that reasons about your constraints, checks them against real
              traveller experience, and shows its work.
            </p>
            <Link
              to="/plan"
              className="mt-8 inline-flex h-12 items-center gap-2 rounded-xl bg-brand px-6 text-[15px] font-semibold text-white">
              
              Try the planner <ArrowRightIcon className="h-4 w-4" />
            </Link>
          </div>
          <img src={IMAGES.heroLake} alt="" className="h-[360px] w-full rounded-3xl object-cover" />
        </div>
      </section>

      <section className="mx-auto max-w-shell px-5 pt-20 lg:px-8">
        <div className="grid gap-4 sm:grid-cols-2">
          {pillars.map((p, i) =>
          <motion.div
            key={p.title}
            initial={{ opacity: 0, y: 14 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: i * 0.05 }}>
            
              <Card className="h-full p-6">
                <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-brand/10 text-brand">
                  <p.icon className="h-5 w-5" />
                </span>
                <h2 className="mt-4 text-[16px] font-bold text-ink">{p.title}</h2>
                <p className="mt-2 text-[14px] leading-relaxed text-muted">{p.body}</p>
              </Card>
            </motion.div>
          )}
        </div>
      </section>

      <AgentFlow />

      <section className="mx-auto max-w-shell px-5 lg:px-8">
        <div className="grid gap-5 lg:grid-cols-2">
          <Card className="p-8">
            <h2 className="font-display text-2xl font-bold text-ink">Future vision</h2>
            <ul className="mt-5 space-y-3 text-[14px] leading-relaxed text-muted">
              <li>· Live re-planning while you travel, driven by weather, delays and closures.</li>
              <li>· Group planning where several travellers' constraints are solved together.</li>
              <li>· Offline itinerary access with voice guidance in regional languages.</li>
              <li>· Verified community reports feeding directly into the recommendation engine.</li>
              <li>· Real booking partners replacing the current demonstration flow.</li>
            </ul>
          </Card>
          <Card className="p-8">
            <div className="flex items-center gap-2">
              <DatabaseIcon className="h-4.5 w-4.5 text-brand" />
              <h2 className="font-display text-2xl font-bold text-ink">Technology</h2>
            </div>
            <dl className="mt-5 divide-y divide-line">
              {stack.map((s) =>
              <div key={s.label} className="py-3.5">
                  <dt className="text-[12.5px] font-semibold uppercase tracking-wide text-muted">{s.label}</dt>
                  <dd className="mt-1 text-[14px] text-ink">{s.value}</dd>
                </div>
              )}
            </dl>
            <p className="mt-4 rounded-xl bg-canvas p-3 text-[12.5px] text-muted">
              The interface talks only to a mock service layer, so connecting the FastAPI backend requires no redesign.
            </p>
          </Card>
        </div>
      </section>
    </div>);

}

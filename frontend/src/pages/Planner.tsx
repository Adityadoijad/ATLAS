import { useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { ArrowLeftIcon, ArrowRightIcon, CheckIcon, SparklesIcon } from 'lucide-react';
import { Button, Card, Field, Input, Pill, Select, Textarea } from '../components/ui/Primitives';
import { AgentProcessing } from '../components/planner/AgentProcessing';
import {
  accessibilityOptions,
  accommodationOptions,
  foodOptions,
  interests as interestOptions,
  transportOptions } from
'../data/content';
import { destinations } from '../data/destinations';
import { generateTripPlan } from '../services/atlasApi';
import { useAtlas } from '../contexts/AtlasContext';
import { PlannerPreferences } from '../types';
import { cn, formatRange, inr } from '../utils/format';

const steps = [
{ id: 1, title: 'Where to?', hint: 'Destination' },
{ id: 2, title: 'When?', hint: 'Travel dates' },
{ id: 3, title: "Who's going?", hint: 'Travellers' },
{ id: 4, title: 'Preferences', hint: 'Interests & budget' },
{ id: 5, title: 'Review', hint: 'Confirm & generate' }];


const emptyPrefs: PlannerPreferences = {
  destination: '',
  startDate: '',
  endDate: '',
  adults: 2,
  children: 0,
  interests: [],
  transport: [],
  accommodation: [],
  food: [],
  accessibility: [],
  budget: 60000,
  currency: 'INR',
  flexibleBudget: true,
  notes: ''
};

function TogglePills({
  options,
  values,
  onToggle,
  label





}: {options: string[];values: string[];onToggle: (value: string) => void;label: string;}) {
  return (
    <fieldset>
      <legend className="mb-2 text-[13px] font-semibold text-ink">{label}</legend>
      <div className="flex flex-wrap gap-2">
        {options.map((option) =>
        <Pill key={option} active={values.includes(option)} onClick={() => onToggle(option)}>
            {option}
          </Pill>
        )}
      </div>
    </fieldset>);

}

export function PlannerPage() {
  const location = useLocation();
  const prefilledDestination = (location.state as { destination?: string } | null)?.destination;
  const [step, setStep] = useState(1);
  const [prefs, setPrefs] = useState<PlannerPreferences>(
    prefilledDestination ? { ...emptyPrefs, destination: prefilledDestination } : emptyPrefs
  );
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [processing, setProcessing] = useState(false);
  const { setPlan, toast } = useAtlas();
  const navigate = useNavigate();

  const update = <K extends keyof PlannerPreferences,>(key: K, value: PlannerPreferences[K]) =>
  setPrefs((p) => ({ ...p, [key]: value }));

  const toggle = (key: 'interests' | 'transport' | 'accommodation' | 'food' | 'accessibility', value: string) =>
  setPrefs((p) => ({
    ...p,
    [key]: p[key].includes(value) ? p[key].filter((v) => v !== value) : [...p[key], value]
  }));

  const validate = (current: number) => {
    const next: Record<string, string> = {};
    if (current === 1 && !prefs.destination.trim()) next.destination = 'Tell ATLAS where you want to go.';
    if (current === 2) {
      if (!prefs.startDate) next.startDate = 'Pick a start date.';
      if (!prefs.endDate) next.endDate = 'Pick an end date.';
      if (prefs.startDate && prefs.endDate && new Date(prefs.endDate) < new Date(prefs.startDate))
      next.endDate = 'End date must be after the start date.';
    }
    if (current === 3 && prefs.adults + prefs.children < 1) next.adults = 'At least one traveller is required.';
    if (current === 4 && prefs.budget <= 0) next.budget = 'Enter a budget above zero.';
    setErrors(next);
    return Object.keys(next).length === 0;
  };

  const next = () => {
    if (!validate(step)) return;
    setStep((s) => Math.min(5, s + 1));
  };

  const generate = async () => {
    setProcessing(true);
    const plan = await generateTripPlan(prefs);
    setPlan(plan);
  };

  if (processing) {
    return (
      <AgentProcessing
        onComplete={() => {
          toast({ title: 'Your itinerary is ready', description: 'Nine agents finished planning your trip.', tone: 'success' });
          navigate('/itinerary');
        }} />);


  }

  return (
    <div className="space-y-6">
      <header>
        <h1 className="font-display text-3xl font-bold text-ink">Plan your trip</h1>
        <p className="mt-1.5 text-[15px] text-muted">
          Five short steps. ATLAS turns them into a complete, budget-aware itinerary.
        </p>
      </header>

      <div className="grid gap-6 lg:grid-cols-[260px_1fr]">
        <nav aria-label="Planner steps">
          <ol className="space-y-1.5">
            {steps.map((s) => {
              const state = s.id === step ? 'current' : s.id < step ? 'done' : 'todo';
              return (
                <li key={s.id}>
                  <button
                    onClick={() => s.id < step && setStep(s.id)}
                    aria-current={state === 'current' ? 'step' : undefined}
                    className={cn(
                      'flex w-full items-center gap-3 rounded-xl border px-3.5 py-3 text-left transition-colors',
                      state === 'current' ?
                      'border-brand bg-brand/5' :
                      state === 'done' ?
                      'border-line bg-surface hover:border-brand/30' :
                      'border-transparent bg-transparent'
                    )}>
                    
                    <span
                      className={cn(
                        'flex h-7 w-7 shrink-0 items-center justify-center rounded-lg text-[12px] font-bold',
                        state === 'current' ?
                        'bg-brand text-white' :
                        state === 'done' ?
                        'bg-success/10 text-success' :
                        'bg-subtle text-muted'
                      )}>
                      
                      {state === 'done' ? <CheckIcon className="h-3.5 w-3.5" /> : s.id}
                    </span>
                    <span>
                      <span className="block text-[13.5px] font-semibold text-ink">{s.title}</span>
                      <span className="block text-[12px] text-muted">{s.hint}</span>
                    </span>
                  </button>
                </li>);

            })}
          </ol>
        </nav>

        <Card className="p-6 sm:p-8">
          <motion.div key={step} initial={{ opacity: 0, x: 12 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.25 }}>
            {step === 1 &&
            <div className="space-y-5">
                <div>
                  <h2 className="text-xl font-bold text-ink">Where to?</h2>
                  <p className="mt-1 text-[13.5px] text-muted">Type a destination or pick a popular one.</p>
                </div>
                <Field label="Destination" error={errors.destination} htmlFor="destination">
                  <Input
                  id="destination"
                  value={prefs.destination}
                  onChange={(e) => update('destination', e.target.value)}
                  placeholder="e.g. Goa, Kyoto, Iceland" />
                
                </Field>
                <div className="flex flex-wrap gap-2">
                  {destinations.slice(0, 8).map((d) =>
                <Pill key={d.id} active={prefs.destination === d.name} onClick={() => update('destination', d.name)}>
                      {d.name}
                    </Pill>
                )}
                </div>
              </div>
            }

            {step === 2 &&
            <div className="space-y-5">
                <div>
                  <h2 className="text-xl font-bold text-ink">When?</h2>
                  <p className="mt-1 text-[13.5px] text-muted">The Weather Agent uses these dates for conditions and crowd levels.</p>
                </div>
                <div className="grid gap-4 sm:grid-cols-2">
                  <Field label="Start date" error={errors.startDate} htmlFor="start">
                    <Input id="start" type="date" value={prefs.startDate} onChange={(e) => update('startDate', e.target.value)} />
                  </Field>
                  <Field label="End date" error={errors.endDate} htmlFor="end">
                    <Input id="end" type="date" value={prefs.endDate} onChange={(e) => update('endDate', e.target.value)} />
                  </Field>
                </div>
              </div>
            }

            {step === 3 &&
            <div className="space-y-5">
                <div>
                  <h2 className="text-xl font-bold text-ink">Who's going?</h2>
                  <p className="mt-1 text-[13.5px] text-muted">Group size affects stays, transport and pacing.</p>
                </div>
                <div className="grid gap-4 sm:grid-cols-2">
                  <Field label="Adults" error={errors.adults} htmlFor="adults">
                    <Input
                    id="adults"
                    type="number"
                    min={0}
                    value={prefs.adults}
                    onChange={(e) => update('adults', Number(e.target.value))} />
                  
                  </Field>
                  <Field label="Children" htmlFor="children">
                    <Input
                    id="children"
                    type="number"
                    min={0}
                    value={prefs.children}
                    onChange={(e) => update('children', Number(e.target.value))} />
                  
                  </Field>
                </div>
              </div>
            }

            {step === 4 &&
            <div className="space-y-7">
                <div>
                  <h2 className="text-xl font-bold text-ink">Preferences</h2>
                  <p className="mt-1 text-[13.5px] text-muted">The more you share, the more personal the itinerary.</p>
                </div>
                <TogglePills label="Interests" options={interestOptions} values={prefs.interests} onToggle={(v) => toggle('interests', v)} />
                <TogglePills label="Transportation" options={transportOptions} values={prefs.transport} onToggle={(v) => toggle('transport', v)} />
                <TogglePills label="Accommodation" options={accommodationOptions} values={prefs.accommodation} onToggle={(v) => toggle('accommodation', v)} />
                <TogglePills label="Food" options={foodOptions} values={prefs.food} onToggle={(v) => toggle('food', v)} />
                <TogglePills label="Accessibility" options={accessibilityOptions} values={prefs.accessibility} onToggle={(v) => toggle('accessibility', v)} />

                <div className="grid gap-4 sm:grid-cols-2">
                  <Field label="Total budget" error={errors.budget} htmlFor="budget">
                    <Input
                    id="budget"
                    type="number"
                    min={0}
                    step={1000}
                    value={prefs.budget}
                    onChange={(e) => update('budget', Number(e.target.value))} />
                  
                  </Field>
                  <Field label="Currency" htmlFor="currency">
                    <Select id="currency" value={prefs.currency} onChange={(e) => update('currency', e.target.value)}>
                      <option value="INR">INR — Indian Rupee</option>
                      <option value="USD">USD — US Dollar</option>
                      <option value="EUR">EUR — Euro</option>
                    </Select>
                  </Field>
                </div>

                <label className="flex items-center gap-3 rounded-xl border border-line p-3.5">
                  <input
                  type="checkbox"
                  checked={prefs.flexibleBudget}
                  onChange={(e) => update('flexibleBudget', e.target.checked)}
                  className="h-4 w-4 accent-[#2563EB]" />
                
                  <span className="text-[13.5px] text-ink">
                    Flexible budget
                    <span className="block text-[12.5px] text-muted">Allow the optimizer to exceed the budget by up to 10% for high-value experiences.</span>
                  </span>
                </label>

                <Field label="Additional preferences" hint="Anything else ATLAS should know." htmlFor="notes">
                  <Textarea
                  id="notes"
                  rows={4}
                  value={prefs.notes}
                  onChange={(e) => update('notes', e.target.value)}
                  placeholder="I prefer quiet places and want to avoid crowded tourist attractions." />
                
                </Field>
              </div>
            }

            {step === 5 &&
            <div className="space-y-5">
                <div>
                  <h2 className="text-xl font-bold text-ink">Review your requirements</h2>
                  <p className="mt-1 text-[13.5px] text-muted">Confirm the brief that goes to the Planner Agent.</p>
                </div>
                <dl className="divide-y divide-line rounded-2xl border border-line">
                  {[
                ['Destination', prefs.destination || 'Not set'],
                ['Dates', formatRange(prefs.startDate, prefs.endDate)],
                ['Travellers', `${prefs.adults} adults · ${prefs.children} children`],
                ['Interests', prefs.interests.join(', ') || 'No preference'],
                ['Transport', prefs.transport.join(', ') || 'No preference'],
                ['Accommodation', prefs.accommodation.join(', ') || 'No preference'],
                ['Food', prefs.food.join(', ') || 'No preference'],
                ['Accessibility', prefs.accessibility.join(', ') || 'None specified'],
                ['Budget', `${inr(prefs.budget)} ${prefs.flexibleBudget ? '· flexible' : '· fixed'}`],
                ['Notes', prefs.notes || '—']].
                map(([label, value]) =>
                <div key={label} className="flex flex-col gap-1 px-4 py-3 sm:flex-row sm:items-baseline sm:gap-6">
                      <dt className="w-40 shrink-0 text-[12.5px] font-semibold uppercase tracking-wide text-muted">{label}</dt>
                      <dd className="text-[14px] text-ink">{value}</dd>
                    </div>
                )}
                </dl>
              </div>
            }
          </motion.div>

          <div className="mt-8 flex items-center justify-between border-t border-line pt-6">
            <Button variant="ghost" onClick={() => setStep((s) => Math.max(1, s - 1))} disabled={step === 1} icon={<ArrowLeftIcon className="h-4 w-4" />}>
              Back
            </Button>
            {step < 5 ?
            <Button onClick={next} icon={<ArrowRightIcon className="h-4 w-4" />}>
                Continue
              </Button> :

            <Button size="lg" onClick={generate} icon={<SparklesIcon className="h-4 w-4" />}>
                Generate My Trip
              </Button>
            }
          </div>
        </Card>
      </div>
    </div>);

}

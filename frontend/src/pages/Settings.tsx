import { useState } from 'react';
import {
  BellIcon,
  GlobeIcon,
  LockIcon,
  PaletteIcon,
  ShieldIcon,
  SlidersHorizontalIcon,
  UserRoundIcon } from
'lucide-react';
import { Button, Card, Field, Input, Select } from '../components/ui/Primitives';
import { useAtlas } from '../contexts/AtlasContext';
import { languages } from '../data/content';
import { cn } from '../utils/format';

const sections = [
{ id: 'account', label: 'Account', icon: UserRoundIcon },
{ id: 'security', label: 'Security', icon: LockIcon },
{ id: 'notifications', label: 'Notifications', icon: BellIcon },
{ id: 'language', label: 'Language', icon: GlobeIcon },
{ id: 'appearance', label: 'Appearance', icon: PaletteIcon },
{ id: 'travel', label: 'Travel Preferences', icon: SlidersHorizontalIcon },
{ id: 'privacy', label: 'Privacy', icon: ShieldIcon }];


function Toggle({
  label,
  description,
  checked,
  onChange





}: {label: string;description: string;checked: boolean;onChange: (v: boolean) => void;}) {
  return (
    <label className="flex items-start justify-between gap-6 border-b border-line py-4 last:border-0">
      <span>
        <span className="block text-[13.5px] font-semibold text-ink">{label}</span>
        <span className="mt-0.5 block text-[12.5px] text-muted">{description}</span>
      </span>
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        aria-label={label}
        onClick={() => onChange(!checked)}
        className={cn(
          'relative h-6 w-11 shrink-0 rounded-full transition-colors',
          checked ? 'bg-brand' : 'bg-subtle'
        )}>
        
        <span
          className={cn(
            'absolute top-0.5 h-5 w-5 rounded-full bg-white shadow transition-transform',
            checked ? 'translate-x-[22px]' : 'translate-x-0.5'
          )} />
        
      </button>
    </label>);

}

export function SettingsPage() {
  const { theme, setTheme, language, setLanguage, toast } = useAtlas();
  const [active, setActive] = useState('account');
  const [notifications, setNotifications] = useState({
    trip: true,
    price: true,
    community: false,
    weather: true
  });
  const [privacy, setPrivacy] = useState({ profile: true, reviews: false, location: true });

  return (
    <div className="space-y-6">
      <header>
        <h1 className="font-display text-3xl font-bold text-ink">Settings</h1>
        <p className="mt-1.5 text-[15px] text-muted">Control your account, appearance, language and privacy.</p>
      </header>

      <div className="grid gap-5 lg:grid-cols-[230px_1fr]">
        <nav aria-label="Settings sections">
          <ul className="space-y-1">
            {sections.map(({ id, label, icon: Icon }) =>
            <li key={id}>
                <button
                onClick={() => setActive(id)}
                aria-current={active === id ? 'true' : undefined}
                className={cn(
                  'flex w-full items-center gap-3 rounded-xl px-3.5 py-2.5 text-[13.5px] font-medium transition-colors',
                  active === id ? 'bg-brand/10 text-brand' : 'text-muted hover:bg-subtle hover:text-ink'
                )}>
                
                  <Icon className="h-4.5 w-4.5" />
                  {label}
                </button>
              </li>
            )}
          </ul>
        </nav>

        <Card className="p-6">
          {active === 'account' &&
          <div className="space-y-5">
              <h2 className="text-[15px] font-bold text-ink">Account</h2>
              <div className="grid gap-4 sm:grid-cols-2">
                <Field label="Display name" htmlFor="s-name">
                  <Input id="s-name" defaultValue="Aarav Explorer" />
                </Field>
                <Field label="Email" htmlFor="s-email">
                  <Input id="s-email" type="email" defaultValue="aarav@atlas.travel" />
                </Field>
                <Field label="Home city" htmlFor="s-city">
                  <Input id="s-city" defaultValue="Pune, India" />
                </Field>
                <Field label="Default currency" htmlFor="s-cur">
                  <Select id="s-cur" defaultValue="INR">
                    <option value="INR">INR — Indian Rupee</option>
                    <option value="USD">USD — US Dollar</option>
                    <option value="EUR">EUR — Euro</option>
                  </Select>
                </Field>
              </div>
              <Button onClick={() => toast({ title: 'Account updated', tone: 'success' })}>Save changes</Button>
            </div>
          }

          {active === 'security' &&
          <div className="space-y-5">
              <h2 className="text-[15px] font-bold text-ink">Security</h2>
              <div className="grid gap-4 sm:grid-cols-2">
                <Field label="Current password" htmlFor="s-cp">
                  <Input id="s-cp" type="password" placeholder="••••••••" />
                </Field>
                <Field label="New password" htmlFor="s-np">
                  <Input id="s-np" type="password" placeholder="••••••••" />
                </Field>
              </div>
              <div className="divide-y divide-line">
                <Toggle
                label="Two-factor authentication"
                description="Require a one-time code when signing in from a new device."
                checked
                onChange={() => toast({ title: 'Two-factor settings', description: 'Mocked in this prototype.', tone: 'info' })} />
              
              </div>
              <Button onClick={() => toast({ title: 'Password updated', tone: 'success' })}>Update password</Button>
            </div>
          }

          {active === 'notifications' &&
          <div>
              <h2 className="text-[15px] font-bold text-ink">Notifications</h2>
              <div className="mt-3">
                <Toggle
                label="Trip updates"
                description="Itinerary changes, reminders and agent re-planning alerts."
                checked={notifications.trip}
                onChange={(v) => setNotifications({ ...notifications, trip: v })} />
              
                <Toggle
                label="Price drops"
                description="Tell me when a saved stay or flight gets cheaper."
                checked={notifications.price}
                onChange={(v) => setNotifications({ ...notifications, price: v })} />
              
                <Toggle
                label="Community activity"
                description="Replies on Lost & Found reports and traveller insights."
                checked={notifications.community}
                onChange={(v) => setNotifications({ ...notifications, community: v })} />
              
                <Toggle
                label="Weather alerts"
                description="Warn me when conditions may affect a planned day."
                checked={notifications.weather}
                onChange={(v) => setNotifications({ ...notifications, weather: v })} />
              
              </div>
            </div>
          }

          {active === 'language' &&
          <div className="space-y-5">
              <h2 className="text-[15px] font-bold text-ink">Language</h2>
              <p className="text-[13px] text-muted">
                ATLAS is built for multilingual travel. Interface strings are localisation-ready.
              </p>
              <div className="grid gap-2 sm:grid-cols-3">
                {languages.map((l) =>
              <button
                key={l.code}
                onClick={() => setLanguage(l.code)}
                className={cn(
                  'rounded-xl border px-4 py-3 text-left transition-colors',
                  language === l.code ? 'border-brand bg-brand/5' : 'border-line hover:border-ink/20'
                )}>
                
                    <span className="block text-[13.5px] font-semibold text-ink">{l.label}</span>
                    <span className="block text-[12.5px] text-muted">{l.native}</span>
                  </button>
              )}
              </div>
            </div>
          }

          {active === 'appearance' &&
          <div className="space-y-5">
              <h2 className="text-[15px] font-bold text-ink">Appearance</h2>
              <div className="grid gap-3 sm:grid-cols-3">
                {(['light', 'dark', 'system'] as const).map((option) =>
              <button
                key={option}
                onClick={() => setTheme(option)}
                className={cn(
                  'rounded-2xl border p-4 text-left capitalize transition-colors',
                  theme === option ? 'border-brand bg-brand/5' : 'border-line hover:border-ink/20'
                )}>
                
                    <span
                  className={cn(
                    'mb-3 block h-16 rounded-xl border border-line',
                    option === 'light' ? 'bg-[#F8FAFC]' : option === 'dark' ? 'bg-[#0F172A]' : 'bg-gradient-to-r from-[#F8FAFC] to-[#0F172A]'
                  )} />
                
                    <span className="text-[13.5px] font-semibold text-ink">{option}</span>
                  </button>
              )}
              </div>
            </div>
          }

          {active === 'travel' &&
          <div className="space-y-5">
              <h2 className="text-[15px] font-bold text-ink">Travel Preferences</h2>
              <div className="grid gap-4 sm:grid-cols-2">
                <Field label="Default trip length" htmlFor="s-len">
                  <Select id="s-len" defaultValue="5">
                    <option value="3">3 days</option>
                    <option value="5">5 days</option>
                    <option value="7">7 days</option>
                  </Select>
                </Field>
                <Field label="Default pace" htmlFor="s-pace">
                  <Select id="s-pace" defaultValue="Moderate">
                    <option>Relaxed</option>
                    <option>Moderate</option>
                    <option>Packed</option>
                  </Select>
                </Field>
              </div>
              <Button onClick={() => toast({ title: 'Travel defaults saved', tone: 'success' })}>Save defaults</Button>
            </div>
          }

          {active === 'privacy' &&
          <div>
              <h2 className="text-[15px] font-bold text-ink">Privacy</h2>
              <div className="mt-3">
                <Toggle
                label="Public profile"
                description="Let other travellers see your name on community posts."
                checked={privacy.profile}
                onChange={(v) => setPrivacy({ ...privacy, profile: v })} />
              
                <Toggle
                label="Share my reviews"
                description="Contribute my ratings to Review Intelligence."
                checked={privacy.reviews}
                onChange={(v) => setPrivacy({ ...privacy, reviews: v })} />
              
                <Toggle
                label="Location while travelling"
                description="Used for nearby food, activity and Lost & Found matches."
                checked={privacy.location}
                onChange={(v) => setPrivacy({ ...privacy, location: v })} />
              
              </div>
            </div>
          }
        </Card>
      </div>
    </div>);

}

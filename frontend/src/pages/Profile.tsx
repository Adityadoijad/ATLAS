import { useState } from 'react';
import { CameraIcon, PencilIcon } from 'lucide-react';
import { Badge, Button, Card, Field, Input, Select } from '../components/ui/Primitives';
import { useAtlas } from '../contexts/AtlasContext';
import { languages } from '../data/content';

const initialProfile = {
  fullName: 'Aarav Explorer',
  email: 'aarav@atlas.travel',
  phone: '+91 98765 43210',
  dob: '1998-04-16',
  nationality: 'Indian'
};

const initialPreferences = {
  travelStyle: 'Balanced explorer',
  language: 'English',
  food: 'Vegetarian',
  accommodation: 'Boutique hotel',
  transport: 'Flight + local transport',
  budget: 'Mid-range (₹40k – ₹80k)',
  accessibility: 'None'
};

export function ProfilePage() {
  const { toast } = useAtlas();
  const [editing, setEditing] = useState(false);
  const [profile, setProfile] = useState(initialProfile);
  const [draft, setDraft] = useState(initialProfile);
  const [preferences, setPreferences] = useState(initialPreferences);

  const save = () => {
    if (!draft.fullName.trim() || !/^\S+@\S+\.\S+$/.test(draft.email)) {
      toast({ title: 'Check your details', description: 'A name and valid email are required.', tone: 'error' });
      return;
    }
    setProfile(draft);
    setEditing(false);
    toast({ title: 'Profile updated', tone: 'success' });
  };

  return (
    <div className="space-y-6">
      <header>
        <h1 className="font-display text-3xl font-bold text-ink">Profile</h1>
        <p className="mt-1.5 text-[15px] text-muted">Your account details and the preferences ATLAS plans around.</p>
      </header>

      <div className="grid gap-5 lg:grid-cols-[300px_1fr]">
        <Card className="h-fit p-6 text-center">
          <div className="relative mx-auto w-fit">
            <span className="flex h-24 w-24 items-center justify-center rounded-full bg-brand/10 text-2xl font-bold text-brand">
              AE
            </span>
            <button
              onClick={() => toast({ title: 'Photo upload', description: 'Image upload is mocked in this prototype.', tone: 'info' })}
              aria-label="Change profile photo"
              className="absolute bottom-0 right-0 flex h-8 w-8 items-center justify-center rounded-full border border-line bg-surface text-muted hover:text-ink">
              
              <CameraIcon className="h-4 w-4" />
            </button>
          </div>
          <h2 className="mt-4 text-lg font-bold text-ink">{profile.fullName}</h2>
          <p className="text-[13px] text-muted">{profile.email}</p>
          <Badge tone="brand" className="mt-3">
            12 trips planned
          </Badge>
          <Button
            variant="secondary"
            className="mt-5 w-full"
            icon={<PencilIcon className="h-3.5 w-3.5" />}
            onClick={() => {
              setDraft(profile);
              setEditing((e) => !e);
            }}>
            
            {editing ? 'Cancel editing' : 'Edit Profile'}
          </Button>
        </Card>

        <div className="space-y-5">
          <Card className="p-6">
            <h2 className="text-[15px] font-bold text-ink">Account Information</h2>
            {editing ?
            <div className="mt-5 grid gap-4 sm:grid-cols-2">
                <Field label="Full Name" htmlFor="p-name">
                  <Input id="p-name" value={draft.fullName} onChange={(e) => setDraft({ ...draft, fullName: e.target.value })} />
                </Field>
                <Field label="Email Address" htmlFor="p-email">
                  <Input id="p-email" type="email" value={draft.email} onChange={(e) => setDraft({ ...draft, email: e.target.value })} />
                </Field>
                <Field label="Phone Number" htmlFor="p-phone">
                  <Input id="p-phone" value={draft.phone} onChange={(e) => setDraft({ ...draft, phone: e.target.value })} />
                </Field>
                <Field label="Date of Birth" htmlFor="p-dob">
                  <Input id="p-dob" type="date" value={draft.dob} onChange={(e) => setDraft({ ...draft, dob: e.target.value })} />
                </Field>
                <Field label="Nationality" htmlFor="p-nat">
                  <Input id="p-nat" value={draft.nationality} onChange={(e) => setDraft({ ...draft, nationality: e.target.value })} />
                </Field>
                <div className="flex items-end gap-3">
                  <Button onClick={save}>Save changes</Button>
                </div>
              </div> :

            <dl className="mt-4 divide-y divide-line">
                {[
              ['Full Name', profile.fullName],
              ['Email Address', profile.email],
              ['Phone Number', profile.phone],
              ['Date of Birth', profile.dob],
              ['Nationality', profile.nationality]].
              map(([label, value]) =>
              <div key={label} className="flex justify-between gap-6 py-3 text-[13.5px]">
                    <dt className="text-muted">{label}</dt>
                    <dd className="font-semibold text-ink">{value}</dd>
                  </div>
              )}
              </dl>
            }
          </Card>

          <Card className="p-6">
            <h2 className="text-[15px] font-bold text-ink">Travel Preferences</h2>
            <p className="mt-1 text-[13px] text-muted">These feed directly into the Planner Agent on every new trip.</p>
            <div className="mt-5 grid gap-4 sm:grid-cols-2">
              <Field label="Travel style" htmlFor="tp-style">
                <Select id="tp-style" value={preferences.travelStyle} onChange={(e) => setPreferences({ ...preferences, travelStyle: e.target.value })}>
                  <option>Balanced explorer</option>
                  <option>Slow and relaxed</option>
                  <option>Packed and adventurous</option>
                  <option>Luxury focused</option>
                </Select>
              </Field>
              <Field label="Preferred language" htmlFor="tp-lang">
                <Select id="tp-lang" value={preferences.language} onChange={(e) => setPreferences({ ...preferences, language: e.target.value })}>
                  {languages.map((l) =>
                  <option key={l.code}>{l.label}</option>
                  )}
                </Select>
              </Field>
              <Field label="Food preference" htmlFor="tp-food">
                <Select id="tp-food" value={preferences.food} onChange={(e) => setPreferences({ ...preferences, food: e.target.value })}>
                  <option>Vegetarian</option>
                  <option>Vegan</option>
                  <option>Non-vegetarian</option>
                  <option>Local cuisine first</option>
                </Select>
              </Field>
              <Field label="Accommodation preference" htmlFor="tp-acc">
                <Select id="tp-acc" value={preferences.accommodation} onChange={(e) => setPreferences({ ...preferences, accommodation: e.target.value })}>
                  <option>Boutique hotel</option>
                  <option>Resort</option>
                  <option>Homestay</option>
                  <option>Hostel</option>
                </Select>
              </Field>
              <Field label="Transport preference" htmlFor="tp-tr">
                <Select id="tp-tr" value={preferences.transport} onChange={(e) => setPreferences({ ...preferences, transport: e.target.value })}>
                  <option>Flight + local transport</option>
                  <option>Train journeys</option>
                  <option>Self-drive</option>
                  <option>Private cab</option>
                </Select>
              </Field>
              <Field label="Budget preference" htmlFor="tp-bud">
                <Select id="tp-bud" value={preferences.budget} onChange={(e) => setPreferences({ ...preferences, budget: e.target.value })}>
                  <option>Budget (under ₹40k)</option>
                  <option>Mid-range (₹40k – ₹80k)</option>
                  <option>Premium (₹80k+)</option>
                </Select>
              </Field>
              <Field label="Accessibility needs" htmlFor="tp-a11y">
                <Select id="tp-a11y" value={preferences.accessibility} onChange={(e) => setPreferences({ ...preferences, accessibility: e.target.value })}>
                  <option>None</option>
                  <option>Wheelchair accessible</option>
                  <option>Elder-friendly</option>
                  <option>Child-friendly</option>
                  <option>Medical accessibility</option>
                </Select>
              </Field>
            </div>
            <Button className="mt-6" onClick={() => toast({ title: 'Preferences saved', description: 'Future plans will use these settings.', tone: 'success' })}>
              Save preferences
            </Button>
          </Card>
        </div>
      </div>
    </div>);

}

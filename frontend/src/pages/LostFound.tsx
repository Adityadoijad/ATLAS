import { useState } from 'react';
import { PackageSearchIcon, SearchIcon } from 'lucide-react';
import { LostFoundCard } from '../components/cards/ContentCards';
import { Button, EmptyState, Field, Input, Select, Tabs, Textarea } from '../components/ui/Primitives';
import { Modal } from '../components/ui/Overlays';
import { useAtlas } from '../contexts/AtlasContext';
import { submitLostFound } from '../services/atlasApi';
import { IMAGES } from '../data/destinations';
import { LostFoundItem } from '../types';

const categories = ['Electronics', 'Documents', 'Gear', 'Jewellery', 'Clothing', 'Other'];

export function LostFoundPage() {
  const { lostFound, addLostFound, toast } = useAtlas();
  const [tab, setTab] = useState('all');
  const [query, setQuery] = useState('');
  const [category, setCategory] = useState('all');
  const [formType, setFormType] = useState<'lost' | 'found' | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [form, setForm] = useState({
    title: '',
    category: 'Electronics',
    location: '',
    date: '',
    description: '',
    contact: 'In-app message'
  });
  const [errors, setErrors] = useState<Record<string, string>>({});

  const results = lostFound.filter((item) => {
    const matchesTab = tab === 'all' || item.type === tab;
    const matchesQuery =
    !query || `${item.title} ${item.location} ${item.category}`.toLowerCase().includes(query.toLowerCase());
    const matchesCategory = category === 'all' || item.category === category;
    return matchesTab && matchesQuery && matchesCategory;
  });

  const submit = async () => {
    const next: Record<string, string> = {};
    if (!form.title.trim()) next.title = 'Describe the item briefly.';
    if (!form.location.trim()) next.location = 'Where was it lost or found?';
    if (!form.date) next.date = 'Select a date.';
    setErrors(next);
    if (Object.keys(next).length > 0 || !formType) return;

    setSubmitting(true);
    const created: LostFoundItem = await submitLostFound({
      title: form.title,
      type: formType,
      category: form.category,
      location: form.location,
      date: form.date,
      description: form.description || 'No additional description provided.',
      image: IMAGES.culture,
      contact: form.contact
    });
    addLostFound(created);
    setSubmitting(false);
    setFormType(null);
    setForm({ title: '', category: 'Electronics', location: '', date: '', description: '', contact: 'In-app message' });
    toast({ title: 'Report submitted', description: 'Travellers in this area will be notified.', tone: 'success' });
  };

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="font-display text-3xl font-bold text-ink">Lost &amp; Found</h1>
          <p className="mt-1.5 text-[15px] text-muted">
            A community board for travellers and locals to reunite lost items in a travel area.
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="secondary" onClick={() => setFormType('found')}>
            Report Found Item
          </Button>
          <Button onClick={() => setFormType('lost')}>Report Lost Item</Button>
        </div>
      </header>

      <div className="flex flex-col gap-3 sm:flex-row">
        <div className="relative flex-1">
          <SearchIcon className="pointer-events-none absolute left-4 top-1/2 h-4.5 w-4.5 -translate-y-1/2 text-muted" />
          <Input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search item, location or category..."
            aria-label="Search lost and found"
            className="pl-12" />
          
        </div>
        <Select value={category} onChange={(e) => setCategory(e.target.value)} aria-label="Filter by category" className="sm:w-52">
          <option value="all">All categories</option>
          {categories.map((c) =>
          <option key={c} value={c}>
              {c}
            </option>
          )}
        </Select>
      </div>

      <Tabs
        value={tab}
        onChange={setTab}
        tabs={[
        { id: 'all', label: 'All reports', count: lostFound.length },
        { id: 'lost', label: 'Lost', count: lostFound.filter((i) => i.type === 'lost').length },
        { id: 'found', label: 'Found', count: lostFound.filter((i) => i.type === 'found').length }]
        } />
      

      {results.length === 0 ?
      <EmptyState
        icon={<PackageSearchIcon className="h-5 w-5" />}
        title="No reports match your search"
        description="Try a different location or clear the category filter." /> :


      <div className="grid gap-5 sm:grid-cols-2 xl:grid-cols-3">
          {results.map((item) =>
        <LostFoundCard
          key={item.id}
          item={item}
          onContact={() =>
          toast({ title: 'Message sent', description: `The reporter of “${item.title}” has been notified.`, tone: 'success' })
          } />

        )}
        </div>
      }

      <Modal
        open={Boolean(formType)}
        onClose={() => setFormType(null)}
        title={formType === 'found' ? 'Report a found item' : 'Report a lost item'}
        description="Visible to travellers and locals in the same area."
        size="lg"
        footer={
        <>
            <Button variant="ghost" onClick={() => setFormType(null)}>
              Cancel
            </Button>
            <Button loading={submitting} onClick={submit}>
              Submit report
            </Button>
          </>
        }>
        
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Item name" error={errors.title} htmlFor="lf-title">
            <Input id="lf-title" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} placeholder="Black DSLR camera bag" />
          </Field>
          <Field label="Category" htmlFor="lf-cat">
            <Select id="lf-cat" value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })}>
              {categories.map((c) =>
              <option key={c}>{c}</option>
              )}
            </Select>
          </Field>
          <Field label="Location" error={errors.location} htmlFor="lf-loc">
            <Input id="lf-loc" value={form.location} onChange={(e) => setForm({ ...form, location: e.target.value })} placeholder="Baga Beach, Goa" />
          </Field>
          <Field label="Date" error={errors.date} htmlFor="lf-date">
            <Input id="lf-date" type="date" value={form.date} onChange={(e) => setForm({ ...form, date: e.target.value })} />
          </Field>
          <div className="sm:col-span-2">
            <Field label="Description" htmlFor="lf-desc">
              <Textarea
                id="lf-desc"
                rows={3}
                value={form.description}
                onChange={(e) => setForm({ ...form, description: e.target.value })}
                placeholder="Colour, distinguishing marks, contents, where you last saw it..." />
              
            </Field>
          </div>
          <Field label="Image" hint="Optional — a photo increases match rates." htmlFor="lf-img">
            <Input id="lf-img" type="file" accept="image/*" className="pt-2.5 text-[13px]" />
          </Field>
          <Field label="Contact preference" htmlFor="lf-contact">
            <Select id="lf-contact" value={form.contact} onChange={(e) => setForm({ ...form, contact: e.target.value })}>
              <option>In-app message</option>
              <option>Email</option>
              <option>Phone</option>
            </Select>
          </Field>
        </div>
      </Modal>
    </div>);

}

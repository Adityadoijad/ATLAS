import { Link } from 'react-router-dom';
import { CompassIcon } from 'lucide-react';

const columns = [
{
  title: 'Product',
  links: [
  { label: 'Plan a trip', to: '/plan' },
  { label: 'AI Assistant', to: '/assistant' },
  { label: 'Explore', to: '/explore' },
  { label: 'Bookings', to: '/bookings' }]

},
{
  title: 'Intelligence',
  links: [
  { label: 'Multi-agent system', to: '/about' },
  { label: 'Review intelligence', to: '/food' },
  { label: 'Community insights', to: '/lost-found' },
  { label: 'Activities', to: '/activities' }]

},
{
  title: 'Account',
  links: [
  { label: 'Dashboard', to: '/dashboard' },
  { label: 'Saved places', to: '/saved' },
  { label: 'Profile', to: '/profile' },
  { label: 'Settings', to: '/settings' }]

}];


export function Footer() {
  return (
    <footer className="border-t border-line bg-surface">
      <div className="mx-auto grid max-w-shell gap-10 px-5 py-14 lg:grid-cols-[1.4fr_repeat(3,1fr)] lg:px-8">
        <div>
          <div className="flex items-center gap-2.5">
            <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-brand text-white">
              <CompassIcon className="h-5 w-5" />
            </span>
            <span className="font-display text-[19px] font-extrabold text-ink">ATLAS</span>
          </div>
          <p className="mt-4 max-w-xs text-sm leading-relaxed text-muted">
            An AI-powered multi-agent travel planning and decision support platform. Where Travels Meets AI.
          </p>
        </div>
        {columns.map((col) =>
        <div key={col.title}>
            <h3 className="text-[13px] font-semibold text-ink">{col.title}</h3>
            <ul className="mt-4 space-y-2.5">
              {col.links.map((l) =>
            <li key={l.label}>
                  <Link to={l.to} className="text-[13px] text-muted transition-colors hover:text-brand">
                    {l.label}
                  </Link>
                </li>
            )}
            </ul>
          </div>
        )}
      </div>
      <div className="border-t border-line">
        <div className="mx-auto flex max-w-shell flex-col gap-2 px-5 py-5 text-[12.5px] text-muted sm:flex-row sm:items-center sm:justify-between lg:px-8">
          <p>© 2026 ATLAS · Where Travel Meets AI</p>
          <p>Prototype interface · mock data, no real bookings or payments</p>
        </div>
      </div>
    </footer>);

}

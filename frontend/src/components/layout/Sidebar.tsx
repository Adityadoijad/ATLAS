import { NavLink } from 'react-router-dom';
import {
  BookmarkIcon,
  CalendarCheckIcon,
  CompassIcon,
  LayoutDashboardIcon,
  LuggageIcon,
  PackageSearchIcon,
  SettingsIcon,
  SparklesIcon,
  UserRoundIcon,
  UtensilsIcon,
  TicketIcon } from
'lucide-react';
import { cn } from '../../utils/format';

const links = [
{ to: '/dashboard', label: 'Home', icon: LayoutDashboardIcon },
{ to: '/trips', label: 'Trips', icon: LuggageIcon },
{ to: '/assistant', label: 'Assistant', icon: SparklesIcon },
{ to: '/bookings', label: 'Bookings', icon: CalendarCheckIcon },
{ to: '/explore', label: 'Explore', icon: CompassIcon },
{ to: '/food', label: 'Food', icon: UtensilsIcon },
{ to: '/activities', label: 'Activities', icon: TicketIcon },
{ to: '/lost-found', label: 'Lost & Found', icon: PackageSearchIcon },
{ to: '/saved', label: 'Saved Places', icon: BookmarkIcon },
{ to: '/profile', label: 'Profile', icon: UserRoundIcon },
{ to: '/settings', label: 'Settings', icon: SettingsIcon }];


export function Sidebar() {
  return (
    <aside className="sticky top-[72px] hidden h-[calc(100vh-72px)] w-[228px] shrink-0 border-r border-line bg-surface/60 px-3 py-6 lg:block">
      <p className="px-3 pb-3 text-[11px] font-semibold uppercase tracking-[0.14em] text-muted">Workspace</p>
      <nav aria-label="Workspace">
        <ul className="space-y-0.5">
          {links.map(({ to, label, icon: Icon }) =>
          <li key={to}>
              <NavLink
              to={to}
              className={({ isActive }) =>
              cn(
                'group flex items-center gap-3 rounded-xl px-3 py-2.5 text-[13.5px] font-medium transition-colors',
                isActive ? 'bg-brand/10 text-brand' : 'text-muted hover:bg-subtle hover:text-ink'
              )
              }>
              
                <Icon className="h-4.5 w-4.5" />
                {label}
              </NavLink>
            </li>
          )}
        </ul>
      </nav>

      <div className="mt-6 rounded-2xl border border-line bg-canvas p-4">
        <p className="text-[13px] font-semibold text-ink">Multi-agent planning</p>
        <p className="mt-1 text-[12px] leading-relaxed text-muted">
          Nine agents coordinate your next itinerary in under a minute.
        </p>
        <NavLink
          to="/plan"
          className="mt-3 inline-flex h-9 w-full items-center justify-center rounded-lg bg-brand text-[13px] font-semibold text-white">
          
          Plan a New Trip
        </NavLink>
      </div>
    </aside>);

}

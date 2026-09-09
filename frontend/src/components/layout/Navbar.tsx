import { useState } from 'react';
import { Link, NavLink, useLocation } from 'react-router-dom';
import { motion } from 'framer-motion';
import { BellIcon, CompassIcon, MenuIcon, MoonIcon, SunIcon, XIcon } from 'lucide-react';
import { useAtlas } from '../../contexts/AtlasContext';
import { languages } from '../../data/content';
import { cn } from '../../utils/format';
import { Dropdown } from '../ui/Overlays';

export const primaryNav = [
{ to: '/', label: 'Home' },
{ to: '/trips', label: 'Trips' },
{ to: '/assistant', label: 'Assistant' },
{ to: '/bookings', label: 'Bookings' },
{ to: '/explore', label: 'Explore' },
{ to: '/about', label: 'About' }];


export function Navbar() {
  const { isDark, setTheme, theme, language, setLanguage, toast, authUser, logout } = useAtlas();
  const [mobileOpen, setMobileOpen] = useState(false);
  const location = useLocation();

  return (
    <header className="sticky top-0 z-40 border-b border-line bg-surface/85 backdrop-blur-xl">
      <div className="mx-auto flex h-[72px] max-w-shell items-center justify-between gap-6 px-5 lg:px-8">
        <Link to="/" className="flex items-center gap-2.5" aria-label="ATLAS home">
          <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-brand text-white">
            <CompassIcon className="h-5 w-5" />
          </span>
          <span className="leading-tight">
            <span className="block font-display text-[19px] font-extrabold tracking-tight text-ink">ATLAS</span>
            <span className="hidden text-[10.5px] font-medium uppercase tracking-[0.14em] text-muted sm:block">
              Where Travels Meets AI
            </span>
          </span>
        </Link>

        <nav aria-label="Primary" className="hidden lg:block">
          <ul className="flex items-center gap-1">
            {primaryNav.map((item) => {
              const active =
              item.to === '/' ? location.pathname === '/' : location.pathname.startsWith(item.to);
              return (
                <li key={item.to}>
                  <NavLink
                    to={item.to}
                    className={cn(
                      'relative block px-3.5 py-2 text-sm font-medium transition-colors',
                      active ? 'text-brand' : 'text-muted hover:text-ink'
                    )}>
                    
                    {item.label}
                    {active &&
                    <motion.span
                      layoutId="nav-underline"
                      className="absolute -bottom-[19px] left-3 right-3 h-[2.5px] rounded-full bg-brand" />

                    }
                  </NavLink>
                </li>);

            })}
          </ul>
        </nav>

        <div className="flex items-center gap-2">
          <div className="hidden xl:block">
            <Dropdown
              label=""
              align="right"
              value={language}
              onChange={setLanguage}
              options={languages.map((l) => ({ value: l.code, label: l.native }))} />
            
          </div>
          <button
            onClick={() => toast({ title: 'No new notifications', description: 'You are all caught up.', tone: 'info' })}
            aria-label="Notifications"
            className="relative hidden h-10 w-10 items-center justify-center rounded-xl border border-line text-muted transition-colors hover:text-ink sm:flex">
            
            <BellIcon className="h-4.5 w-4.5" />
            <span className="absolute right-2.5 top-2.5 h-1.5 w-1.5 rounded-full bg-brand" />
          </button>
          <button
            onClick={() => setTheme(isDark ? 'light' : 'dark')}
            aria-label={`Switch to ${isDark ? 'light' : 'dark'} theme`}
            aria-pressed={isDark}
            className="flex h-10 w-10 items-center justify-center rounded-xl border border-line text-muted transition-colors hover:text-ink"
            title={`Theme: ${theme}`}>
            
            {isDark ? <SunIcon className="h-4.5 w-4.5" /> : <MoonIcon className="h-4.5 w-4.5" />}
          </button>
          <Link
            to="/profile"
            aria-label="Your profile"
            className="flex h-10 w-10 items-center justify-center rounded-full bg-brand/10 text-[13px] font-bold text-brand ring-2 ring-transparent transition hover:ring-brand/30">
            
            {authUser ? authUser.name.slice(0, 2).toUpperCase() : 'EX'}
          </Link>
          {authUser ? <button onClick={logout} className="hidden text-sm font-semibold text-muted hover:text-ink sm:block">Log out</button> : <Link to="/login" className="hidden text-sm font-semibold text-brand sm:block">Log in</Link>}
          <button
            onClick={() => setMobileOpen((o) => !o)}
            aria-label="Toggle navigation menu"
            aria-expanded={mobileOpen}
            className="flex h-10 w-10 items-center justify-center rounded-xl border border-line text-ink lg:hidden">
            
            {mobileOpen ? <XIcon className="h-4.5 w-4.5" /> : <MenuIcon className="h-4.5 w-4.5" />}
          </button>
        </div>
      </div>

      {mobileOpen &&
      <motion.nav
        initial={{ height: 0, opacity: 0 }}
        animate={{ height: 'auto', opacity: 1 }}
        aria-label="Mobile"
        className="overflow-hidden border-t border-line bg-surface lg:hidden">
        
          <ul className="mx-auto max-w-shell space-y-1 px-5 py-4">
            {primaryNav.map((item) =>
          <li key={item.to}>
                <NavLink
              to={item.to}
              onClick={() => setMobileOpen(false)}
              className={({ isActive }) =>
              cn(
                'block rounded-xl px-4 py-2.5 text-sm font-medium',
                isActive ? 'bg-brand/10 text-brand' : 'text-muted hover:bg-subtle'
              )
              }>
              
                  {item.label}
                </NavLink>
              </li>
          )}
            <li className="pt-2">
              <NavLink
              to="/plan"
              onClick={() => setMobileOpen(false)}
              className="block rounded-xl bg-brand px-4 py-2.5 text-center text-sm font-semibold text-white">
              
                Plan a New Trip
              </NavLink>
            </li>
          </ul>
        </motion.nav>
      }
    </header>);

}

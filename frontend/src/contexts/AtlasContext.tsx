import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { Booking, LostFoundItem, TripPlan, Trip, SavedPlace } from '../types';
import { bookings as seedBookings, lostFoundItems as seedLostFound } from '../data/catalog';
import { uid } from '../utils/format';
import i18n, { supportedLanguages, type LanguageCode } from '../i18n';
import {
  AuthUser,
  deletePersistedSavedPlace,
  deletePersistedTrip,
  fetchCurrentUser,
  fetchPersistedSavedPlaces,
  fetchPersistedTrips,
  loginUser,
  registerUser,
  savePersistedPlace
} from '../services/atlasApi';

type Theme = 'light' | 'dark' | 'system';

export interface Toast {
  id: string;
  title: string;
  description?: string;
  tone: 'success' | 'info' | 'error';
}

interface AtlasState {
  authUser: AuthUser | null;
  authLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  initializeSession: (token: string) => Promise<void>;
  register: (name: string, email: string, password: string) => Promise<void>;
  logout: () => void;
  theme: Theme;
  setTheme: (t: Theme) => void;
  isDark: boolean;
  language: LanguageCode;
  setLanguage: (code: string) => void;
  saved: string[];
  toggleSaved: (id: string, label?: string) => void;
  isSaved: (id: string) => boolean;
  savedItems: SavedPlace[];
  removeSavedItem: (id: string) => void;
  trips: Trip[];
  removeTrip: (id: string) => void;
  bookings: Booking[];
  addBooking: (b: Booking) => void;
  cancelBooking: (id: string) => void;
  lostFound: LostFoundItem[];
  addLostFound: (item: LostFoundItem) => void;
  plan: TripPlan | null;
  setPlan: (p: TripPlan | null) => void;
  toasts: Toast[];
  toast: (t: Omit<Toast, 'id'>) => void;
  dismissToast: (id: string) => void;
}

const AtlasContext = createContext<AtlasState | null>(null);

export function AtlasProvider({ children }: {children: React.ReactNode;}) {
  const [authUser, setAuthUser] = useState<AuthUser | null>(null);
  const [authLoading, setAuthLoading] = useState(true);
  const [theme, setTheme] = useState<Theme>('light');
  const [language, setLanguage] = useState<LanguageCode>(() => {
    const stored = localStorage.getItem('atlas_language');
    return supportedLanguages.includes(stored as LanguageCode) ? stored as LanguageCode : 'en';
  });
  const [saved, setSaved] = useState<string[]>([]);
  const [savedItems, setSavedItems] = useState<SavedPlace[]>([]);
  const [trips, setTrips] = useState<Trip[]>([]);
  const [bookings, setBookings] = useState<Booking[]>(seedBookings);
  const [lostFound, setLostFound] = useState<LostFoundItem[]>(seedLostFound);
  const [plan, setPlan] = useState<TripPlan | null>(null);
  const [toasts, setToasts] = useState<Toast[]>([]);

  const prefersDark =
  typeof window !== 'undefined' && window.matchMedia ?
  window.matchMedia('(prefers-color-scheme: dark)').matches :
  false;
  const isDark = theme === 'dark' || theme === 'system' && prefersDark;

  useEffect(() => {
    const root = document.documentElement;
    root.classList.toggle('dark', isDark);
  }, [isDark]);

  useEffect(() => {
    const token = localStorage.getItem('atlas_access_token');
    if (!token) {
      setAuthLoading(false);
      return;
    }
    Promise.all([fetchCurrentUser(token), fetchPersistedTrips(token), fetchPersistedSavedPlaces(token)])
      .then(([user, persistedTrips, persistedPlaces]) => {
        setAuthUser(user);
        setTrips(persistedTrips);
        setSavedItems(persistedPlaces);
        setSaved(persistedPlaces.map((place) => place.id));
      })
      .catch(() => {
        localStorage.removeItem('atlas_access_token');
      })
      .finally(() => setAuthLoading(false));
  }, []);

  const initializeSession = useCallback(async (token: string) => {
    localStorage.setItem('atlas_access_token', token);
    const [user, persistedTrips, persistedPlaces] = await Promise.all([
      fetchCurrentUser(token),
      fetchPersistedTrips(token),
      fetchPersistedSavedPlaces(token)
    ]);
    setAuthUser(user);
    setTrips(persistedTrips);
    setSavedItems(persistedPlaces);
    setSaved(persistedPlaces.map((place) => place.id));
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const result = await loginUser(email, password);
    await initializeSession(result.access_token);
  }, [initializeSession]);

  const register = useCallback(async (name: string, email: string, password: string) => {
    await registerUser({ name, email, password });
    await login(email, password);
  }, [login]);

  const logout = useCallback(() => {
    localStorage.removeItem('atlas_access_token');
    setAuthUser(null);
    setTrips([]);
    setSaved([]);
    setSavedItems([]);
    setPlan(null);
  }, []);

  const dismissToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const toast = useCallback(
    (t: Omit<Toast, 'id'>) => {
      const id = uid('toast');
      setToasts((prev) => [...prev, { ...t, id }]);
      window.setTimeout(() => setToasts((prev) => prev.filter((x) => x.id !== id)), 3600);
    },
    []
  );

  const toggleSaved = useCallback(
    (id: string, label?: string) => {
      setSaved((prev) => {
        const exists = prev.includes(id);
        const token = localStorage.getItem('atlas_access_token');
        if (token && exists) {
          deletePersistedSavedPlace(id, token).catch(() => toast({ title: 'Could not remove saved place', tone: 'error' }));
        } else if (token) {
          savePersistedPlace({ place_id: id, name: label ?? id, type: 'destination', category: 'Destinations' }, token)
            .catch(() => toast({ title: 'Could not save place', tone: 'error' }));
        }
        toast({
          title: exists ? 'Removed from saved' : 'Saved',
          description: label ? `${label} ${exists ? 'removed from' : 'added to'} your places.` : undefined,
          tone: exists ? 'info' : 'success'
        });
        return exists ? prev.filter((x) => x !== id) : [...prev, id];
      });
    },
    [toast]
  );

  const value = useMemo<AtlasState>(
    () => ({
      theme,
      authUser,
      authLoading,
      login,
      initializeSession,
      register,
      logout,
      setTheme,
      isDark,
      language,
      setLanguage: (code: string) => {
        const nextLanguage: LanguageCode = supportedLanguages.includes(code as LanguageCode) ? code as LanguageCode : 'en';
        setLanguage(nextLanguage);
        localStorage.setItem('atlas_language', nextLanguage);
        i18n.changeLanguage(nextLanguage);
        toast({ title: i18n.t('toast.languageUpdated'), description: i18n.t('toast.languageSaved'), tone: 'success' });
      },
      saved,
      toggleSaved,
      isSaved: (id: string) => saved.includes(id),
      savedItems,
      removeSavedItem: (id: string) => {
        const token = localStorage.getItem('atlas_access_token');
        setSavedItems((prev) => prev.filter((p) => p.id !== id));
        if (token) deletePersistedSavedPlace(id, token).catch(() => toast({ title: 'Could not remove saved place', tone: 'error' }));
        toast({ title: 'Removed', description: 'Place removed from your collection.', tone: 'info' });
      },
      trips,
      removeTrip: (id: string) => {
        const token = localStorage.getItem('atlas_access_token');
        setTrips((prev) => prev.filter((t) => t.id !== id));
        if (token) deletePersistedTrip(id, token).catch(() => toast({ title: 'Could not delete trip', tone: 'error' }));
        toast({ title: 'Trip deleted', tone: 'info' });
      },
      bookings,
      addBooking: (b: Booking) => setBookings((prev) => [b, ...prev]),
      cancelBooking: (id: string) => {
        setBookings((prev) => prev.map((b) => b.id === id ? { ...b, status: 'cancelled' } : b));
        toast({ title: 'Booking cancelled', description: 'A confirmation has been sent to your email.', tone: 'error' });
      },
      lostFound,
      addLostFound: (item: LostFoundItem) => setLostFound((prev) => [item, ...prev]),
      plan,
      setPlan,
      toasts,
      toast,
      dismissToast
    }),
    [theme, isDark, language, saved, savedItems, trips, bookings, lostFound, plan, toasts, authUser, authLoading, login, initializeSession, register, logout, toggleSaved, toast, dismissToast]
  );

  return <AtlasContext.Provider value={value}>{children}</AtlasContext.Provider>;
}

export function useAtlas() {
  const ctx = useContext(AtlasContext);
  if (!ctx) throw new Error('useAtlas must be used inside AtlasProvider');
  return ctx;
}

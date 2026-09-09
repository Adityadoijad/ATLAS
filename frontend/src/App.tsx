import React from 'react';
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { AtlasProvider } from './contexts/AtlasContext';
import { Toaster } from './components/ui/Overlays';
import { Shell } from './components/layout/Shell';
import { HomePage } from './pages/Home';
import { ExplorePage } from './pages/Explore';
const PlannerPage = React.lazy(() => import('./pages/Planner').then((module) => ({ default: module.PlannerPage })));
const ItineraryPage = React.lazy(() => import('./pages/Itinerary').then((module) => ({ default: module.ItineraryPage })));
const AssistantPage = React.lazy(() => import('./pages/Assistant').then((module) => ({ default: module.AssistantPage })));
import { TripsPage } from './pages/Trips';
const BookingsPage = React.lazy(() => import('./pages/Bookings').then((module) => ({ default: module.BookingsPage })));
const LostFoundPage = React.lazy(() => import('./pages/LostFound').then((module) => ({ default: module.LostFoundPage })));
import { SavedPlacesPage } from './pages/SavedPlaces';
import { ProfilePage } from './pages/Profile';
import { SettingsPage } from './pages/Settings';
import { AboutPage } from './pages/About';
import { DashboardPage } from './pages/Dashboard';
import { FoodPage } from './pages/Food';
import { AuthPage } from './pages/Auth';
import { AuthCallbackPage } from './pages/AuthCallback';
import { ActivitiesPage } from './pages/Activities';

function LoadingSpinner() {
  return <div className="flex min-h-48 items-center justify-center text-sm text-muted">Loading…</div>;
}

export function App() {
  return (
    <AtlasProvider>
      <BrowserRouter>
        <React.Suspense fallback={<LoadingSpinner />}>
        <Routes>
          <Route
            path="/"
            element={
            <Shell withFooter>
                <HomePage />
              </Shell>
            } />
          
          <Route
            path="/about"
            element={
            <Shell withFooter>
                <AboutPage />
              </Shell>
            } />
          <Route path="/login" element={<Shell><AuthPage /></Shell>} />
          <Route path="/register" element={<Shell><AuthPage /></Shell>} />
          <Route path="/auth/callback" element={<Shell><AuthCallbackPage /></Shell>} />
          
          <Route
            path="/assistant"
            element={
            <Shell contained={false}>
                <AssistantPage />
              </Shell>
            } />
          
          {[
          { path: '/dashboard', element: <DashboardPage /> },
          { path: '/explore', element: <ExplorePage /> },
          { path: '/plan', element: <PlannerPage /> },
          { path: '/itinerary', element: <ItineraryPage /> },
          { path: '/trips', element: <TripsPage /> },
          { path: '/bookings', element: <BookingsPage /> },
          { path: '/food', element: <FoodPage /> },
          { path: '/activities', element: <ActivitiesPage /> },
          { path: '/lost-found', element: <LostFoundPage /> },
          { path: '/saved', element: <SavedPlacesPage /> },
          { path: '/profile', element: <ProfilePage /> },
          { path: '/settings', element: <SettingsPage /> }].
          map((route) =>
          <Route key={route.path} path={route.path} element={<Shell withSidebar>{route.element}</Shell>} />
          )}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
        </React.Suspense>
        <Toaster />
      </BrowserRouter>
    </AtlasProvider>);

}
